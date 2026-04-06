'''
smtx-reconcile

Fetches dailyReads and power2choose data from MongoDB, downloads and parses each
plan's Electricity Facts Label (EFL), computes estimated annual cost against 3 years
of real usage data, and produces a ranked Markdown report of the top-5 cheapest plans.
'''
import os
import re
import sys
import json
import argparse
import subprocess
from collections import defaultdict
from datetime import datetime

import dateparser
import requests

from kizano import getConfig, getLogger
from smartmetertx import schema
from smartmetertx.utils import getMongoConnection

log = getLogger(__name__)

DAYS_IN_MONTH = {
    '01': 31, '02': 28, '03': 31, '04': 30, '05': 31, '06': 30,
    '07': 31, '08': 31, '09': 30, '10': 31, '11': 30, '12': 31
}
MONTH_NAMES = {
    '01': 'January',  '02': 'February', '03': 'March',    '04': 'April',
    '05': 'May',      '06': 'June',     '07': 'July',     '08': 'August',
    '09': 'September','10': 'October',  '11': 'November', '12': 'December'
}
CANDIDATE_POOL = 15   # try up to this many plans (by kwh2000 asc) to find TOP_N valid ones
TOP_N          = 5

# Compiled EFL regex patterns — covers Budget Power, Frontier, Gexa, Rhythm, Ranchero,
# TruePower, and SoFed formats observed in the wild.
_RE_ENERGY   = re.compile(r'(?:Fixed\s+)?Energy Charge[:\s]+\$?\s*([\d.]+)\s*[¢c]?\s*per\s*k[Ww][Hh]', re.I)
_RE_BASE     = re.compile(r'(?:Monthly\s+)?Base Charge[:\s]+\$\s*([\d.]+)\s*per', re.I)
_RE_TDSP_KWH = re.compile(r'(?:TDU|TDSP|Delivery|Oncor|CenterPoint)[^\n]*?([\d.]+)\s*[¢c]\s*per\s*k[Ww][Hh]', re.I)
_RE_TDSP_BASE= re.compile(r'(?:TDU|TDSP|Delivery|Oncor|CenterPoint)[^\n]*?\$\s*([\d.]+)\s*per\s*(?:billing\s*cycle|month)', re.I)
_RE_CREDIT   = re.compile(r'(?:Credit|Discount|Bill\s+Credit)[^\n]*?\$\s*([\d.]+)\s*per\s*(?:billing\s*cycle|month)', re.I)


class SmtxReconciler:
    '''
    Reconciles real electricity usage against current provider plan offerings
    to identify the cheapest available plans and produce a ranked Markdown report.
    '''

    def __init__(self, scratch_pad: str):
        self.config      = getConfig()
        self.mongo       = getMongoConnection(self.config)
        self.db          = self.mongo.get_database(self.config['mongo'].get('dbname', 'smartmetertx'))
        self.scratch_pad = scratch_pad
        os.makedirs(scratch_pad, exist_ok=True)

    def close(self):
        if self.mongo:
            self.mongo.close()
            self.mongo = None

    def getMonthlyUsage(self, since: datetime) -> dict:
        '''
        Query dailyReads and return average monthly kWh per calendar month (01–12),
        averaged across all complete months in the date window.
        Partial boundary months (where recorded day-count < expected days) are skipped.
        Returns {mm: avg_monthly_kwh}.
        '''
        log.info('Fetching daily reads since %s...', since.strftime('%F'))
        cursor = self.db[schema.DAILY_READS].find({'readDate': {'$gte': since}}).sort('readDate', 1)
        by_year_month = defaultdict(list)
        for rec in cursor:
            date = rec['readDate']
            key  = (date.strftime('%Y'), date.strftime('%m'))
            by_year_month[key].append(float(rec['energyDataKwh']))

        by_cal_month = defaultdict(list)
        for (year, mm), daily_kwh in by_year_month.items():
            expected = DAYS_IN_MONTH[mm]
            if len(daily_kwh) < expected:
                log.debug('Skipping partial month %s-%s (%d/%d days)', year, mm, len(daily_kwh), expected)
                continue
            by_cal_month[mm].extend(daily_kwh)

        result = {
            mm: (sum(vals) / len(vals)) * DAYS_IN_MONTH[mm]
            for mm, vals in sorted(by_cal_month.items())
        }
        log.info('Monthly usage computed for %d calendar months.', len(result))
        scratch_path = os.path.join(self.scratch_pad, 'monthly_usage.json')
        with open(scratch_path, 'w') as f:
            json.dump({mm: round(v, 2) for mm, v in result.items()}, f, indent=2)
        return result

    def getProviderPlans(self, since: datetime):
        '''
        Query power2choose for all plans since `since`.
        Returns (plans_all, plans_latest) where plans_latest contains only the most-recent
        scrape date's plans, sorted by price.kwh2000 ascending.
        '''
        log.info('Fetching provider plans since %s...', since.strftime('%F'))
        cursor = list(self.db[schema.POWER2CHOOSE].find({'discovered_at': {'$gte': since}}))
        log.info('Found %d power2choose records.', len(cursor))

        # Determine the latest scrape date
        latest_date = max(p['discovered_at'].strftime('%Y-%m-%d') for p in cursor)
        log.info('Latest scrape date: %s', latest_date)

        plans_latest = sorted(
            [p for p in cursor if p['discovered_at'].strftime('%Y-%m-%d') == latest_date],
            key=lambda p: p['price']['kwh2000']
        )

        scratch_all    = os.path.join(self.scratch_pad, 'market_plans.json')
        scratch_latest = os.path.join(self.scratch_pad, 'latest_plans.json')
        with open(scratch_all, 'w') as f:
            json.dump([{k: str(v) if isinstance(v, datetime) else v for k, v in p.items() if k != '_id'}
                    for p in cursor], f, indent=2)
        with open(scratch_latest, 'w') as f:
            json.dump([{k: str(v) if isinstance(v, datetime) else v for k, v in p.items() if k != '_id'}
                    for p in plans_latest], f, indent=2)

        return cursor, plans_latest

    def fetchEflText(self, url: str, slug: str):
        '''
        Download the EFL at `url` and return its plain text content.
        PDFs are converted via pdftotext. HTML has tags stripped.
        Saves raw file and extracted text to the scratch pad.
        Returns None on any failure (plan should be disqualified).
        '''
        try:
            resp = requests.get(url, timeout=30, allow_redirects=True)
            if resp.status_code != 200:
                log.warning('EFL fetch returned HTTP %d for %s', resp.status_code, url)
                return None

            content_type = resp.headers.get('content-type', '').lower()
            is_pdf = 'pdf' in content_type or resp.content[:4] == b'%PDF'

            if is_pdf:
                raw_path = os.path.join(self.scratch_pad, f'efl_{slug}.pdf')
                with open(raw_path, 'wb') as f:
                    f.write(resp.content)
                result = subprocess.run(
                    ['pdftotext', raw_path, '-'],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    log.warning('pdftotext failed (rc=%d) for %s', result.returncode, url)
                    return None
                text = result.stdout
            else:
                raw_path = os.path.join(self.scratch_pad, f'efl_{slug}.html')
                with open(raw_path, 'wb') as f:
                    f.write(resp.content)
                text = re.sub(r'<[^>]+>', ' ', resp.text)
                text = re.sub(r'\s+', ' ', text)

            txt_path = os.path.join(self.scratch_pad, f'efl_{slug}.txt')
            with open(txt_path, 'w') as f:
                f.write(text)
            return text

        except Exception as exc:
            log.warning('Exception fetching EFL %s: %s', url, exc)
            return None

    def parseEflPricing(self, text: str):
        '''
        Extract billing components from EFL plain text.
        Returns dict with keys: energy_rate, base_fee, tdsp_kwh, tdsp_base, net_credit
        (all in ¢/kWh for rates, $/month for fees).
        Returns None if energy_rate cannot be determined.
        '''
        energy_match = _RE_ENERGY.search(text)
        if not energy_match:
            return None
        energy_rate = float(energy_match.group(1))
        if energy_rate < 1.0:   # dollars/kWh → convert to cents
            energy_rate *= 100.0

        base_match = _RE_BASE.search(text)
        base_fee = float(base_match.group(1)) if base_match else 0.0

        tdsp_kwh_match = _RE_TDSP_KWH.search(text)
        tdsp_kwh = float(tdsp_kwh_match.group(1)) if tdsp_kwh_match else 0.0

        tdsp_base_match = _RE_TDSP_BASE.search(text)
        tdsp_base = float(tdsp_base_match.group(1)) if tdsp_base_match else 0.0

        credit_match = _RE_CREDIT.search(text)
        net_credit = float(credit_match.group(1)) if credit_match else 0.0

        return {
            'energy_rate': energy_rate,
            'base_fee':    base_fee,
            'tdsp_kwh':    tdsp_kwh,
            'tdsp_base':   tdsp_base,
            'net_credit':  net_credit,
        }

    def monthlyBill(self, pricing: dict, kwh: float) -> float:
        '''Compute total monthly bill in dollars for a given usage level.'''
        per_kwh = pricing['energy_rate'] + pricing['tdsp_kwh']
        fixed   = pricing['base_fee'] + pricing['tdsp_base'] - pricing['net_credit']
        return per_kwh * kwh / 100.0 + fixed

    def estimateAnnualCost(self, pricing: dict, monthly_usage: dict):
        '''
        Compute estimated annual cost and per-month breakdown using confirmed EFL pricing
        applied to actual historical usage.
        Returns (annual_dollars, {mm: {kwh, bill, eff_rate_cents}}).
        '''
        monthly = {}
        for mm, kwh in sorted(monthly_usage.items()):
            bill = self.monthlyBill(pricing, kwh)
            eff  = (bill / kwh * 100.0) if kwh > 0 else 0.0
            monthly[mm] = {
                'kwh':            round(kwh, 1),
                'bill':           round(bill, 2),
                'eff_rate_cents': round(eff, 3),
            }
        annual = sum(v['bill'] for v in monthly.values())
        return round(annual, 2), monthly

    def marketTrend(self, plans_all: list) -> dict:
        '''
        Group all plans by discovery month and compute market rate statistics.
        Returns {YYYY-MM: {avg_kwh1000, min_kwh1000, avg_kwh2000, min_kwh2000, plans_scraped}}.
        '''
        by_month = defaultdict(list)
        for p in plans_all:
            month_key = p['discovered_at'].strftime('%Y-%m')
            by_month[month_key].append(p['price'])

        trend = {}
        for month, prices in sorted(by_month.items()):
            kwh1000 = [p['kwh1000'] for p in prices]
            kwh2000 = [p['kwh2000'] for p in prices]
            trend[month] = {
                'plans_scraped': len(prices),
                'avg_kwh1000':   round(sum(kwh1000) / len(kwh1000), 2),
                'min_kwh1000':   min(kwh1000),
                'avg_kwh2000':   round(sum(kwh2000) / len(kwh2000), 2),
                'min_kwh2000':   min(kwh2000),
            }
        return trend

    def generateReport(
        self,
        ranked: list,
        monthly_usage: dict,
        trend: dict,
        current_rate: float,
        renewal_rate: float
    ) -> str:
        '''
        Produce the full Markdown report string.
        '''
        annual_kwh   = sum(monthly_usage.values())
        current_ann  = annual_kwh * current_rate / 100.0
        renewal_ann  = annual_kwh * renewal_rate / 100.0

        lines = []

        # ── Header ──────────────────────────────────────────────────────────────
        lines += [
            '# Electricity Plan Comparison Report',
            '',
            f'**Generated:** {datetime.now().strftime("%B %d, %Y")}  ',
            f'**Current plan rate:** {current_rate}¢/kWh  ',
            f'**Renewal offer rate:** {renewal_rate}¢/kWh',
            '',
        ]

        # ── Usage Profile ────────────────────────────────────────────────────────
        lines += [
            '## Usage Profile',
            '',
            f'- **Annual total:** {annual_kwh:,.1f} kWh/year',
            f'- **Average monthly:** {annual_kwh/12:,.1f} kWh/month',
            '',
            '| Month | Avg kWh |',
            '|-------|---------|',
        ]
        for mm, kwh in sorted(monthly_usage.items()):
            lines.append(f'| {MONTH_NAMES[mm]} | {kwh:,.1f} |')
        lines.append('')

        # ── Market Rate Trend ─────────────────────────────────────────────────────
        lines += [
            '## Market Rate Trend',
            '',
            '| Month | Plans | Avg @1000 kWh | Min @1000 kWh | Avg @2000 kWh | Min @2000 kWh |',
            '|-------|-------|---------------|---------------|---------------|---------------|',
        ]
        for month, d in sorted(trend.items()):
            lines.append(
                f'| {month} | {d["plans_scraped"]} | {d["avg_kwh1000"]}¢ | {d["min_kwh1000"]}¢'
                f' | {d["avg_kwh2000"]}¢ | {d["min_kwh2000"]}¢ |'
            )
        lines.append('')

        # ── Current vs Renewal ────────────────────────────────────────────────────
        lines += [
            '## Current Plan vs Renewal Offer',
            '',
            '| Plan | Rate | Est. Annual Cost | vs Current |',
            '|------|------|-----------------|------------|',
            f'| Current plan | {current_rate}¢ flat | **${current_ann:,.2f}** | baseline |',
            f'| Renewal offer | {renewal_rate}¢ flat | **${renewal_ann:,.2f}** |'
            f' +${renewal_ann - current_ann:,.2f}/yr (+{(renewal_rate/current_rate-1)*100:.1f}%) |',
            '',
            f'> **Accepting the renewal would cost an additional ${renewal_ann - current_ann:,.2f}/year.**',
            '',
        ]

        # ── Top N Plans ───────────────────────────────────────────────────────────
        lines.append('## Top 5 Cheapest Available Plans')
        lines.append('')
        lines.append('Costs calculated from confirmed EFL pricing applied to 3-year average usage.')
        lines.append('')

        for i, plan in enumerate(ranked, 1):
            p        = plan['pricing']
            annual   = plan['annual']
            monthly  = plan['monthly']
            eff_ann  = annual / annual_kwh * 100.0
            sv_curr  = current_ann - annual
            sv_renew = renewal_ann - annual
            per_kwh  = p['energy_rate'] + p['tdsp_kwh']
            fixed    = p['base_fee'] + p['tdsp_base'] - p['net_credit']
            etf      = f'${plan["term_value"]}mo contract' if plan.get('term_value') else ''

            lines += [
                f'### {i}. {plan["company_name"]} — {plan["plan_name_clean"]}',
                '',
                f'- **Estimated annual cost:** ${annual:,.2f}',
                f'- **Effective avg rate:** {eff_ann:.3f}¢/kWh',
                f'- **vs Current ({current_rate}¢):** {"SAVES" if sv_curr > 0 else "COSTS"} ${abs(sv_curr):,.2f}/yr',
                f'- **vs Renewal ({renewal_rate}¢):** saves ${sv_renew:,.2f}/yr',
                f'- **Contract term:** {plan.get("term_value", "?")} months',
                f'- **Rate structure:** {per_kwh:.4f}¢/kWh (energy+TDU) + ${fixed:.2f}/month fixed',
                f'- **EFL:** {plan["fact_sheet"]}',
                '',
                '#### Monthly Cost Breakdown',
                '',
                '| Month | Avg kWh | Rate (¢/kWh) | Monthly Bill | vs Current |',
                '|-------|---------|-------------|-------------|------------|',
            ]
            for mm, d in sorted(monthly.items()):
                curr_bill = monthly_usage[mm] * current_rate / 100.0
                diff      = d['bill'] - curr_bill
                sign      = '+' if diff >= 0 else '-'
                lines.append(
                    f'| {MONTH_NAMES[mm]} | {d["kwh"]:,.1f} | {d["eff_rate_cents"]:.2f}¢'
                    f' | ${d["bill"]:,.2f} | {sign}${abs(diff):.2f} |'
                )
            lines += [
                f'| **Annual Total** | **{annual_kwh:,.1f}** | **{eff_ann:.2f}¢**'
                f' | **${annual:,.2f}** |'
                f' **{"+" if sv_curr <= 0 else "-"}${abs(sv_curr):,.2f}** |',
                '',
            ]

        # ── Summary Table ─────────────────────────────────────────────────────────
        lines += [
            '## Summary Comparison',
            '',
            '| Rank | Plan | Annual Cost | Eff. Rate | vs Current | vs Renewal | Term |',
            '|------|------|-------------|-----------|------------|------------|------|',
            f'| — | Current ({current_rate}¢ flat) | ${current_ann:,.2f} | {current_rate:.2f}¢'
            f' | baseline | saves ${renewal_ann - current_ann:,.2f} | — |',
        ]
        for i, plan in enumerate(ranked, 1):
            eff = plan['annual'] / annual_kwh * 100.0
            sv  = current_ann - plan['annual']
            svr = renewal_ann - plan['annual']
            lines.append(
                f'| {i} | {plan["company_name"]} {plan["plan_name_clean"]}'
                f' | ${plan["annual"]:,.2f} | {eff:.2f}¢'
                f' | {"+" if sv < 0 else "-"}${abs(sv):,.2f}'
                f' | saves ${svr:,.2f}'
                f' | {plan.get("term_value", "?")}mo |'
            )
        lines += [
            f'| — | Renewal ({renewal_rate}¢ flat) | ${renewal_ann:,.2f} | {renewal_rate:.2f}¢'
            f' | +${renewal_ann - current_ann:,.2f} | — | — |',
            '',
        ]

        # ── Recommendation ────────────────────────────────────────────────────────
        cheapest = ranked[0]
        gap = current_ann - cheapest['annual']
        lines += [
            '## Recommendation',
            '',
        ]
        if gap > 0:
            lines.append(
                f'The cheapest available plan (**{cheapest["company_name"]} {cheapest["plan_name_clean"]}**) '
                f'saves ${gap:,.2f}/yr vs your current rate.'
            )
        else:
            lines.append(
                f'**Your current {current_rate}¢/kWh rate is the cheapest option available today.** '
                f'No plan in this market snapshot beats it on all-in annual cost for your usage profile.'
            )
            lines.append(
                f'The closest competitor is **{cheapest["company_name"]} {cheapest["plan_name_clean"]}** '
                f'at ${cheapest["annual"]:,.2f}/yr — only ${abs(gap):,.2f}/yr more expensive.'
            )
        lines += [
            '',
            f'**Do not accept the {renewal_rate}¢ renewal offer** — it costs '
            f'${renewal_ann - current_ann:,.2f}/yr more than your current plan.',
            '',
        ]

        return '\n'.join(lines) + '\n'

    def _printSummary(
        self,
        ranked: list,
        monthly_usage: dict,
        current_rate: float,
        renewal_rate: float,
    ):
        '''Print a compact rank table to stdout.'''
        annual_kwh  = sum(monthly_usage.values())
        current_ann = annual_kwh * current_rate / 100.0
        renewal_ann = annual_kwh * renewal_rate / 100.0

        print(f'\nAnnual usage: {annual_kwh:,.1f} kWh  |  avg monthly: {annual_kwh/12:,.1f} kWh')
        print(f'Current plan:  ${current_ann:,.2f}/yr  ({current_rate}¢ flat)')
        print(f'Renewal offer: ${renewal_ann:,.2f}/yr  ({renewal_rate}¢ flat)  — ${renewal_ann - current_ann:,.2f} MORE')
        print()
        print(f'{"Rank":<5} {"Annual$":>9} {"Eff¢":>7} {"vs Current":>12} {"vs Renewal":>12}  Plan')
        print('-' * 88)
        for i, plan in enumerate(ranked, 1):
            eff  = plan['annual'] / annual_kwh * 100.0
            sv   = plan['annual'] - current_ann
            svr  = renewal_ann - plan['annual']
            sign = '+' if sv >= 0 else '-'
            print(
                f'{i:<5} ${plan["annual"]:>8,.2f} {eff:>6.2f}¢ {sign}${abs(sv):>10,.2f}'
                f' saves ${svr:>9,.2f}  {plan["company_name"]} — {plan["plan_name_clean"]}'
            )
        print()

    def run(self, since_providers: datetime, since_meter_reads: datetime,
            current_rate: float, renewal_rate: float, output_path: str) -> int:
        '''
        Full pipeline: query MongoDB → fetch EFLs → parse pricing → rank → write report.
        '''
        monthly_usage          = self.getMonthlyUsage(since_meter_reads)
        plans_all, candidates  = self.getProviderPlans(since_providers)
        trend                  = self.marketTrend(plans_all)
        ranked                 = []

        for plan in candidates[:CANDIDATE_POOL]:
            cname = plan['company_name']
            slug  = f'{plan["plan_id"]}_{re.sub(r"[^A-Za-z0-9]", "_", cname)[:20]}'

            text = self.fetchEflText(plan['fact_sheet'], slug)
            if text is None:
                log.warning(
                    'Disqualifying %s (%s) — EFL fetch failed. '
                    'P2C rates were kwh500=%.1f kwh1000=%.1f kwh2000=%.1f',
                    cname, plan['fact_sheet'],
                    plan['price']['kwh500'], plan['price']['kwh1000'], plan['price']['kwh2000']
                )
                continue

            pricing = self.parseEflPricing(text)
            if pricing is None:
                log.warning(
                    'Disqualifying %s (%s) — EFL text parsed but energy rate not found. '
                    'P2C rates were kwh500=%.1f kwh1000=%.1f kwh2000=%.1f',
                    cname, plan['fact_sheet'],
                    plan['price']['kwh500'], plan['price']['kwh1000'], plan['price']['kwh2000']
                )
                continue

            annual, monthly = self.estimateAnnualCost(pricing, monthly_usage)
            ranked.append({
                'company_name':   cname,
                'plan_name_clean':plan['plan_name'],
                'term_value':     plan.get('term_value'),
                'prepaid':        plan.get('prepaid', False),
                'timeofuse':      plan.get('timeofuse', False),
                'fact_sheet':     plan['fact_sheet'],
                'website':        plan.get('website', ''),
                'pricing':        pricing,
                'annual':         annual,
                'monthly':        monthly,
            })
            log.info('Qualified: %s — estimated $%.2f/yr', cname, annual)

            if len(ranked) == TOP_N:
                break

        if not ranked:
            log.error('No plans could be qualified. Check EFL URLs and pdftotext availability.')
            return 1

        ranked.sort(key=lambda x: x['annual'])

        scratch_ranked = os.path.join(self.scratch_pad, 'ranked_plans.json')
        with open(scratch_ranked, 'w') as f:
            json.dump(ranked, f, indent=2)
        log.info('Ranked plan data written to %s', scratch_ranked)

        report = self.generateReport(ranked, monthly_usage, trend, current_rate, renewal_rate)
        with open(output_path, 'w') as f:
            f.write(report)
        log.info('Report written to %s', output_path)

        self._printSummary(ranked, monthly_usage, current_rate, renewal_rate)
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog='smtx-reconcile',
        description='Compare electricity provider plans against real meter usage and produce a ranked report.',
    )
    parser.add_argument('--since-providers',   default='3 months',
                        help='How far back to look for provider plan data (default: "3 months")')
    parser.add_argument('--since-meter-reads', default='3 years',
                        help='How far back to look for meter reads (default: "3 years")')
    parser.add_argument('-o', '--output', default='results.md',
                        help='Output Markdown file path (default: results.md)')
    parser.add_argument('--scratch-pad', default=None,
                        help='Directory for intermediate artifacts. Defaults to smtx-data-<YYYY-MM-DD-HHMM>/ in CWD.')
    parser.add_argument('--current-rate', type=float, default=None,
                        help='Your current rate in ¢/kWh (prompted interactively if omitted)')
    parser.add_argument('--renewal-rate', type=float, default=None,
                        help='Renewal offer rate in ¢/kWh (prompted interactively if omitted)')
    args = parser.parse_args()

    if args.current_rate is None:
        if sys.stdin.isatty():
            args.current_rate = float(input('Your current rate (¢/kWh): '))
        else:
            log.error('--current-rate is required in non-interactive mode')
            return 2

    if args.renewal_rate is None:
        if sys.stdin.isatty():
            args.renewal_rate = float(input('Renewal offer rate (¢/kWh): '))
        else:
            log.error('--renewal-rate is required in non-interactive mode')
            return 2

    scratch_pad = args.scratch_pad or f'smtx-data-{datetime.now().strftime("%Y-%m-%d-%H%M")}'

    since_providers   = dateparser.parse(f'{args.since_providers} ago')
    since_meter_reads = dateparser.parse(f'{args.since_meter_reads} ago')

    log.info('Provider plans since: %s', since_providers.strftime('%F'))
    log.info('Meter reads since:    %s', since_meter_reads.strftime('%F'))
    log.info('Scratch pad:          %s', scratch_pad)

    reconciler = SmtxReconciler(scratch_pad)
    try:
        return reconciler.run(
            since_providers,
            since_meter_reads,
            args.current_rate,
            args.renewal_rate,
            args.output
        )
    finally:
        reconciler.close()

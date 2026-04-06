# smtx-reconcile

Compares available electricity provider plans from the Power to Choose database against your
real meter usage history stored in MongoDB. Produces a Markdown report ranking plans by
estimated annual cost using confirmed EFL (Electricity Facts Label) pricing.

## Prerequisites

- `smtx-fetch` must have been run to populate the `dailyReads` MongoDB collection
- `smtx-power2choose` must have been run to populate the `power2choose` MongoDB collection
- `pdftotext` must be installed for PDF EFL parsing: `apt install poppler-utils`

## CLI Arguments

- `--since-providers` — How far back to look for provider plans (default: `3 months`)
- `--since-meter-reads` — How far back to use meter reads for usage profile (default: `3 years`)
- `-o / --output` — Output file path for the Markdown report (default: `results.md`)
- `--scratch-pad` — Directory to store intermediate artifacts (default: `smtx-data-<YYYY-MM-DD-HHMM>/`)
- `--current-rate` — Your current plan rate in ¢/kWh (prompted interactively if omitted)
- `--renewal-rate` — Renewal offer rate in ¢/kWh (prompted interactively if omitted)

## Interactive Mode

If `--current-rate` and `--renewal-rate` are omitted and stdin is a TTY, the command will
prompt for them interactively. In non-interactive / cron mode both flags are required.

## Example

```bash
smtx-reconcile --since-providers='3 months' --since-meter-reads='3 years' \
    --current-rate=12.0 --renewal-rate=14.0 -o results.md
```

## Scratch Pad Artifacts

The scratch pad directory contains intermediate files useful for debugging:

| File | Contents |
|------|----------|
| `monthly_usage.json` | Average kWh per calendar month derived from meter reads |
| `market_plans.json` | All power2choose plans in the date window |
| `latest_plans.json` | Most-recent scrape's plans sorted by kwh2000 ascending |
| `efl_<slug>.pdf` or `.html` | Raw downloaded EFL document |
| `efl_<slug>.txt` | Extracted text from the EFL |
| `ranked_plans.json` | Final ranked plans with confirmed EFL pricing and cost breakdown |

## EFL Parsing

`smtx-reconcile` fetches each candidate plan's Electricity Facts Label (EFL) directly and
extracts the energy charge, base fee, TDU delivery charges, and any bill credits using
PUCT-standardized label formats.

Plans whose EFL cannot be fetched or parsed are disqualified with a warning log entry.
No interpolation fallback is used — only plans with confirmed EFL pricing are ranked.

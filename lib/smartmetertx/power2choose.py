'''
smtx-power2choose

Fetches electricity plan listings from the Power to Choose API and inserts them into
the configured MongoDB `power2choose` collection. Intended to run daily via cron.
Sends an SNS error alert via NotifyHelper if the fetch or insert fails.
'''
import argparse
from base64 import b64encode
import json
from datetime import datetime, timezone
from hashlib import sha1

import requests
import pymongo

import kizano
from smartmetertx import notify, schema, utils

log = kizano.getLogger(__name__)

P2C_URL = 'http://api.powertochoose.org/api/PowerToChoose/plans'

# Default API query parameters — overridden by config['smartmetertx']['power2choose']
# and further overridden by CLI flags.
DEFAULT_PARAMS = {
    'estimated_use':       '2000',
    'plan_mo_from':        '10',
    'plan_mo_to':          '24',
    'plan_type':           '1',
    'timeofuse':           'off',
    'renewable_energy_id': '10',
}

class Power2ChooseFetcher:
    '''
    Fetches Power to Choose plan listings and stores them in MongoDB.
    Mirrors the n8n workflow logic as a native Python CLI command.
    '''

    def __init__(self):
        self.config = kizano.getConfig()
        self.notify = notify.NotifyHelper()
        self.mongo  = utils.getMongoConnection(self.config)
        self.db     = self.mongo.get_database(self.config['mongo'].get('dbname', 'smartmetertx'))
        self.collection = self.db[schema.POWER2CHOOSE]

    def close(self):
        if self.mongo:
            self.mongo.close()
            self.mongo = None

    def buildParams(self, cli_overrides: dict) -> dict:
        '''
        Merge parameter priority: defaults < config file < CLI flags.
        Config lives under config['smartmetertx']['power2choose'].
        '''
        params = dict(DEFAULT_PARAMS)
        cfg_p2c = self.config.get('smartmetertx', {}).get('power2choose', {})
        params.update({k: str(v) for k, v in cfg_p2c.items() if v is not None})
        params.update({k: str(v) for k, v in cli_overrides.items() if v is not None})
        return params

    def fetchPlans(self, params: dict) -> list:
        '''
        POST to the Power to Choose API and return the raw plan list.
        Raises on HTTP errors or missing/empty data payload.
        '''
        log.info('Fetching plans from Power to Choose API (zip=%s)...', params.get('zip_code'))
        resp = requests.post(
            P2C_URL,
            data=params,
            headers={'Accept': 'application/json'},
            timeout=60,
        )
        resp.raise_for_status()
        body = resp.json()
        plans = body.get('data', [])
        if not plans:
            raise ValueError(f'Power to Choose API returned 0 plans (full response: {body})')
        log.info('Received %d plans from API.', len(plans))
        return plans

    def insertPlans(self, plans: list) -> int:
        '''
        Bulk-insert mapped plan documents into MongoDB.
        Duplicate key errors (code 11000) are silently skipped; other errors are re-raised.
        Returns the number of successfully inserted documents.
        '''
        log.info('Inserting %d plan documents into MongoDB...', len(plans))
        try:
            result = self.collection.insert_many(plans, ordered=False)
            inserted = len(result.inserted_ids)
            log.info('Inserted %d new plan documents.', inserted)
            return inserted
        except pymongo.errors.BulkWriteError as exc:
            non_dup_errors = [e for e in exc.details['writeErrors'] if e['code'] != 11000]
            if non_dup_errors:
                raise RuntimeError(f'MongoDB write errors: {non_dup_errors}') from exc
            inserted = exc.details.get('nInserted', 0)
            log.info(f'Inserted {inserted} new plan documents ({len(exc.details["writeErrors"])} duplicates skipped).')
            return inserted

    def run(self, cli_overrides: dict) -> int:
        '''
        Full pipeline: build params → fetch API → map documents → insert into MongoDB.
        '''
        params       = self.buildParams(cli_overrides)
        discovered_at = datetime.now(tz=timezone.utc)

        raw_plans = self.fetchPlans(params)
        # Associate a unique ID with all of these discovered other than the date.
        batch_id = b64encode(sha1((discovered_at.strftime('%s') + json.dumps(raw_plans)).encode('utf-8')).digest()).decode('utf-8')
        mapped    = [schema.castPlan(p, batch_id, discovered_at) for p in raw_plans]
        inserted  = self.insertPlans(mapped)

        log.info(f'Power to Choose fetch complete: {inserted}/{len(mapped)} plans stored for {discovered_at.strftime("%F")} with Batch ID {batch_id}.')
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog='smtx-power2choose',
        description='Fetch Power to Choose plan listings and store them in MongoDB.',
    )
    parser.add_argument('--zip-code',            default=None,
                        help='Service zip code (overrides config)')
    parser.add_argument('--min-term',            default=None, type=int,
                        dest='plan_mo_from',
                        help='Minimum plan term in months (overrides config)')
    parser.add_argument('--max-term',            default=None, type=int,
                        dest='plan_mo_to',
                        help='Maximum plan term in months (overrides config)')
    parser.add_argument('--plan-type',           default=None, type=int,
                        help='Plan type filter: 1=fixed (overrides config)')
    parser.add_argument('--renewable-energy-id', default=None, type=int,
                        help='Renewable energy filter ID (overrides config)')
    args = parser.parse_args()

    cli_overrides = {
        k: v for k, v in {
            'zip_code':            args.zip_code,
            'plan_mo_from':        args.plan_mo_from,
            'plan_mo_to':          args.plan_mo_to,
            'plan_type':           args.plan_type,
            'renewable_energy_id': args.renewable_energy_id,
        }.items() if v is not None
    }

    fetcher = Power2ChooseFetcher()
    try:
        return fetcher.run(cli_overrides)
    except Exception as exc:
        errmsg = f'smtx-power2choose failed: {exc}'
        log.error(errmsg)
        fetcher.notify.error('Power to Choose Fetch Failed', errmsg)
        return 1
    finally:
        fetcher.close()

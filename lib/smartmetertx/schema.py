'''
smartmetertx.schema

Single source of truth for MongoDB collection names, document shapes (TypedDicts),
type-coercion/cast functions, and index definitions.

All modules that read from or write to MongoDB should import collection names and
use the cast functions from here rather than scattering magic strings or inline
type-coercion throughout the codebase.
'''
from datetime import datetime
from typing import TypedDict

import dateparser

# ── Collection names ─────────────────────────────────────────────────────────

DAILY_READS    = 'dailyReads'
INTERVAL_READS = 'interval15minReads'
METER_READS    = 'meterReads'
POWER2CHOOSE   = 'power2choose'

# ── Document shapes ───────────────────────────────────────────────────────────

class DailyRead(TypedDict):
    readDate:      datetime
    revisionDate:  datetime
    startReading:  float
    endReading:    float
    energyDataKwh: float


class IntervalRead(TypedDict):
    readingDate:  datetime
    revisionDate: datetime
    readingType:  str
    readingData:  list  # list of (kWh: float, readingType: str) tuples


class PriceBreakdown(TypedDict):
    kwh500:  float
    kwh1000: float
    kwh2000: float


class Power2ChoosePlan(TypedDict):
    plan_id:         int
    company_id:      str
    company_name:    str
    plan_name:       str
    website:         str
    price:           PriceBreakdown
    pricing_details: str
    tos:             str
    fact_sheet:      str
    prepaid:         bool
    timeofuse:       bool
    min_usage:       bool
    rating_total:    float
    rating_count:    int
    promotions:      str
    term_value:      int
    special_terms:   str
    discovered_at:   datetime


# ── Cast / coerce functions ───────────────────────────────────────────────────

def castDailyRead(raw: dict) -> DailyRead:
    '''
    Coerce a raw daily-read dict (as returned by the SmartMeterTexas API) into a
    properly typed DailyRead document ready for MongoDB insertion.

    API date formats: readDate='MM/DD/YYYY', revisionDate='MM/DD/YYYY HH:MM:SS'
    '''
    return {
        'readDate':      datetime.strptime(raw['readDate'], '%m/%d/%Y'),
        'revisionDate':  datetime.strptime(raw['revisionDate'], '%m/%d/%Y %H:%M:%S'),
        'startReading':  float(raw['startReading']),
        'endReading':    float(raw['endReading']),
        'energyDataKwh': float(raw['energyDataKwh']),
    }


def castIntervalRead(raw: dict) -> IntervalRead:
    '''
    Coerce a raw 15-minute interval-read dict (as returned by the SmartMeterTexas
    API) into a properly typed IntervalRead document ready for MongoDB insertion.

    The 'RD' field contains comma-separated 'value-type' pairs, e.g. '0.155-A,0.474-A'.
    Empty entries are skipped; bare '-' entries are stored as (0.0, 'X').
    '''
    readings = []
    for entry in raw['RD'].split(','):
        if not entry:
            continue
        if entry == '-':
            readings.append((0.0, 'X'))
            continue
        reading_val, reading_type = entry.split('-')
        readings.append((float(reading_val), reading_type))
    return {
        'readingDate':  dateparser.parse(raw['DT']),
        'revisionDate': dateparser.parse(raw['RevTS']),
        'readingType':  raw['RT'],
        'readingData':  readings,
    }


def castPlan(raw: dict, discovered_at: datetime) -> Power2ChoosePlan:
    '''
    Map a raw Power to Choose API response record to the MongoDB Power2ChoosePlan
    document schema, coercing all fields to their correct types.

    API field names differ from the stored names in a few cases:
        terms_of_service → tos
        minimum_usage    → min_usage
        price_kwh*       → price.kwh*
    '''
    return {
        'plan_id':         int(raw['plan_id']),
        'company_id':      str(raw.get('company_id', '')),
        'company_name':    str(raw.get('company_name', '')),
        'plan_name':       str(raw.get('plan_name', '')),
        'website':         str(raw.get('website', '')),
        'price': {
            'kwh500':  float(raw.get('price_kwh500', 0)),
            'kwh1000': float(raw.get('price_kwh1000', 0)),
            'kwh2000': float(raw.get('price_kwh2000', 0)),
        },
        'pricing_details': str(raw.get('pricing_details', '')),
        'tos':             str(raw.get('terms_of_service', '')),
        'fact_sheet':      str(raw.get('fact_sheet', '')),
        'prepaid':         bool(raw.get('prepaid', False)),
        'timeofuse':       bool(raw.get('timeofuse', False)),
        'min_usage':       bool(raw.get('minimum_usage', False)),
        'rating_total':    float(raw.get('rating_total', 0)),
        'rating_count':    int(raw.get('rating_count', 0)),
        'promotions':      str(raw.get('promotions', '')),
        'term_value':      int(raw.get('term_value', 0)),
        'special_terms':   str(raw.get('special_terms', '')),
        'discovered_at':   discovered_at,
    }


# ── Index definitions ─────────────────────────────────────────────────────────
# Each entry: {'keys': [(field, direction), ...], ...pymongo create_index kwargs}

DAILY_READ_INDEXES = [
    {'keys': [('revisionDate', 1)], 'background': True},
    {'keys': [('readDate', 1)],     'background': True, 'unique': True},
]

INTERVAL_READ_INDEXES = [
    {'keys': [('readingDate', 1)],  'background': True, 'unique': True},
    {'keys': [('revisionDate', 1)], 'background': True, 'unique': True},
]

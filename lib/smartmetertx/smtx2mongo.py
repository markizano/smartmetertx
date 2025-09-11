'''
\x1b[31mModule-Level Documentation!\x1b[0m
'''
import os
import dateparser
import pymongo
import json
from datetime import datetime

from kizano import getConfig, getLogger
from smartmetertx.api import MeterReader
from smartmetertx.notify import NotifyHelper
from smartmetertx.utils import getMongoConnection

log = getLogger(__name__)
HOME = os.getenv('HOME', '')
SMTX_FROM   = dateparser.parse(os.environ.get('SMTX_FROM', 'day before yesterday'))
SMTX_TO     = dateparser.parse(os.environ.get('SMTX_TO', 'today'))

class Smtx2Mongo(object):
    '''
    SmartMeterTexas -> MongoDB
    Model object to take the records we get from https://smartmetertexas.com and insert them into
    a mongodb we control for data preservation and other analytics on our electric usage data we
    would want to undertake.
    '''

    def __init__(self):
        self.config = getConfig()
        self.notify = NotifyHelper()
        self.mongo = getMongoConnection(self.config)
        self.db = self.mongo.get_database(self.config['mongo'].get('dbname', 'smartmetertx'))
        self.dailyReads = self.db.dailyReads
        self.interval15minReads = self.db.interval15minReads
        self.getSMTX()
        self.ensureIndexes()

    def close(self):
        if self.mongo:
            self.mongo.close()
            self.mongo = None

    def ensureIndexes(self):
        self.dailyReads.create_index(
            [('revisionDate', 1)],
            background=True,
        )
        self.dailyReads.create_index(
            [('readDate', 1)],
            background=True,
            unique=True,
        )
        self.interval15minReads.create_index(
            [('readingDate', 1)],
            background=True,
            unique=True,
        )
        self.interval15minReads.create_index(
            [('revisionDate', 1)],
            background=True,
            unique=True,
        )
        return self

    def getSMTX(self):
        log.info('Connecting to SmartMeterTX...')
        self.smtx = MeterReader()
        log.info('Success!')
        return self.smtx

    def getDailyReads(self):
        # Get the meter reads and print the date in the format their API expects.
        log.info('Getting daily reads from SmartMeterTX API...')
        reads = self.smtx.get_daily_read(self.config['smartmetertx']['esiid'], SMTX_FROM.strftime('%m/%d/%Y'), SMTX_TO.strftime('%m/%d/%Y'))
        log.info('Acquired %d meter reads!' % len(reads['registeredReads']))
        return reads

    def get15minReads(self):
        log.info('Getting 15min reads from SmartMeterTX API...')
        reads = self.smtx.get_15min_reads(self.config['smartmetertx']['esiid'], SMTX_FROM.strftime('%m/%d/%Y'), SMTX_TO.strftime('%m/%d/%Y'))
        log.info('Acquired %d meter reads!' % len(reads['energyData']))
        return reads

    def typecastDailyReads(self, dailyData: list[dict]) -> list[dict]:
        '''
        Convert strings to proper data types to store in DB.
        Feb-2024 update data structure:

        {
            "trans_id": "00000000000000000",
            "esiid": "0000000000000000000",
            "registeredReads": [{
                "readDate": "01/01/2024",
                "revisionDate": "01/02/2024 00:00:00",
                "startReading": "0000.000",
                "endReading": "0000.000",
                "energyDataKwh": "00.000"
            }]
        }
        '''
        results = []
        for meterRead in dailyData:
            meterRead['readDate'] = datetime.strptime(meterRead['readDate'], '%m/%d/%Y')
            meterRead['revisionDate'] = datetime.strptime(meterRead['revisionDate'], '%m/%d/%Y %H:%M:%S')
            meterRead['startReading'] = float(meterRead['startReading'])
            meterRead['endReading'] = float(meterRead['endReading'])
            meterRead['energyDataKwh'] = float(meterRead['energyDataKwh'])
            results.append(meterRead)
        log.debug(json.dumps(dailyData, indent=2, default=str))
        return results

    def typecast15minReads(self, interval15Data: list[dict]) -> list[dict]:
        '''
        Convert strings to proper date types to store in DB.
        Sample data structure:

        {
            "trans_id": "whateveryouputfortxnid",
            "esiid": "00000000000000000",
            "energyData": [
                {
                    "DT": "09/01/2025",
                    "RevTS": "09/02/2025 06:21:18",
                    "RT": "C",
                    "RD": "0.155-A,0.474-A,0.282-A,0.304-A,0.286-A,0.293-A,0.294-A,0.310-A,,,,,0.394-A"
                }
            ]
        }

        "RD" field contains 100 comma-separated readings, but the 4 empty ones removed makes 96.
        It accounts for 2 hours between the break, so ... timezone offset?
        '''
        result = []
        log.debug(json.dumps(interval15Data, indent=2, default=str))
        # Re-map the keys to make them more descriptive.
        for energyData in interval15Data:
            remapped = {
                'readingDate': dateparser.parse(energyData['DT']),
                'revisionDate': dateparser.parse(energyData['RevTS']),
                'readingType': energyData['RT'],
                'readingData': [],
            }
            for readingData in energyData['RD'].split(','):
                if not readingData: continue
                if readingData == '-':
                    remapped['readingData'].append( (0.0, 'X') )
                    continue
                reading, readingType = readingData.split('-')
                reading = float(reading)
                remapped['readingData'].append( (reading, readingType) )
            result.append(remapped)
        return result

    def insertDailyData(self, dailyData):
        log.info('Inserting %d reads into the DB.' % len(dailyData))
        try:
            insertResult = self.dailyReads.insert_many(dailyData, ordered=False)
            log.debug(insertResult)
        except pymongo.errors.BulkWriteError as e:
            errs = list(filter( lambda x: x['code'] != 11000, e.details['writeErrors'] ))
            if errs:
                log.error('Failed to insert daily reads: %s' % errs)
                self.notify.error('SmartMeterTX to MongoDB Exception', f'Failed to insert daily reads into MongoDB:\n{errs}')
        log.info('Complete!')

    def insert15minData(self, interval15minData):
        log.info('Inserting %d 15min reads into the DB.' % len(interval15minData))
        try:
            insertResult = self.interval15minReads.insert_many(interval15minData, ordered=False)
            log.debug(insertResult)
        except pymongo.errors.BulkWriteError as e:
            errs = list(filter( lambda x: x['code'] != 11000, e.details['writeErrors'] ))
            if errs:
                log.error('Failed to insert 15min reads: %s' % errs)
                self.notify.error('SmartMeterTX to MongoDB Exception', f'Failed to insert 15min reads into MongoDB:\n{errs}')
        log.info('Complete!')

def main() -> int:
    log.info('Gathering records from %s to %s' % ( SMTX_FROM.strftime('%F/%R'), SMTX_TO.strftime('%F/%R') ) )
    smtx2mongo = Smtx2Mongo()
    try:
        dailyReads = smtx2mongo.getDailyReads()
        dailyData = smtx2mongo.typecastDailyReads(dailyReads['registeredReads'])
        if dailyData:
            smtx2mongo.insertDailyData(dailyData)
        else:
            log.warning('No daily reads inserted!')
    except Exception as e:
        errmsg = f'Global exception trying to insert daily reads into MongoDB:\n{e}\n'
        log.error(errmsg)
        smtx2mongo.notify.error('SmartMeterTX to MongoDB Exception', errmsg)
        return 1

    try:
        interval15minReads = smtx2mongo.get15minReads()
        interval15minData = smtx2mongo.typecast15minReads(interval15minReads['energyData'])
        if interval15minData:
            smtx2mongo.insert15minData(interval15minData)
        else:
            log.warning('No 15min reads inserted!')
    except Exception as e:
        errmsg = f'Global exception trying to insert 15min reads into MongoDB:\n{e}\n'
        log.error(errmsg)
        smtx2mongo.notify.error('SmartMeterTX to MongoDB Exception', errmsg)
        return 1

    smtx2mongo.close()
    return 0


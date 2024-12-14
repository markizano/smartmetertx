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
        self.collection = self.db.dailyReads
        self.getSMTX()
        self.ensureIndexes()

    def close(self):
      if self.mongo:
        self.mongo.close()
        self.mongo = None

    def ensureIndexes(self):
        self.collection.create_index(
            [('revisionDate', 1)],
            background=True
        )
        self.collection.create_index(
            [('readDate', 1)],
            background=True,
            unique=True
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
        if not reads:
            log.warning('Failed to get records from meterReads()')
            error = self.smtx.get_last_error()
            if error:
                self.notify.error('SmartMeterTX API Exception', 'Failed to get records from meterReads(): %s' % error)
        else:
            log.info('Acquired %d meter reads!' % len(reads['registeredReads']))
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
        log.debug(json.dumps(dailyData, indent=2, default=str))
        for meterRead in dailyData:
            meterRead['readDate'] = datetime.strptime(meterRead['readDate'], '%m/%d/%Y')
            meterRead['revisionDate'] = datetime.strptime(meterRead['revisionDate'], '%m/%d/%Y %H:%M:%S')
            meterRead['startReading'] = float(meterRead['startReading'])
            meterRead['endReading'] = float(meterRead['endReading'])
            results.append(meterRead)
        return results

    def insertDailyData(self, dailyData):
        results = []
        log.info('Inserting %d reads into the DB.' % len(dailyData))
        try:
            insertResult = self.collection.insert_many(dailyData)
            log.debug(insertResult)
            results.append(insertResult)
        except pymongo.errors.BulkWriteError as e:
            errs = list(filter( lambda x: x['code'] != 11000, e.details['writeErrors'] ))
            if errs:
                log.error('Failed to insert records: %s' % errs)
                self.notify.error('SmartMeterTX to MongoDB Exception', 'Failed to insert records into MongoDB:\n%s' % errs)
        log.info('Complete!')

def main() -> int:
    log.info('Gathering records from %s to %s' % ( SMTX_FROM.strftime('%F/%R'), SMTX_TO.strftime('%F/%R') ) )
    smtx2mongo = Smtx2Mongo()
    try:
        reads = smtx2mongo.getDailyReads()
        if not reads:
            log.error('Failed to read smartmetertexas API...')
            return 2

        dailyData = smtx2mongo.typecastDailyReads(reads['registeredReads'])
        if dailyData:
            smtx2mongo.insertDailyData(dailyData)
        else:
            log.warning('No records inserted!')
        smtx2mongo.close()
    except Exception as e:
        log.error('Failed to insert records into MongoDB: %s' % e)
        smtx2mongo.notify.error('SmartMeterTX to MongoDB Exception', 'Global exception trying to insert records into MongoDB:\n%s' % e)
        return 1
    return 0


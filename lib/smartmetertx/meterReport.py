'''
SMTX Meter Report

This script is used to generate a report of the daily meter reads from the SmartMeterTX API based
on what is stored in the MongoDB. Sends a report via AWS SNS to the configured topic.
'''

import os
import dateparser

from kizano import getConfig, getLogger
from smartmetertx.utils import getMongoConnection
from smartmetertx.notify import NotifyHelper

log = getLogger(__name__)
HOME = os.getenv('HOME', '')
SMTX_FROM   = dateparser.parse(os.environ.get('SMTX_FROM', 'day before yesterday'))
SMTX_TO     = dateparser.parse(os.environ.get('SMTX_TO', 'today'))

class SmartMeterTxMeterReport(object):

    def __init__(self):
        self.config = getConfig()
        self.notify = NotifyHelper()
        self.mongo = getMongoConnection(self.config)
        self.db = self.mongo.get_database(self.config['mongo'].get('dbname', 'smartmetertx'))
        self.collection = self.db.dailyReads

    def close(self):
        if self.mongo:
            self.mongo.close()
            self.mongo = None

    def getDailyReads(self):
        '''
        Get the meter reads for the date range specified in the environment variables.
        '''
        log.info('Getting daily reads from SmartMeterTX DB...')
        reads = self.collection.find({
            'readDate': {
                '$gte': SMTX_FROM,
                '$lte': SMTX_TO
            }
        }).sort('readDate', 1)
        if not reads:
            log.error('No records found for the date range specified.')
            return None
        result = []
        for reading in reads:
            reading['readDate'] = reading['readDate'].strftime('%F')
            reading['energyDataKwh'] = float(reading['energyDataKwh'])
            result.append(reading)
        return result

    def sendReport(self, reads):
        '''
        Send the report via AWS SNS.
        '''
        log.info('Sending report via AWS SNS...')
        report = '''
Daily Reads Report
==================

Date Range: %s to %s
    
''' % ( SMTX_FROM.strftime('%F'), SMTX_TO.strftime('%F') )
        total = 0.0
        for i, read in enumerate(reads):
            report += '%(readDate)s: %(energyDataKwh)03.3f kWh    ' % read
            if (i + 1) % 7 == 0:
                report += '\n'
            total += float(read['energyDataKwh'])
        report += "\n\nTotal Energy Use: %0.3f\n" % total
        log.debug(report)
        response = self.notify.info('SmartMeterTX Daily Reads Report', report)
        log.info(f'Report size in {len(report.encode("utf-8"))} bytes with {len(reads)} records and message id {response["MessageId"]}.')

def main() -> int:
    log.info('Gathering records from %s to %s' % ( SMTX_FROM.strftime('%F'), SMTX_TO.strftime('%F') ) )
    smtxReport = SmartMeterTxMeterReport()
    reads = smtxReport.getDailyReads()
    if not reads:
        log.error('Failed to read SmartMeterTX db...')
        return 2
    smtxReport.sendReport(reads)
    return 0


'''
SMTX Meter Report

This script is used to generate a report of the daily meter reads from the SmartMeterTX API based
on what is stored in the MongoDB. Sends a report via AWS SNS to the configured topic.
'''

import os
import dateparser
import pymongo
import boto3

from kizano import getConfig, getLogger
from smartmetertx.utils import getMongoConnection

log = getLogger(__name__)
HOME = os.getenv('HOME', '')
SMTX_FROM   = dateparser.parse(os.environ.get('SMTX_FROM', 'day before yesterday'))
SMTX_TO     = dateparser.parse(os.environ.get('SMTX_TO', 'today'))

class SmartMeterTxMeterReport(object):

    def __init__(self):
        self.config = getConfig()
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
        }).sort('readDate', pymongo.ASCENDING)
        if not reads:
            log.error('No records found for the date range specified.')
            return None
        result = []
        for reading in reads:
            reading['readDate'] = reading['readDate'].strftime('%F')
            result.append(reading)
        return result

    def sendReport(self, reads):
        '''
        Send the report via AWS SNS.
        '''
        log.info('Sending report via AWS SNS...')
        sns = boto3.client('sns')
        report = '''
Daily Reads Report
==================

Date Range: %s to %s
    
''' % ( SMTX_FROM.strftime('%F'), SMTX_TO.strftime('%F') )
        total = 0.0
        for read in reads:
            report += '%(readDate)s: %(energyDataKwh)s kWh\n' % read
            total += float(read['energyDataKwh'])
        report += "\n\nTotal Energy Use: %0.2f\n" % total
        response = sns.publish(
            TopicArn=self.config['aws']['sns']['topic'],
            Subject='SmartMeterTX Daily Reads Report',
            Message=report
        )
        log.debug(report)
        log.info(f'Report size in bytes: {len(bytes(report, "utf-8"))}')
        log.info('Success with message id %(MessageId)s !' % response)

def main() -> int:
    log.info('Gathering records from %s to %s' % ( SMTX_FROM.strftime('%F'), SMTX_TO.strftime('%F') ) )
    smtxReport = SmartMeterTxMeterReport()
    reads = smtxReport.getDailyReads()
    if not reads:
        log.error('Failed to read SmartMeterTX db...')
        return 2
    smtxReport.sendReport(reads)
    return 0


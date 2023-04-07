'''
\x1b[31mModule-Level Documentation!\x1b[0m
'''
import os, sys
import yaml
import dateparser
import pymongo
import json
from datetime import datetime

import kizano
from smartmetertx.api import MeterReader
from smartmetertx.utils import getConfig

log = kizano.getLogger(__name__)
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
    self.getMongoConnection()
    self.getSMTX()

  def ensureIndexes(self):
    self.db.meterReads.create_index(
      [('reading', 1)],
      background=True
    )
    self.db.meterReads.create_index(
      [('datetime', 1)],
      background=True,
      unique=True
    )
    return self

  def getMongoConnection(self):
    # Establish connections to various sources and targets.
    log.info('Connecting to DB...')
    self.db = pymongo.MongoClient(self.config['mongodb']['url']).get_database('smartmetertx')
    self.ensureIndexes()
    log.info('Connected! Indexes have been established as well!')
    return self.db

  def getSMTX(self):
    log.info('Connecting to SmartMeterTX...')
    self.smtx = MeterReader()
    self.smtx.login(self.config['smartmetertx']['user'], self.config['smartmetertx']['pass'])
    log.info('Success! Getting meter reads...')
    return self.smtx

  def getDailyReads(self):
    # Get the meter reads and print the date in the format their API expects.
    reads = self.smtx.get_daily_read(self.config['smartmetertx']['esiid'], SMTX_FROM.strftime('%m/%d/%Y'), SMTX_TO.strftime('%m/%d/%Y'))
    if not reads:
        log.warn('Failed to get records from meterReads()')
    else:
        log.info('Acquired %d meter reads! Inserting into DB...' % len(reads['dailyData']))
    return reads

  def filterDailyReads(self, dailyData):
    results = []
    log.debug(json.dumps(dailyData, indent=2))
    for meterRead in dailyData:
      meterRead['datetime'] = datetime.strptime('%(date)s %(starttime)s' % meterRead, '%m/%d/%Y %H:%M%p')
      del meterRead['date'], meterRead['starttime']
      meterRead['startreading'] = float(meterRead['startreading'])
      meterRead['endreading'] = float(meterRead['endreading'])
      results.append(meterRead)
    return results

  def insertDailyData(self, dailyData):
    results = []
    log.info('Inserting %d reads into the DB.' % len(dailyData))
    try:
      insertResult = self.db.meterReads.insert_many(dailyData)
      log.debug(insertResult)
      results.append(insertResult)
    except pymongo.errors.BulkWriteError as e:
      errs = list(filter( lambda x: x['code'] != 11000, e.details['writeErrors'] ))
      if errs:
        raise errs
    log.info('Complete!')

def main():
  log.info('Gathering records from %s to %s' % ( SMTX_FROM.strftime('%F/%R'), SMTX_TO.strftime('%F/%R') ) )
  smtx2mongo = Smtx2Mongo()
  reads = smtx2mongo.getDailyReads()
  if not reads:
    log.error('Failed to read smartmetertexas API...')
    return 2

  dailyData = smtx2mongo.filterDailyReads(reads['dailyData'])
  if dailyData:
    smtx2mongo.insertDailyData(dailyData)
  else:
    log.warning('No records inserted!')
  return 0



import os
import pymongo
import gnupg
import kizano
from urllib.parse import urlencode

log = kizano.getLogger(__name__)

def getMongoConnection(config: kizano.Config):
    # Establish connections to various sources and targets.
    log.info('Connecting to MongoDB...')
    gpg = gnupg.GPG(gnupghome=os.path.join(os.environ['HOME'], '.gnupg'), use_agent=True)
    mongo_user = config['mongo']['username']
    mongo_pass = gpg.decrypt(config['mongo']['password']).data.decode('utf-8')
    mongo_host = config['mongo']['host']
    mongo_opts = urlencode(config['mongo']['opts'])
    mongo_url = f'mongodb://{mongo_user}:{mongo_pass}@{mongo_host}/?{mongo_opts}'
    db = pymongo.MongoClient(mongo_url)
    log.info('Connected!')
    return db


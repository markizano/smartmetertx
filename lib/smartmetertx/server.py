
import os
import json
import cherrypy
import jinja2

from kizano import getLogger, Config
log = getLogger(__name__)

from smartmetertx.utils import getConfig, getMongoConnection
from smartmetertx.controller import SmartMeterController

#class HttpApi(object):

class MeterServer(SmartMeterController):
    mongo = None

    def __init__(self, config: Config):
        super(MeterServer, self)
        self.config = config
        self.db = getMongoConnection(config).get_database(config['mongo'].get('dbname', 'smartmetertx'))

    def __del__(self):
        self.close()

    def close(self):
        if self.mongo:
            self.mongo.close()
            self.mongo = None

    @cherrypy.expose
    def index(self):
        '''
        Home page!
        '''
        return self.returnValue(True, {'hello': 'world'})

    @cherrypy.expose
    def meterRead(self, date):
        '''
        Return a meter read for a specified date.
        Gets the full meter read from the DB.
        '''
        result = {}
        import dateparser
        queryDate = dateparser.parse(date)
        timerange = {
            '$gte': queryDate.replace( hour=max(0, queryDate.hour-1) ),
            '$lt': queryDate.replace( hour=min(23, queryDate.hour+1) )
        }
        result = self.db.meterReads.find_one({'datetime': timerange })
        del result['_id']
        result['datetime'] = result['datetime'].strftime('%F/%R:%S')
        return self.returnValue(True, result)

    @cherrypy.expose
    def meterReads(self, fdate, tdate):
        '''
        Return a list of meter reads for a specified date range.
        Gets only the list of values paired with the date as an object/key-value pairing.
        '''
        result = []
        import dateparser
        fromDate = dateparser.parse(fdate)
        toDate = dateparser.parse(tdate)
        timerange = {
            '$gte': fromDate,
            '$lt': toDate
        }
        projection = { '_id': False, 'reading': True, 'datetime': True}
        reads = list( self.db.meterReads.find({'datetime': timerange }, projection) )
        for mRead in reads:
            sdate = mRead['datetime'].strftime('%F')
            result.append( [sdate, mRead['reading'] ] )
        return self.returnValue(True, result)

class GoogleGraphsFS(SmartMeterController):
    def __init__(self):
        UI_PATH = os.path.realpath( os.getenv('UI_PATH', './ui') )
        log.info(f'Serving files from {UI_PATH}')
        fsloader = jinja2.FileSystemLoader( UI_PATH )
        self.view = jinja2.Environment(loader=fsloader)
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    @cherrypy.expose
    def index(self, **kwargs):
        return self.view.get_template('index.html').render(
            page='<p>Index Page.</p>',
            navigation='<li><a href="/user/login">Login</a></li>'
        )

def main():
    '''
    Main application/API entry point.
    '''
    config = getConfig()
    smtx = MeterServer(config)
    content = GoogleGraphsFS()
    log.debug(f'Got config: {config}')
    serverConfig = config.get('daemon', {})
    cherrypy.config.update(serverConfig.get('cherrypy', {}))
    cherrypy.tree.mount(smtx, '/api', { '/api': serverConfig['sites']['/api'] } )
    cherrypy.tree.mount(content, '/', {'/': serverConfig['sites']['/'] })
    if hasattr(cherrypy.engine, 'block'):
        # 3.1 syntax
        cherrypy.engine.start()
        cherrypy.engine.block()
    else:
        # 3.0 syntax
        cherrypy.server.quickstart()
        cherrypy.engine.start()
    return 0


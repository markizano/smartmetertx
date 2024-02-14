
import os, sys
import cherrypy
import jinja2
from datetime import datetime

from kizano import getLogger, getConfig, Config
log = getLogger('smartmetertx.server')

from smartmetertx.utils import getMongoConnection
from smartmetertx.controller import SmartMeterController

DEFAULT_UI_PATH = os.path.join( sys.exec_prefix, 'share', 'smartmetertx' )

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
    @cherrypy.tools.json_out()
    def meterRead(self, date: str = None):
        '''
        Return a meter read for a specified date.
        Gets the full meter read from the DB.
        '''
        result = {}
        if date is None:
            return self.returnValue(False, 'No date specified.')
        try:
            import dateparser
            queryDate = dateparser.parse(date)
            timerange = {
                '$gte': queryDate.replace( hour=max(0, queryDate.hour-1) ),
                '$lt': queryDate.replace( hour=min(23, queryDate.hour+1) )
            }
            result = self.db.meterReads.find_one({'datetime': timerange })
            if result is None:
                return self.returnValue(False, f'No meter read found for {date}')
            log.debug(result)
            del result['_id']
            result['datetime'] = result['datetime'].strftime('%F/%R:%S')
            return self.returnValue(True, result)
        except Exception as e:
            import traceback as tb
            log.error(f'Error getting meter read for {date}: {e}')
            log.error(tb.format_exc())
            return self.returnValue(False, 'uhm, well, this is embarassing :S')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def meterReads(self, fdate: str = None, tdate: str = None):
        '''
        Return a list of meter reads for a specified date range.
        Gets only the list of values paired with the date as an object/key-value pairing.
        '''
        result = []
        if fdate is None:
            return self.returnValue(False, 'No From Date Specified. Need `fdate`.')
        if tdate is None:
            return self.returnValue(False, 'No To Date Specified. Need `tdate`.')
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
    def __init__(self, uiPath: str = None):
        log.info(f'Serving files from {uiPath}')
        fsloader = jinja2.FileSystemLoader( uiPath )
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
    cherrypy._cplogging.LogManager.time = lambda self: datetime.now().strftime('%F %T')
    config = getConfig()
    apiConfig = {
        'tools.trailing_slash.on': False,
        'tools.json_in.on': True,
        'tools.staticdir.on': False,
    }
    serverConfig = {
        'tools.trailing_slash.on': False,
        'tools.staticdir.on': True,
        'tools.staticdir.dir': os.path.realpath( config.get('server', {}).get('ui.path', DEFAULT_UI_PATH) )
    }
    smtx = MeterServer(config)
    content = GoogleGraphsFS( serverConfig['tools.staticdir.dir'] )
    log.debug(f'Got config: {config}')
    cherrypy.config.update(config.get('daemon', {}).get('cherrypy', {}))
    cherrypy.tree.mount(smtx, '/api', { '/api': apiConfig } )
    cherrypy.tree.mount(content, '/', {'/': serverConfig })
    cherrypy.engine.start()
    cherrypy.engine.block()
    return 0


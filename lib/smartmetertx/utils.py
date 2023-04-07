
import os
import kizano

log = kizano.getLogger(__name__)

class Config(object):
    __CONFIGCACHE = {}

    @staticmethod
    def getConfig():
        """
        Static method for getting configuration for this app, be it cron, client or server.
        """
        if Config.__CONFIGCACHE:
            log.debug('Cache-HIT: Returning config from cache')
            return Config.__CONFIGCACHE
        try:
            syscfg = kizano.utils.read_yaml(os.path.join('etc', 'smartmetertx', 'config.yml'))
            log.info('Found and loaded /etc/smartmetertx/config.yml')
        except:
            syscfg = {}
        try:
            localcfg = kizano.utils.read_yaml( os.path.join(os.environ['HOME'], '.config', 'smartmetertx', 'config.yml') )
            log.info('Found and loaded ~/.config/smartmetertx/config.yml')
        except:
            localcfg = {}
        Config.__CONFIGCACHE = kizano.utils.dictmerge(syscfg, localcfg)
        log.debug(f'Cache-Miss: Config loaded - {Config.__CONFIGCACHE}')
        return Config.getConfig()

getConfig = Config.getConfig


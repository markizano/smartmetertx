
import os
import kizano

class Config(object):
    __CONFIGCACHE = {}

    @staticmethod
    def getConfig():
        """
        Static method for getting configuration for this app, be it cron, client or server.
        """
        if Config.__CONFIGCACHE:
            return Config.__CONFIGCACHE
        try:
            syscfg = kizano.utils.read_yaml(os.path.join('etc', 'smartmetertx', 'config.yml'))
        except:
            syscfg = {}
        try:
            localcfg = kizano.utils.read_yaml( os.path.join(os.environ['HOME'], '.config', 'smartmetertx', 'config.yml') )
        except:
            localcfg = {}
        Config.__CONFIGCACHE = kizano.utils.dictmerge(syscfg, localcfg)
        return Config.getConfig()

getConfig = Config.getConfig

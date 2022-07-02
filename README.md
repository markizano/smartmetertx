# Original Class Object
https://github.com/cmulk/python_smartmetertx

# python-smartmetertx
SmartMeterTX Python class provides a JSON interface to the electricity usage data available at https://www.smartmetertexas.com.  
You must have an account established at the site.

Additions done by [@Markizano](http://github.com/markizano) to support HTTP2.0 since the 2019 SmartMeterTexas2.0 update.
API seems to be the same.

More details can be found: https://github.com/mrand/smart_meter_texas

Depends on a MongoDB server to be running in the environment of sorts.

Will have to later build support for sqlite3 for local DB setup installs
that require no further software than this package.

More documentation in [doc|./doc].

Notable files below:

# bin/fetchMeterReads.cron.py
Run this on a CRON to collect meter reads at least once a day to store data offline from the
SmartMeterTexas.com site.

# bin/smtx-server.py
Run this to start up the local server.
Configure with `~/.config/smartmetertx/config.yml`.
Starts on port 7689 by default.

Loads a simple web page that can be used to visualize the data you want.

Extend as you please from here :)

# Original Class Object
https://github.com/cmulk/python_smartmetertx

# python-smartmetertx
SmartMeterTX/SmartMeter Texas Python class provides a JSON interface to the electricity usage data available at https://www.smartmetertexas.com.
You must have an account established at the site.

Additions done by [@Markizano](http://github.com/markizano) to support updates since JAN 2024.
API seems to be the same.

More details can be found: https://github.com/mrand/smart_meter_texas

Depends on a MongoDB server to be running in the environment of sorts.

Will have to later build support for sqlite3 for local DB setup installs
that require no further software than this package.

More documentation in [doc](./doc).

I created this as a means to collect and store data longer than the two years SMTX stores data.
In this way, you can have this in your local database and render charts and graphs no matter who your electric provider is.
If you live in Texas, you know how challenging it can be searching for a new provider every couple of months to annually
and not having clear access to your electric usage history.

This is a project used to help piece together some of that together so I have a single interface when dealing with my electric usage.

I, Markizano, will support this project as long as I live in Texas.

# Prerequisites
- [Setting up an unprivileged script account](./doc/unprivileged-setup.md)

Notable files below:

# bin/fetchMeterReads.cron.py
Full documentation: [fetchMeterReads.cron.py.md](./doc/fetchMeterReads.cron.py.md)

# bin/meterReadsReport.py
Full documentation: [meterReadsReport.py.md](./doc/meterReadsReport.py.md)

# bin/smtx-server.py
Full documentation: [smtx-server.py.md](./doc/smtx-server.py.md)

Extend as you please from here :)

**Update FEB 2024**
SmartMeterTX has changed their API endpoints and now requires you to have your address whitelisted with them and to setup an SSL certificate with them.

You can email `support-at-smartmetertexas-dot-com` (I redacted the @ and . to derail the bots) to get your address
whitelisted and coordinate with them on a public-facing SSL certificate for the HTTP/2.0 connection.

# Screenshots
![smtx-sample-page](https://markizano.net/assets/images/smtx-home-page.png)

# References
- SMTX API Documentation: https://www.smartmetertexas.com/commonapi/gethelpguide/help-guides/Smart_Meter_Texas_Data_Access_Interface_Guide.pdf


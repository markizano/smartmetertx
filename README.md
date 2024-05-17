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

Notable files below:

# bin/fetchMeterReads.cron.py
Run this on a CRON to collect meter reads at least once a day to store data offline from the
SmartMeterTexas.com site.

# bin/smtx-server.py
Run this to start up the local server.
Configure with `~/.config/smartmetertx/config.yml`.
Starts on port 7689 by default.

Passwords are encrypted using gpg. You can store the PGP armored message block in your configuration
file and this app will attempt to decrypt using your key (pending you manage the password/key/chain requirements beyond this app).

Encrypt the password using:

    $ echo -en "my-secret-password" | gpg -aer 0x0000

Where `0x0000` is the key you want to use for this encryption.
In this way, sensitive credentials are not stored in plain text in files.

Loads a simple web page that can be used to visualize the data you want.

Extend as you please from here :)

# Screenshots
![smtx-sample-page](https://markizano.net/assets/images/smtx-home-page.png)

# References
- SMTX API Documentation: https://www.smartmetertexas.com/commonapi/gethelpguide/help-guides/Smart_Meter_Texas_Data_Access_Interface_Guide.pdf


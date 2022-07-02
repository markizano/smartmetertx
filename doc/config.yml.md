
# config.yml
Configuration can be stored in `/etc/smartmetertx/config.yml` or in `~/.config/smartmetertx/config.yml`.
System config will be read from `/etc` first, then `~/.config` will override on top of that.

Note: References to SMTX Website are talking about https://www.smartmetertexas.com/

Here's documentation for each of the data points:

## mongodb
Type: Object
Description: Top-level object for talking to MongoDB server/database.
Members:
- url: [#mongodb.url]
## mongodb.url
Type: string
Description: URL containing everything the MongoDB client needs to find and connect to the DB.

## smartmetertx
Type: Object
Description: Contains the datapoints we need to authenticate and find meter reads info from https://www.smartmetertexas.com/
Members:
- [#smartmetertx.user]
- [#smartmetertx.pass]
- [#smartmetertx.esiid]

## smartmetertx.user
Type: string
Description: Username to authenticate against https://www.smartmetertexas.com/
## smartmetertx.pass
Type: String
Description: Authentication password to login to the SMTX website.
## smartmetertx.esiid
Type: String
Description: The meter ESIID associated with your account.

## daemon
Type: Object
Description: Top-level holder for all things related to the server/daemon that runs and serves the browser applet.

## daemon.cherrypy
Type: Object
Description: Config directives for CherryPy engine itself.

## daemon.sites
Type: Object
Description: Objects that configure each of the sites setup and configured in the application itself.
  Probably should just make this internal configuration.

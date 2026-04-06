
# config.yml

Configuration can be stored in `/etc/smartmetertx/config.yml` or in `~/.config/smartmetertx/config.yml`.
System config will be read from `/etc` first, then `~/.config` will override on top of that.

Note: References to SMTX Website are talking about <https://www.smartmetertexas.com/>

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
Description: Contains the datapoints we need to authenticate and find meter reads info from <https://www.smartmetertexas.com/>
Members:

- [#smartmetertx.user]
- [#smartmetertx.pass]
- [#smartmetertx.esiid]

## smartmetertx.user

Type: string
Description: Username to authenticate against <https://www.smartmetertexas.com/>

## smartmetertx.pass

Type: String
Description: Authentication password to login to the SMTX website.

## smartmetertx.esiid

Type: String
Description: The meter ESIID associated with your account.

## smartmetertx.power2choose

Type: Object
Description: Default query parameters for the Power to Choose API fetcher (`smtx-power2choose`).
All keys are optional and override built-in defaults. CLI flags override these values.
Members:

- zip_code: Service zip code to query plans for
- plan_mo_from: Minimum plan term in months (default: 10)
- plan_mo_to: Maximum plan term in months (default: 24)
- plan_type: Plan type filter — 1=fixed (default: 1)
- timeofuse: Time-of-use plans — 'on' or 'off' (default: off)
- renewable_energy_id: Renewable energy filter ID (default: 10)
- estimated_use: Estimated monthly usage in kWh for pricing tiers (default: 2000)

## smartmetertx.power2choose.zip_code

Type: string
Description: ZIP code for the service address used to filter available plans.

## smartmetertx.power2choose.plan_mo_from

Type: integer
Description: Minimum contract term in months.

## smartmetertx.power2choose.plan_mo_to

Type: integer
Description: Maximum contract term in months.

## smartmetertx.power2choose.plan_type

Type: integer
Description: Plan type filter. 1 = fixed-rate plans only.

## smartmetertx.power2choose.timeofuse

Type: string
Description: Include time-of-use plans. Set to 'on' to include, 'off' to exclude (default).

## smartmetertx.power2choose.renewable_energy_id

Type: integer
Description: Renewable energy filter ID passed to the Power to Choose API.

## smartmetertx.power2choose.estimated_use

Type: integer
Description: Estimated monthly kWh usage used by the API to calculate price tiers (default: 2000).

## daemon

Type: Object
Description: Top-level holder for all things related to the server/daemon that runs and serves the
browser applet.

## daemon.cherrypy

Type: Object
Description: Config directives for CherryPy engine itself.

## daemon.sites

Type: Object
Description: Objects that configure each of the sites setup and configured in the application itself.
  Probably should just make this internal configuration.

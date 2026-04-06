# Original Class Object

- <https://github.com/cmulk/python_smartmetertx>

## python-smartmetertx

SmartMeterTX/SmartMeter Texas Python class provides a JSON interface to the electricity usage data
available at <https://www.smartmetertexas.com>. You must have an account established at the site.

Additions done by [@Markizano](http://github.com/markizano) to support updates since JAN 2024.
API seems to be the same.

More details can be found: <https://github.com/mrand/smart_meter_texas>

Depends on a MongoDB server to be running in the environment of sorts.

Will have to later build support for sqlite3 for local DB setup installs
that require no further software than this package.

More documentation in [doc](./doc).

I created this as a means to collect and store data longer than the two years SMTX stores data. In
this way, you can have this in your local database and render charts and graphs no matter who your
electric provider is. If you live in Texas, you know how challenging it can be searching for a new
provider every couple of months to annually and not having clear access to your electric usage
history.

This is a project used to help piece together some of that together so I have a single interface
when dealing with my electric usage.

I, Markizano, will support this project as long as I live in Texas.

## Installation

```bash
pip install smartmetertx2mongo
```

## Prerequisites

- MongoDB server
- Python 3.11+
- AWS credentials configured for SNS notifications (optional — for error alerting)
- [Setting up an unprivileged script account](./doc/unprivileged-setup.md)

## Commands

## smtx-fetch

Run on a cron to collect meter reads daily from SmartMeterTexas.com and store them in MongoDB.

Full documentation: [smtx-fetch.md](./doc/smtx-fetch.md)

## smtx-power2choose

Fetch electricity plan listings from the Power to Choose API and store them in MongoDB.
Intended to run daily via cron to keep plan data current.

Full documentation: [smtx-power2choose.md](./doc/smtx-power2choose.md)

## smtx-reconcile

Compare available provider plans against your real meter usage history and rank them by
estimated annual cost. Produces a Markdown report with confirmed EFL pricing.

Full documentation: [smtx-reconcile.md](./doc/smtx-reconcile.md)

## smtx-report

Fetch meter reads from MongoDB and send a usage summary report via SNS notification.

Full documentation: [smtx-report.md](./doc/smtx-report.md)

## smtx-server

Start the local web server for visualizing meter data in a browser.

Full documentation: [smtx-server.md](./doc/smtx-server.md)

Extend as you please from here :)

**Update FEB 2024**:
SmartMeterTX has changed their API endpoints and now requires you to have your address whitelisted
with them and to setup an SSL certificate with them.

You can email `support-at-smartmetertexas-dot-com` (I redacted the @ and . to derail the bots) to
get your address whitelisted and coordinate with them on a public-facing SSL certificate for the
HTTP/2.0 connection.

**Update JUL 2025**:

> As per our records, you have integrated and accessing the API services for your SMT accounts. The
> new API services with JWT token are expected to be available starting 22nd August 2025, and the
> existing SSL-based API will be decommissioned after 13th September 2025.You will no longer need a
> Public SSL certificate as a prerequisite for the API Integration after 13th September 2025. The new
> API services and existing API services are running in parallel from 23rd August 2025 to 12th
> September 2025. The documentation and new Interface Guide for the new API services are available
> under the Quick Reference Guide(FTPS and API Security Upgrade Project) section on the portal home
> page at smartmetertexas.com. Please refer the latest Interface guide and let us know if you are
> having any assist from us.

## Screenshots

![smtx-sample-page](https://markizano.net/assets/images/smtx-home-page.png)

## References

- SMTX API Documentation: <https://www.smartmetertexas.com/commonapi/gethelpguide/help-guides/Smart_Meter_Texas_Data_Access_Interface_Guide.pdf>

Run this on a CRON to collect meter reads at least once a day to store data offline from the
SmartMeterTexas.com site.

If you want to catch up on previous meter reads, you can use environment variables to set the dates parseable by [dateparser](https://dateparser.readthedocs.io/en/latest/).

# Environment Variables

## SMTX_FROM
The FROM date where to start meter reads. Usually this will be included in the results.

## SMTX_TO
The TO date where to stop results. This is usually not inclusive, so if you want the target date, specify the day after that.

# Example CRON Entry

In `/etc/cron.d/metrics`, I have the following:

```
2 2 * * * smartmetertx /home/smartmetertx/bin/fetch-meter-reads.sh
```

# Example CRON script
In this script, I have it setup to ensure the script runs as the specified user since I don't like scripts running as root:

```bash
#!/bin/bash

# Ensure this script runs as the smartmetertx user account.
test "$UID" -eq `id -u smartmetertx` || { exec sudo -H -E -u smartmetertx -g apps $0 $@; exit 0; }

# From the `kizano` python package; this will redirect all output to the system logger with some metadata associated with it.
exec > >(log smtx-fetch-meter-reads)
exec 2>&1

# Activates the python virtual environment.
. ~/bin/activate
echo "Running fetch.meterReads.cron.py as smartmetertx:apps"

# Set the AWS profile so SNS topics can be sent out. You will have to setup an AWS account. SNS notifications are free for the first million.
export AWS_PROFILE=sns

# Run and overwrite this PID with the Python script that will fetch the meter reads.
exec /home/smartmetertx/bin/fetchMeterReads.cron.py

```

For more info on setting up the unprivileged account, please see the [doc](./unprivileged-setup.md).

# Ad-hoc Run The Script
In the case you want to fetch certain meter reads from the API you can do this:

```bash
SMTX_FROM=2024-01-11 SMTX_TO=2024-02-12 ~smartmetertx/bin/fetch-meter-reads.sh
```

You can even run this script as root as it will drop privileges before running the python goodies.

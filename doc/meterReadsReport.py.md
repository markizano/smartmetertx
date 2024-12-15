**New in v1.2.4!**

This script will fetch the meter reads from the database and send a notify to the configured SNS topic.

Sample output from the report:

```
Daily Reads Report
==================

Date Range: 2024-11-11 to 2024-12-11
    
2024-11-11: 36.18 kWh    2024-11-12: 28.26 kWh    2024-11-13: 33.91 kWh    2024-11-14: 33.31 kWh    2024-11-15: 35.42 kWh    2024-11-16: 35.57 kWh    2024-11-17: 38.29 kWh    
2024-11-18: 38.50 kWh    2024-11-19: 29.52 kWh    2024-11-20: 45.85 kWh    2024-11-21: 57.85 kWh    2024-11-22: 49.32 kWh    2024-11-23: 52.42 kWh    2024-11-24: 46.68 kWh    
2024-11-25: 42.83 kWh    2024-11-26: 42.85 kWh    2024-11-27: 39.43 kWh    2024-11-28: 55.00 kWh    2024-11-29: 60.10 kWh    2024-11-30: 52.13 kWh    2024-12-01: 50.49 kWh    
2024-12-02: 58.80 kWh    2024-12-03: 47.75 kWh    2024-12-04: 49.78 kWh    2024-12-05: 43.79 kWh    2024-12-06: 65.40 kWh    2024-12-07: 47.19 kWh    2024-12-08: 39.94 kWh    
2024-12-09: 36.44 kWh    2024-12-10: 56.47 kWh    2024-12-11: 72.03 kWh    

Total Energy Use: 1421.50
```

# Run the Report

Simply use the same `$SMTX_FROM` and `$SMTX_TO` variables described in [fetchMeterReads.cron.py](./fetchMeterReads.cron.py.md) to generate a report on a date range, like so:

```bash
AWS_PROFILE=sns SMTX_FROM=2024-11-11 SMTX_TO=2024-12-11 bin/meterReadsReport.py
```

and it will generate and send a notify on a report.

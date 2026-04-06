# smtx-power2choose

Fetches electricity plan listings from the Power to Choose API and stores them in the configured
MongoDB `power2choose` collection. Intended to run daily via cron to keep plan data current.

Sends an SNS error alert if the fetch or insert fails.

## CLI Arguments

- `--zip-code` — Service zip code (overrides config)
- `--min-term` — Minimum plan term in months (overrides config)
- `--max-term` — Maximum plan term in months (overrides config)
- `--plan-type` — Plan type filter: 1=fixed (overrides config)
- `--renewable-energy-id` — Renewable energy filter ID (overrides config)

## Configuration

Parameters can be set under `smartmetertx.power2choose` in `~/.config/smartmetertx/config.yml`.
CLI flags override config values, which override built-in defaults.

See [config.yml.md](./config.yml.md) for the full configuration reference.

## Example CRON Entry

In `/etc/cron.d/metrics`, add:

```cron
0 6 * * * smartmetertx AWS_PROFILE=sns smtx-power2choose
```

## Ad-hoc Run

```bash
smtx-power2choose --zip-code=75001
```

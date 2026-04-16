# Rate Limit Usage

Prevent alert storms by suppressing repeated notifications within a cooldown window.

## Configuration (`example_rate_limit.json`)

```json
{
  "cooldown_seconds": 1800,
  "state_file": "/tmp/cronwrap_ratelimit.json"
}
```

## Python API

```python
from cronwrap.rate_limit import RateLimitPolicy

policy = RateLimitPolicy.from_dict({"cooldown_seconds": 1800})

if not policy.is_suppressed("my-job"):
    # send alert ...
    policy.record_alert("my-job")
else:
    print("Alert suppressed: within cooldown window")
```

## Fields

| Field | Default | Description |
|---|---|---|
| `cooldown_seconds` | `3600` | Minimum seconds between alerts per job |
| `state_file` | `/tmp/cronwrap_ratelimit.json` | Path to persist alert timestamps |

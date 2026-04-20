# Job Throttle Usage

Prevent a job from running more often than a configured interval.

## Configuration

```json
{
  "job_name": "daily-report",
  "min_interval_seconds": 3600,
  "state_dir": "/var/lib/cronwrap/throttle"
}
```

## Python API

```python
from cronwrap.job_throttle import ThrottlePolicy, ThrottleError

policy = ThrottlePolicy.from_dict({
    "job_name": "daily-report",
    "min_interval_seconds": 3600,
})

try:
    policy.acquire()   # raises ThrottleError if too soon
    # ... run your job ...
except ThrottleError as exc:
    print(f"Skipped: {exc}")
```

## Check without acquiring

```python
remaining = policy.check()
if remaining > 0:
    print(f"Job throttled for {remaining:.0f}s more.")
else:
    print("Job may run.")
```

## Reset

```python
policy.reset()  # clear state so job can run immediately
```

## CLI integration

Use `throttle-check` sub-command (if wired into `cronwrap/throttle_cli.py`)
to inspect or reset throttle state from the shell.

# Job Concurrency Policy

Prevent multiple simultaneous instances of the same cron job.

## Configuration (`example_job_concurrency.json`)

```json
{
  "job_name": "nightly_report",
  "max_instances": 1,
  "state_dir": "/var/run/cronwrap/concurrency"
}
```

| Field | Default | Description |
|---|---|---|
| `job_name` | required | Unique job identifier |
| `max_instances` | `1` | Maximum simultaneous instances allowed |
| `state_dir` | `/tmp/cronwrap/concurrency` | Directory for PID state files |

## Usage

```python
from cronwrap.job_concurrency import ConcurrencyPolicy, ConcurrencyError

policy = ConcurrencyPolicy.from_dict({
    "job_name": "nightly_report",
    "max_instances": 1,
})

try:
    policy.acquire()          # registers current PID
    run_my_job()
except ConcurrencyError as e:
    print(f"Skipping: {e}")
finally:
    policy.release()          # deregisters current PID
```

## Notes

- Stale PIDs (processes that no longer exist) are automatically pruned on each
  `acquire()` or `running_count()` call.
- State is stored as a simple JSON file per job in `state_dir`.

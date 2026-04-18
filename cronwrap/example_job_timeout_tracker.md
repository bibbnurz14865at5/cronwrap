# Job Timeout Tracker

The `job_timeout_tracker` module scans job history and identifies runs that
exceeded the configured timeout policy thresholds.

## Usage

```python
from pathlib import Path
from cronwrap.timeout_policy import TimeoutPolicy
from cronwrap.job_timeout_tracker import find_violations, violations_to_json

policy = TimeoutPolicy(warn_after=60.0, kill_after=120.0)
violations = find_violations(Path("/var/log/cronwrap"), policy)
print(violations_to_json(violations))
```

## TimeoutViolation fields

| Field       | Type   | Description                          |
|-------------|--------|--------------------------------------|
| `job_name`  | str    | Name of the job                      |
| `duration`  | float  | Actual run duration in seconds       |
| `limit`     | float  | The threshold that was exceeded      |
| `timestamp` | str    | ISO-8601 timestamp of the run        |

## Filtering by job

Pass `job_name` to `find_violations` to restrict the scan to a single job:

```python
violations = find_violations(Path("/var/log/cronwrap"), policy, job_name="backup")
```

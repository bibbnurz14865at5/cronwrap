# Job Summary Usage

`cronwrap-summary` aggregates per-job statistics from the history directory
into a concise report.

## Quick start

```bash
# Print a human-readable table
cronwrap-summary show --history-dir .cronwrap/history

# Output JSON for downstream processing
cronwrap-summary show --history-dir .cronwrap/history --json
```

## Sample table output

```
JOB                             RUNS  SUCCESS%   AVG_DUR     LAST
----------------------------------------------------------------------
backup-db                         42     97.6%     12.34s       ok
clean-tmp                         10    100.0%      0.45s       ok
send-report                        5     80.0%      3.12s     fail
```

## Sample JSON output

```json
[
  {
    "job_name": "backup-db",
    "total_runs": 42,
    "success_rate": 0.9762,
    "avg_duration": 12.34,
    "last_status": "ok"
  }
]
```

## Programmatic use

```python
from cronwrap.job_summary import build_summary

for entry in build_summary(".cronwrap/history"):
    print(entry.job_name, entry.success_rate)
```

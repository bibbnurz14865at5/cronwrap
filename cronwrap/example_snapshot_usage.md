# Job Snapshot Usage

The `cronwrap-snapshot` command generates a point-in-time JSON report of
every job whose history is stored in the history directory.

## Quick start

```bash
# Print snapshot to stdout
cronwrap-snapshot --history-dir .cronwrap/history

# Save snapshot to a file
cronwrap-snapshot --history-dir .cronwrap/history --output /tmp/snapshot.json
```

## Output format

```json
{
  "generated_at": "2024-06-01T12:00:00+00:00",
  "jobs": [
    {
      "job_name": "backup",
      "last_run": "2024-06-01T11:55:00+00:00",
      "last_status": "success",
      "success_rate": 0.95,
      "avg_duration": 12.4,
      "total_runs": 120
    }
  ]
}
```

## Python API

```python
from cronwrap.job_snapshot import build_snapshot, save_snapshot

report = build_snapshot(".cronwrap/history")
print(report.to_json())

# Persist for later diffing
save_snapshot(report, "/var/log/cronwrap/snapshot.json")
```

## Integration tips

- Schedule a daily `cronwrap-snapshot` run and commit the output to git to
  track job health trends over time.
- Feed the JSON into a dashboard or alerting tool to detect degrading
  success rates before they become outages.

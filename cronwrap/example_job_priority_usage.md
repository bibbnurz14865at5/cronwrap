# Job Priority Usage

Assign priority levels to cron jobs so dashboards and digests can surface
the most important jobs first.

## Priority Levels

| Level      | Description                              |
|------------|------------------------------------------|
| `critical` | Must not fail; alert immediately         |
| `high`     | Important; alert on first failure        |
| `normal`   | Default level                            |
| `low`      | Informational; alert only after retries  |

## Programmatic Usage

```python
from pathlib import Path
from cronwrap.job_priority import PriorityIndex

idx = PriorityIndex(Path("/var/lib/cronwrap/priorities.json"))

# Assign priorities
idx.set("db_backup", priority="critical", weight=10)
idx.set("send_report", priority="normal")
idx.set("temp_cleanup", priority="low")

# Retrieve a single job's priority
jp = idx.get("db_backup")
print(jp.priority)  # critical

# Iterate jobs highest-priority first
for job in idx.sorted_jobs():
    print(job.job_name, job.priority)
```

## Example JSON

See `example_job_priority.json` for a sample index file.

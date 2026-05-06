# Job Heatmap Usage

The `JobHeatmap` module tracks how many times a cron job runs during each
hour of the day (buckets 0–23). This lets you spot busy periods and
unexpected off-hours activity.

## Programmatic usage

```python
from cronwrap.job_heatmap import JobHeatmap
from datetime import datetime

hm = JobHeatmap(state_dir="/var/lib/cronwrap/heatmaps")

# Record a run at the current hour
hour = datetime.utcnow().hour
rec = hm.record("backup", hour)
print(rec.peak_hour())   # e.g. 3
print(rec.total_runs())  # e.g. 42
```

## CLI

```bash
# Show ASCII heatmap
cronwrap-heatmap show backup

# Show as JSON
cronwrap-heatmap show backup --json

# List all tracked jobs
cronwrap-heatmap list

# Reset a job's heatmap
cronwrap-heatmap reset backup
```

## HeatmapRecord fields

| Field      | Type       | Description                        |
|------------|------------|------------------------------------|
| `job_name` | `str`      | Name of the cron job               |
| `buckets`  | `List[int]`| Run counts indexed by hour (0-23)  |

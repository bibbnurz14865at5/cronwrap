# Job Dependencies Usage

Ensure a cron job only proceeds when its upstream jobs have completed successfully.

## Config (`example_job_dependencies.json`)

```json
{
  "job_name": "report_job",
  "depends_on": ["fetch_data", "preprocess"],
  "require_success_within_seconds": 3600
}
```

## Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `job_name` | str | required | Name of the job being configured |
| `depends_on` | list[str] | `[]` | Job names that must have succeeded |
| `require_success_within_seconds` | int\|null | `null` | Max age of last success in seconds |

## Python Usage

```python
from cronwrap.job_dependencies import DependencyConfig, assert_dependencies, DependencyError

cfg = DependencyConfig.from_json_file("example_job_dependencies.json")
try:
    assert_dependencies(cfg, history_dir="/var/cronwrap/history")
except DependencyError as e:
    print(f"Blocked: {e}")
    raise SystemExit(1)

# safe to proceed
run_my_job()
```

## CLI Integration

Check dependencies before running a wrapped command:

```bash
python -m cronwrap.job_dependencies_cli \
  --config example_job_dependencies.json \
  --history-dir /var/cronwrap/history \
  -- /usr/local/bin/report_job.sh
```

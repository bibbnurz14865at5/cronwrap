# Job Baseline Usage

`cronwrap.job_baseline` tracks a rolling median duration for each job
and flags runs that are anomalously slow.

## Quick start

```python
from cronwrap.job_baseline import JobBaseline

baseline = JobBaseline(state_dir="/var/lib/cronwrap/baselines")

# After a job finishes, record its duration (seconds):
record = baseline.update("nightly-backup", duration=42.3)

print(record.median)          # rolling median over last 20 runs
print(record.is_anomalous(42.3))   # False — within 2× median
print(record.is_anomalous(200.0))  # True  — more than 2× median
```

## Customising the rolling window and anomaly factor

```python
record = baseline.update("etl-job", duration=15.0, window=10)

if record.is_anomalous(duration=60.0, factor=3.0):
    print("Job took more than 3× its usual time — investigate!")
```

## Accessing raw data

```python
record = baseline.load("nightly-backup")
print(record.durations)   # list of the last N durations
print(record.to_dict())   # serialisable dict
```

## State files

Each job gets a JSON file under `state_dir`:

```
/var/lib/cronwrap/baselines/
  nightly-backup.baseline.json
  etl-job.baseline.json
```

Example file contents:

```json
{
  "job_name": "nightly-backup",
  "durations": [38.1, 41.5, 42.3],
  "window": 20
}
```

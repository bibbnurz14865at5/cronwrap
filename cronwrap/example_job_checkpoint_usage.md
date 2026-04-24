# Job Checkpoint Usage

The `JobCheckpoint` module lets long-running cron jobs persist their progress
so they can resume from the last successful step after a failure or restart.

## Basic Usage

```python
from cronwrap.job_checkpoint import JobCheckpoint

cp = JobCheckpoint(job_name="nightly_etl", state_dir="/var/lib/cronwrap/checkpoints")

# Check whether a previous run left a checkpoint
last = cp.load()
start_step = last.step if last else "fetch"
print(f"Resuming from step: {start_step}")

# After completing each stage, save progress
cp.save(step="fetch", meta={"rows_fetched": 42000})
cp.save(step="transform")
cp.save(step="load")

# Clear the checkpoint when the job finishes successfully
cp.clear()
```

## API

### `JobCheckpoint(job_name, state_dir)`
- `job_name` — unique identifier for the job (used as the filename).
- `state_dir` — directory where checkpoint JSON files are stored
  (default: `/tmp/cronwrap/checkpoints`).

### `.save(step, meta=None) -> Checkpoint`
Persist a checkpoint at the named *step*.  Optional *meta* dict stores
arbitrary key/value pairs (e.g. record counts, offsets).

### `.load() -> Checkpoint | None`
Return the last saved `Checkpoint`, or `None` if no checkpoint exists.

### `.clear()`
Delete the checkpoint file once the job completes successfully.

### `.has_checkpoint() -> bool`
Quick existence check without deserialising the file.

## `Checkpoint` dataclass fields

| Field | Type | Description |
|-------|------|-------------|
| `job_name` | `str` | Name of the owning job |
| `step` | `str` | Last completed step label |
| `timestamp` | `float` | Unix timestamp of the save |
| `meta` | `dict` | Arbitrary extra data |

# Job Suppression Usage

`JobSuppression` lets you temporarily silence notifications for a job — useful during planned maintenance or known incidents.

## Python API

```python
from datetime import datetime, timezone, timedelta
from cronwrap.job_suppression import JobSuppression

js = JobSuppression(state_dir="/var/lib/cronwrap/suppression")

# Suppress notifications for 2 hours
until = datetime.now(timezone.utc) + timedelta(hours=2)
js.suppress("backup-job", until=until, reason="scheduled maintenance")

# Check before dispatching a notification
if js.is_suppressed("backup-job"):
    print("Notifications suppressed — skipping alert.")

# Resume early
js.resume("backup-job")

# List all currently active suppressions
for state in js.list_suppressed():
    print(state.job_name, state.suppressed_until, state.reason)
```

## CLI

```bash
# Suppress for 90 minutes with an optional reason
cronwrap-suppression suppress backup-job --minutes 90 --reason "deploy window"

# Check suppression status (exits 2 if suppressed, 0 if active)
cronwrap-suppression check backup-job

# Resume notifications immediately
cronwrap-suppression resume backup-job

# List all active suppressions
cronwrap-suppression list
```

## State files

Each job's suppression state is stored as a JSON file under `state_dir`:

```json
{
  "job_name": "backup-job",
  "suppressed_until": "2024-06-01T04:00:00+00:00",
  "reason": "deploy window"
}
```

The `reason` field is optional and omitted when not provided.

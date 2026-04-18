# Job Annotations

Annotations let you attach arbitrary key-value metadata to a cron job.
They are stored as JSON files in a configurable directory.

## Programmatic usage

```python
from cronwrap.job_annotations import JobAnnotations

ann = JobAnnotations("/var/lib/cronwrap/annotations", "backup-db")
ann.set("owner", "data-team")
ann.set("oncall", "alice@example.com")

print(ann.get("owner"))   # data-team
print(ann.all())           # {'owner': 'data-team', 'oncall': 'alice@example.com'}

ann.remove("oncall")
ann.clear()
```

## CLI usage

```bash
# Set an annotation
cronwrap-annotations --job backup-db set owner "data-team"

# Get a single annotation
cronwrap-annotations --job backup-db get owner

# List all annotations (JSON)
cronwrap-annotations --job backup-db list

# Remove one annotation
cronwrap-annotations --job backup-db remove owner

# Clear all annotations for a job
cronwrap-annotations --job backup-db clear

# Use a custom storage directory
cronwrap-annotations --storage-dir /tmp/ann --job myjob set tier gold
```

## Storage format

Each job's annotations are stored in:
```
<storage_dir>/<job_name>.annotations.json
```

Example file contents:
```json
{
  "owner": "data-team",
  "tier": "gold"
}
```

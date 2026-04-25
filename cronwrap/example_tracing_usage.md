# Job Tracing Usage

`cronwrap` can attach a lightweight distributed trace context to each job run,
making it easy to correlate logs and alerts across systems.

## Starting a trace

```python
from cronwrap.job_tracing import JobTracing
from datetime import datetime, timezone

tracing = JobTracing("/var/lib/cronwrap/traces")

record = tracing.start_trace(
    job_name="nightly-report",
    started_at=datetime.now(timezone.utc).isoformat(),
    # Optionally propagate a parent trace from an upstream system:
    # parent_span_id="abc-123",
    # trace_id="existing-trace-id",
    extra={"triggered_by": "cron"},
)
print(record.trace_id)  # propagate this to downstream services
```

## Finishing a trace

```python
record = tracing.finish_trace(
    job_name="nightly-report",
    ended_at=datetime.now(timezone.utc).isoformat(),
    status="success",
)
```

## CLI inspection

```bash
# Show the current trace for a job
cronwrap-tracing show nightly-report --state-dir /var/lib/cronwrap/traces

# Clear the trace record
cronwrap-tracing clear nightly-report
```

## Schema

| Field | Required | Description |
|---|---|---|
| `job_name` | yes | Name of the job |
| `trace_id` | yes | UUID for the overall trace |
| `span_id` | yes | UUID for this specific span |
| `started_at` | yes | ISO-8601 start timestamp |
| `ended_at` | no | ISO-8601 end timestamp |
| `parent_span_id` | no | Parent span for nested traces |
| `status` | no | `success` or `failure` |
| `extra` | no | Arbitrary key-value metadata |

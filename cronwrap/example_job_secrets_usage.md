# Job Secrets Usage

Track which environment variables (secrets) a cron job requires,
without storing their values.

## Register secrets for a job

```python
from cronwrap.job_secrets import JobSecrets, SecretsRegistry

reg = SecretsRegistry("/var/lib/cronwrap/secrets.json")
reg.register(JobSecrets(
    job_name="backup",
    required=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
    optional=["AWS_SESSION_TOKEN"],
))
```

## Check before running

```python
secrets = reg.get("backup")
if secrets:
    result = secrets.check()
    if not result.ok:
        raise RuntimeError(f"Missing secrets: {result.missing}")
```

## List all registered jobs

```python
print(reg.all_jobs())
```

## Remove a job's secret definition

```python
reg.remove("backup")
```

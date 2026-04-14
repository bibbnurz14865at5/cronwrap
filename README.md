# cronwrap

A lightweight CLI wrapper for managing and monitoring cron jobs with Slack/email alerting on failures.

---

## Installation

```bash
pip install cronwrap
```

Or install from source:

```bash
git clone https://github.com/yourname/cronwrap.git && cd cronwrap && pip install .
```

---

## Usage

Wrap any cron command with `cronwrap` to enable monitoring and failure alerts:

```bash
cronwrap --slack-webhook https://hooks.slack.com/... --email you@example.com -- python /path/to/job.py
```

**Example crontab entry:**

```cron
0 3 * * * cronwrap --slack-webhook $SLACK_WEBHOOK -- /usr/bin/python3 /opt/scripts/backup.py
```

If the wrapped command exits with a non-zero status, `cronwrap` will automatically send an alert containing the exit code, stdout, and stderr output.

### Options

| Flag | Description |
|------|-------------|
| `--slack-webhook URL` | Slack incoming webhook URL for failure notifications |
| `--email ADDRESS` | Email address to notify on failure |
| `--timeout SECONDS` | Kill the job if it exceeds this duration |
| `--name NAME` | Human-readable job name included in alerts |
| `--quiet` | Suppress stdout/stderr output from the wrapped command |

---

## Configuration

Environment variables can be used in place of flags:

```bash
export CRONWRAP_SLACK_WEBHOOK="https://hooks.slack.com/..."
export CRONWRAP_EMAIL="ops@example.com"
```

---

## License

MIT © 2024 Your Name
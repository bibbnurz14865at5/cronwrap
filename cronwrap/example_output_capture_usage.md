# Output Capture Usage

`cronwrap.output_capture` provides helpers to capture, truncate, and inspect
job stdout/stderr before storing or sending alerts.

## Basic Usage

```python
from cronwrap.output_capture import capture, tail_lines

stdout = "...job output..."
stderr = "...error output..."

# Truncate to default 4096 bytes each
result = capture(stdout, stderr)

if result.truncated:
    print("Output was truncated")

# Get combined output for alert messages
print(result.combined())

# Get last 20 lines of stderr
print(tail_lines(result.stderr, n=20))
```

## Serialisation

```python
import json
from cronwrap.output_capture import CapturedOutput

data = result.to_dict()
json.dumps(data)  # safe to store in history

restored = CapturedOutput.from_dict(data)
```

## Custom Limits

```python
# Only keep 1 KB of output
result = capture(stdout, stderr, max_bytes=1024)
```

# Logs Directory

This directory contains all logging files for the multi-agent brainstorming system.

## Log File Structure

Each agent creates three types of log files:

### 1. Communication Logs (`*_communications.jsonl`)
- **Format**: JSON Lines (one JSON object per line)
- **Content**: All requests and responses between agents
- **Fields**:
  - `timestamp`: ISO format timestamp
  - `type`: Type of log entry (request, response, incoming_request, outgoing_response, error, activity)
  - `request_id`: Unique identifier for tracking requests across agents
  - `from_agent`: Source agent name
  - `to_agent`: Target agent name
  - `skill`: Skill being requested
  - `request_data` / `response_data`: Full request/response payload
  - `status`: Status (success, error, sent, received)
  - `error`: Error message if status is error

### 2. Error Logs (`*_errors.log`)
- **Format**: Standard Python logging format
- **Content**: All errors and exceptions
- **Includes**: Stack traces and context information

### 3. Activity Logs (`*_activity.log`)
- **Format**: Standard Python logging format
- **Content**: General activity and informational messages
- **Includes**: Agent startup, agent card requests, etc.

## Log Files by Agent

- `host_agent_communications.jsonl` - Host agent communication logs
- `host_agent_errors.log` - Host agent error logs
- `host_agent_activity.log` - Host agent activity logs
- `idea_agent_communications.jsonl` - Idea agent communication logs
- `idea_agent_errors.log` - Idea agent error logs
- `idea_agent_activity.log` - Idea agent activity logs
- `critic_agent_communications.jsonl` - Critic agent communication logs
- `critic_agent_errors.log` - Critic agent error logs
- `critic_agent_activity.log` - Critic agent activity logs
- `prioritizer_agent_communications.jsonl` - Prioritizer agent communication logs
- `prioritizer_agent_errors.log` - Prioritizer agent error logs
- `prioritizer_agent_activity.log` - Prioritizer agent activity logs

## Reading Logs

### Communication Logs (JSONL)
```python
import json

# Read all communication logs
with open('logs/host_agent_communications.jsonl', 'r') as f:
    for line in f:
        log_entry = json.loads(line)
        print(log_entry)
```

### Filter by Request ID
To track a specific request across all agents:
```python
import json
import glob

request_id = "your-request-id"

# Search across all communication logs
for log_file in glob.glob('logs/*_communications.jsonl'):
    with open(log_file, 'r') as f:
        for line in f:
            log_entry = json.loads(line)
            if log_entry.get('request_id') == request_id:
                print(f"{log_file}: {log_entry}")
```

### Filter by Agent
To see all communications from/to a specific agent:
```python
import json

agent_name = "host_agent"

# Search in all communication logs
for log_file in glob.glob('logs/*_communications.jsonl'):
    with open(log_file, 'r') as f:
        for line in f:
            log_entry = json.loads(line)
            if log_entry.get('from_agent') == agent_name or log_entry.get('to_agent') == agent_name:
                print(log_entry)
```

## Log Rotation

Logs are appended to files continuously. For production use, consider:
- Implementing log rotation (e.g., daily rotation)
- Archiving old logs
- Setting up log retention policies

## Privacy and Security

⚠️ **Warning**: Logs may contain sensitive information including:
- User input topics
- Generated ideas
- Full request/response payloads

Ensure proper access controls and consider data retention policies.


# Bug Fix Comparison Table

## Before vs After — Bug Fix Comparison

| # | File | Line(s) | Severity | Category | Before (Broken) | After (Fixed) | Impact |
|---|------|---------|----------|----------|-----------------|---------------|--------|
| 1 | `remote_agent_connection.py` | 300–303 | 🔴 CRITICAL | Logic Bug | `import time` inside function body + `end_time = 300` (fixed integer) | `import time` at module top + `end_time = time.time() + 300` (future timestamp) | Polling loop **never ran** — every request silently returned `"Task timed out"` |
| 2 | `remote_agent_connection.py` | 303 | 🔴 CRITICAL | Logic Bug | `while time.time() < end_time:` — `time.time()` ≈ 1.7B, so `1.7B < 300` is **always False** | Evaluates correctly after `end_time = time.time() + 300` fix | Loop skipped entirely on every call |
| 3 | `agent_executor.py` | 86 | 🟠 MEDIUM | Logic / Operator Precedence | `task_input.get("user_request") or ... if isinstance(task_input, dict) else ""` — `isinstance` guard only applied to the last `.get()` | `(task_input.get("user_request") or task_input.get("project_idea") or task_input.get("topic", "")) if isinstance(task_input, dict) else ""` | `AttributeError` crash when `task_input` is not a dict |
| 4 | `streamlit_app/app.py` | 147–153 | 🟠 MEDIUM | Deprecated API | `loop = asyncio.get_event_loop()` then `loop.run_until_complete(...)` | `asyncio.run(_send_request())` | Deprecation warning in Python 3.10+, raises `RuntimeError` in Python 3.12+ |
| 5 | `streamlit_app/app.py` | 103 | 🟡 LOW | Wrong Comment | `poll_interval = 10  # Poll every 5 second` | `poll_interval = 10  # Poll every 10 seconds` | Misleading comment — said 5s but code used 10s |
| 6 | `architect_agent.py` | 21 | 🟠 MEDIUM | Deprecated SDK Param | `ChatOpenAI(openai_api_key=self.api_key, ...)` | `ChatOpenAI(api_key=self.api_key, ...)` | Deprecation warning from `langchain-openai`; future versions will break |
| 7 | `developer_agent.py` | 21 | 🟠 MEDIUM | Deprecated SDK Param | `ChatOpenAI(openai_api_key=self.api_key, ...)` | `ChatOpenAI(api_key=self.api_key, ...)` | Same as above |
| 8 | `tester_agent.py` | 20 | 🟠 MEDIUM | Deprecated SDK Param | `ChatOpenAI(openai_api_key=self.api_key, ...)` | `ChatOpenAI(api_key=self.api_key, ...)` | Same as above |
| 9 | `tester_agent.py` | 67 | 🟡 LOW | Bad Import Placement | `import re` inside `except` block (re-imported on every exception) | `import re` at module level | Minor performance waste; bad practice |
| 10 | `developer_agent.py` | 158 | 🟡 LOW | Inconsistent Backoff | `wait_time = 2 ** attempt` → **1s, 2s, 4s** (too aggressive for OpenAI rate limits) | `wait_time = 5 * (2 ** attempt)` → **5s, 10s, 20s** | Retries too fast — likely hits rate limit again immediately |
| 11 | `tester_agent.py` | 88 | 🟡 LOW | Inconsistent Backoff | `wait_time = 2 ** attempt` → **1s, 2s, 4s** | `wait_time = 5 * (2 ** attempt)` → **5s, 10s, 20s** | Same as above — now consistent with `architect_agent.py` |

---

## Severity Summary

| Severity | Count | Files Affected |
|----------|-------|----------------|
| 🔴 Critical | 2 | `remote_agent_connection.py` |
| 🟠 Medium | 5 | `agent_executor.py`, `streamlit_app/app.py`, all 3 agent files |
| 🟡 Low | 4 | `streamlit_app/app.py`, `tester_agent.py`, `developer_agent.py` |
| **Total** | **11** | **6 files** |

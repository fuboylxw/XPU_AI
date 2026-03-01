#!/usr/bin/env python3
"""
ReAct task + SSE smoke test.

Usage:
  python3 scripts/react_task_sse_smoke.py --base-url http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Dict, Optional


def _http_post_json(url: str, payload: Dict[str, object], timeout: float) -> int:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        method="POST",
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return int(resp.status)


def _stream_progress(
    url: str,
    timeout_seconds: int,
    max_final_events: int,
) -> int:
    req = urllib.request.Request(
        url=url,
        method="GET",
        headers={"Accept": "text/event-stream"},
    )

    final_count = 0
    start_ts = time.time()
    current_data: Optional[str] = None

    with urllib.request.urlopen(req, timeout=timeout_seconds + 5) as resp:
        for raw in resp:
            if time.time() - start_ts > timeout_seconds:
                print("timeout waiting progress events", file=sys.stderr)
                break

            line = raw.decode("utf-8", errors="ignore").rstrip("\n")

            if not line:
                if current_data is not None:
                    try:
                        event = json.loads(current_data)
                    except Exception:
                        current_data = None
                        continue

                    progress_type = event.get("progress_type", "")
                    status = event.get("status", "")
                    task_id = event.get("task_id")
                    data = event.get("data") or {}
                    react_event = data.get("react_event")
                    attempt = data.get("attempt")
                    print(
                        f"event progress_type={progress_type} status={status} task_id={task_id} "
                        f"react_event={react_event} attempt={attempt}"
                    )

                    if progress_type in ("result", "error"):
                        final_count += 1
                        if final_count >= max_final_events:
                            break

                    current_data = None
                continue

            if line.startswith(":"):
                # comment / keep-alive
                continue

            if line.startswith("data:"):
                current_data = line[len("data:") :].strip()
                continue

    return final_count


def main() -> int:
    parser = argparse.ArgumentParser(description="ReAct task SSE smoke test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="FastAPI base URL")
    parser.add_argument("--question", default="What time is it in Beijing now?", help="Task question")
    parser.add_argument("--user-id", default="smoke_user", help="User ID")
    parser.add_argument("--timeout-seconds", type=int, default=90, help="SSE wait timeout")
    parser.add_argument("--max-final-events", type=int, default=1, help="Stop after N result/error events")
    args = parser.parse_args()

    session_id = f"smoke_{uuid.uuid4().hex[:10]}"
    execute_url = urllib.parse.urljoin(args.base_url.rstrip("/") + "/", f"api/tasks/{session_id}/execute")
    progress_url = urllib.parse.urljoin(
        args.base_url.rstrip("/") + "/",
        f"api/tasks/{session_id}/progress?include_thinking=false",
    )

    print(f"session_id={session_id}")
    print(f"POST {execute_url}")
    try:
        status = _http_post_json(
            execute_url,
            payload={"session_id": session_id, "question": args.question, "user_id": args.user_id},
            timeout=20.0,
        )
    except urllib.error.HTTPError as e:
        print(f"execute request failed: status={e.code}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"execute request failed: {e}", file=sys.stderr)
        return 2

    if status not in (200, 202, 204):
        print(f"unexpected execute status: {status}", file=sys.stderr)
        return 2

    print(f"execute status={status}")
    print(f"GET {progress_url}")

    try:
        final_count = _stream_progress(
            progress_url,
            timeout_seconds=max(10, int(args.timeout_seconds)),
            max_final_events=max(1, int(args.max_final_events)),
        )
    except urllib.error.HTTPError as e:
        print(f"progress stream failed: status={e.code}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"progress stream failed: {e}", file=sys.stderr)
        return 3

    if final_count <= 0:
        print("no final result/error events received", file=sys.stderr)
        return 4

    print(f"ok: final_events={final_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

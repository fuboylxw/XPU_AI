"""
简单测试：调用 FastAPI 的流式聊天接口以跑通 ChatbotAgent.answer_question_stream。

使用 TestClient 触发应用的 startup/shutdown 事件，并消费 SSE 流，打印前几段数据。
"""
from typing import List
import os
import sys
from starlette.testclient import TestClient

# 确保可以导入项目根目录下的 fastapi_app
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi_app.main import app


def consume_sse_lines(lines_iter, max_lines: int = 10) -> List[str]:
    """消费部分 SSE 行，返回收集到的行列表。"""
    collected: List[str] = []
    for idx, line in enumerate(lines_iter):
        if isinstance(line, bytes):
            try:
                line = line.decode("utf-8", errors="ignore")
            except Exception:
                line = str(line)
        collected.append(line)
        if idx + 1 >= max_lines:
            break
    return collected


def main():
    payload = {
        "conversation_id": "conv_test_stream",
        "message": "你好，介绍一下西安工程大学的图书馆",
        "user_id": "tester_stream",
    }

    with TestClient(app) as client:
        # 使用 stream 模式以便迭代响应内容
        with client.stream("POST", "/api/chat/stream/", json=payload) as response:
            assert response.status_code == 200, f"状态码异常: {response.status_code}"

            lines = consume_sse_lines(response.iter_lines(), max_lines=10)
            print("=== 收到的前10条SSE流数据 ===")
            for i, l in enumerate(lines, 1):
                print(f"[{i}] {l}")


if __name__ == "__main__":
    main()
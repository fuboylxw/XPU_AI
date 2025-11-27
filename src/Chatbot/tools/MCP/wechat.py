import time
import json
import requests
from typing import Any, Dict, Optional, List

class WeChatTool:
    def __init__(self, settings: Any) -> None:
        self.corp_id = getattr(settings, "WECHAT_CORP_ID", "")
        self.corp_secret = getattr(settings, "WECHAT_CORP_SECRET", "")
        self.agent_id = getattr(settings, "WECHAT_AGENT_ID", "")
        self.default_user = getattr(settings, "WECHAT_DEFAULT_USER", "")
        self.mode = "wecom" if self.corp_id and self.corp_secret else "unavailable"

    def _get_token(self) -> Optional[str]:
        try:
            r = requests.get(
                "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                params={"corpid": self.corp_id, "corpsecret": self.corp_secret},
                timeout=6,
            )
            d = r.json()
            if d.get("errcode") == 0:
                return d.get("access_token")
            return None
        except Exception:
            return None

    def send_message(self, to_user: str, content: str) -> Dict[str, Any]:
        if self.mode != "wecom":
            return {"success": False, "error": "WeChat not configured", "source": "wechat"}
        token = self._get_token()
        if not token:
            return {"success": False, "error": "Failed to get token", "source": "wechat"}
        try:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
            payload = {
                "touser": to_user or self.default_user,
                "msgtype": "text",
                "agentid": int(self.agent_id),
                "text": {"content": content},
                "safe": 0,
            }
            r = requests.post(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), timeout=6)
            d = r.json()
            ok = d.get("errcode") == 0
            return {"success": ok, "source": "wechat", "answer": "ok" if ok else d.get("errmsg")}
        except Exception as e:
            return {"success": False, "error": str(e), "source": "wechat"}

    def fetch_messages(self, since_ts: Optional[int] = None) -> Dict[str, Any]:
        return {"success": False, "error": "Receiving via WeCom not supported", "source": "wechat", "results": []}

def build_wechat_send_runner(settings: Any):
    tool = WeChatTool(settings)
    async def runner(params: Dict[str, Any]) -> Dict[str, Any]:
        to_user = str(params.get("to_user") or tool.default_user)
        content = str(params.get("content") or "")
        return tool.send_message(to_user, content)
    return runner

def build_wechat_fetch_runner(settings: Any):
    tool = WeChatTool(settings)
    async def runner(params: Dict[str, Any]) -> Dict[str, Any]:
        ts = params.get("since_ts")
        try:
            since_ts = int(ts) if ts is not None else None
        except Exception:
            since_ts = None
        return tool.fetch_messages(since_ts)
    return runner

WECHAT_SEND_INPUT_SCHEMA = {
    "properties": {
        "to_user": {"type": "string"},
        "content": {"type": "string"},
    },
    "required": ["content"],
}

WECHAT_FETCH_INPUT_SCHEMA = {
    "properties": {
        "since_ts": {"type": "integer"},
    },
    "required": [],
}
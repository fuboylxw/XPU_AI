"""
时间查询工具（官方时间服务优先）
优先使用中国科学院国家授时中心（NTSC）网页 `http://www.time.ac.cn/stime.asp` 解析北京时间；
若网页解析失败，回退到 NTSC NTP 服务；仍失败则回退本地系统时间。
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
import re
import requests
import socket
import struct
import time
from zoneinfo import ZoneInfo
from typing import Dict, Any

from src.Chatbot.utils.logger import setup_logger


class TimeTool:
    def __init__(self) -> None:
        self.logger = setup_logger("time_tool")
        self.ntp_server = "ntp.ntsc.ac.cn"  # 国家授时中心 NTP 服务
        self.ntp_timeout = 5

    def _query_time_ac_cn(self, timeout_sec: int = 5) -> datetime | None:
        """从国家授时中心网页解析北京时间（Asia/Shanghai）。失败返回 None。"""
        url = "http://www.time.ac.cn/stime.asp"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "http://www.time.ac.cn/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            # 避免环境代理干扰，显式禁用代理
            resp = requests.get(url, headers=headers, timeout=timeout_sec, proxies={"http": None, "https": None})
            if resp.status_code != 200:
                return None
            text = resp.text
            # 中文样式：YYYY年MM月DD日 HH:MM:SS
            m = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{1,2}):(\d{1,2})", text)
            if m:
                y, mo, d, h, mi, s = map(int, m.groups())
                return datetime(y, mo, d, h, mi, s, tzinfo=ZoneInfo("Asia/Shanghai"))
            # ISO 样式：YYYY-MM-DD HH:MM:SS
            m2 = re.search(r"(20\d{2}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})", text)
            if m2:
                dt_str = f"{m2.group(1)} {m2.group(2)}"
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                return dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
            # JSONP/脚本中的日期变量兜底：提取花括号中的 time 字段
            brace_start = text.find("{")
            brace_end = text.rfind("}")
            if brace_start != -1 and brace_end > brace_start:
                blob = text[brace_start : brace_end + 1]
                m3 = re.search(r'"?time"?\s*:\s*"(20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"', blob)
                if m3:
                    dt = datetime.strptime(m3.group(1), "%Y-%m-%d %H:%M:%S")
                    return dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
            return None
        except Exception as e:
            # 降级为警告：该站点可能在部分网络环境不可达，属正常回退场景
            self.logger.warning(f"time.ac.cn 解析失败（将回退至NTP/系统时间）: {e}")
            return None

    def _query_ntp_unix_epoch(self) -> float | None:
        """查询 NTP 服务器，返回 UNIX epoch 秒（float）。

        使用最简 NTP 客户端实现（UDP 123），解析 transmit timestamp。
        """
        try:
            addr = (self.ntp_server, 123)
            msg = b"\x1b" + 47 * b"\0"  # LI=0, VN=3, Mode=3 (client)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(self.ntp_timeout)
                s.sendto(msg, addr)
                data, _ = s.recvfrom(512)
            if not data or len(data) < 48:
                return None
            # 解析 transmit timestamp（第 40-47 字节）
            # 参考结构：!12I（48字节），第11和第12个整数为秒与小数部分
            unpacked = struct.unpack("!12I", data[:48])
            seconds = unpacked[10]
            fraction = unpacked[11] / 2**32
            ntp_epoch = seconds + fraction  # NTP epoch（始于 1900-01-01）
            unix_epoch = ntp_epoch - 2208988800  # 转为 UNIX epoch（始于 1970-01-01）
            return unix_epoch
        except Exception as e:
            self.logger.error(f"NTP 查询失败: {e}")
            return None

    def get_time(self, timezone: str | None = None, fmt: str | None = None) -> Dict[str, Any]:
        tz = (timezone or "Asia/Shanghai").strip()
        fmt = fmt or "%Y-%m-%d %H:%M:%S"
        try:
            # 1) 优先解析 time.ac.cn 的北京时间
            bj_dt = self._query_time_ac_cn()
            source = "time.ac.cn"
            if bj_dt is None:
                # 2) 回退 NTP（UTC）
                unix_epoch = self._query_ntp_unix_epoch()
                source = "ntp.ntsc.ac.cn" if unix_epoch is not None else "system"
                if unix_epoch is None:
                    now_utc = datetime.now(dt_timezone.utc)
                else:
                    now_utc = datetime.fromtimestamp(unix_epoch, tz=dt_timezone.utc)
                bj_dt = now_utc.astimezone(ZoneInfo("Asia/Shanghai"))
            # 统一转换到目标时区
            now = bj_dt.astimezone(ZoneInfo(tz))
            return {
                "success": True,
                "time": now.strftime(fmt),
                "timezone": tz,
                "format": fmt,
                "timestamp": int(now.timestamp()),
                "source": source,
            }
        except Exception as e:
            self.logger.error(f"获取时间失败: {e}")
            return {"success": False, "error": str(e), "timezone": tz}

"""
天气查询工具（城市代码仅从本地 JSON 读取）

实现策略：
- 城市代码解析仅使用本地 `data/local_city_codes.json` 文件，不进行任何网络解析。
- 天气数据仍调用中国天气网官方接口（根据本地城市代码查询实况/预报）。

返回结构化结果，便于 MCP 上层消费。
"""

from __future__ import annotations

import aiohttp
import requests
import re
import time
from typing import Any, Dict, List, Optional

from src.Chatbot.utils.logger import setup_logger


class WeatherTool:
    def __init__(self, settings: Any | None = None) -> None:
        self.logger = setup_logger("weather")
        self.settings = settings
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=20),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            },
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
            self.session = None

    def _parse_cma_js_blob(self, text: str) -> Dict[str, Any]:
        """解析 d1.weather.com.cn/weather_index/{code}.html 返回的 JS 变量集合。

        返回包含可能的键：dataSK, dataZS, dataFC 等。
        """
        out: Dict[str, Any] = {}
        try:
            # 匹配形如：var dataSK = {...};
            for key in ("dataSK", "dataFC", "dataZS", "alarms"):
                m = re.search(rf"var\s+{key}\s*=\s*(\{{.*?\}});", text, re.S)
                if m:
                    import json
                    try:
                        out[key] = json.loads(m.group(1))
                    except Exception:
                        # 有些返回中 dataFC 是 JSON 字符串，需要二次解析
                        raw = m.group(1)
                        mm = re.search(r"\"(\{.*?\})\"", raw, re.S)
                        if mm:
                            out[key] = json.loads(mm.group(1))
            return out
        except Exception as e:
            self.logger.debug(f"解析 CMA JS 变量失败: {e}")
            return out

    def _extract_temps(self, temp_str: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """从如 '19℃~8℃' 字符串中提取最高/最低温（摄氏度数字）。"""
        if not temp_str:
            return None, None
        s = str(temp_str)
        m = re.findall(r"(-?\d+)℃", s)
        if len(m) >= 2:
            return m[0], m[1]
        if len(m) == 1:
            return m[0], m[0]
        # 兜底：提取数字
        m2 = re.findall(r"-?\d+", s)
        if len(m2) >= 2:
            return m2[0], m2[1]
        if len(m2) == 1:
            return m2[0], m2[0]
        return None, None

    def _summarize_from_mobile_weatherinfo(self, wi: Dict[str, Any], days: int) -> List[Dict[str, Any]]:
        """解析 m.weather.com.cn 的多日预报结构（weather1/temp1/wind1 ...）。"""
        out: List[Dict[str, Any]] = []
        try:
            n = max(1, min(6, days))
            for i in range(1, n + 1):
                temp = wi.get(f"temp{i}")
                weather = wi.get(f"weather{i}")
                wind = wi.get(f"wind{i}")
                tmax, tmin = self._extract_temps(temp)
                out.append(
                    {
                        "date": f"day{i}",
                        "max_temp_C": tmax,
                        "min_temp_C": tmin,
                        "summary": (str(weather or "") + ", " + str(wind or "")).strip(", "),
                        "source": "cma_weather_mobile",
                    }
                )
        except Exception as e:
            self.logger.debug(f"解析 mobile weatherinfo 失败: {e}")
        return out

    async def _fetch_mobile_forecast(self, code: str) -> Optional[Dict[str, Any]]:
        """获取 m.weather.com.cn 的多日预报 JSON。

        该接口可能有反爬与跳转，使用移动端 UA 并容错解码/JSONP。
        """
        url = f"http://m.weather.com.cn/data/{code}.html"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1"
            ),
            "Referer": "http://m.weather.com.cn/",
        }
        try:
            if self.session:
                async with self.session.get(url, headers=headers) as resp:
                    data = await resp.read() if resp.status == 200 else b""
            else:
                r = requests.get(url, headers=headers, timeout=10)
                data = r.content if r.status_code == 200 else b""
            text: str = ""
            for enc in ("utf-8", "gbk", "gb2312"):
                if not data:
                    break
                try:
                    text = data.decode(enc)
                    break
                except Exception:
                    continue
            if not text and data:
                try:
                    text = data.decode("utf-8", errors="ignore")
                except Exception:
                    text = ""

            import json
            # 尝试直接解析为 JSON
            try:
                obj = json.loads(text)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                # 若为 HTML/JSONP，尝试提取 JSON 片段
                lb = text.find("{")
                rb = text.rfind("}")
                if lb != -1 and rb > lb:
                    frag = text[lb : rb + 1]
                    try:
                        obj = json.loads(frag)
                        if isinstance(obj, dict):
                            return obj
                    except Exception:
                        pass
            return None
        except Exception as e:
            self.logger.debug(f"请求 m.weather.com.cn 失败: {e}")
            return None

    def _fallback_city_code(self, city: str) -> Optional[str]:
        """仅本地查询：从 JSON 文件解析城市代码（不使用内置映射）。"""
        raw = city.strip()
        # 载入本地 JSON 文件
        local_map = self._load_local_city_codes()
        # 句子内包含匹配（中文）
        for k, v in local_map.items():
            if k and k in raw:
                return v
        # 去后缀的精确匹配
        name = raw
        for suf in ("市", "区", "县"):
            if name.endswith(suf):
                name = name[: -len(suf)]
                break
        # JSON 精确匹配
        if name in local_map:
            return local_map[name]
        # 中文片段匹配（本地 JSON 优先）
        mlist = re.findall(r"[\u4e00-\u9fa5]{2,}", raw)
        for seg in mlist:
            if seg in local_map:
                return local_map[seg]
            for suf in ("市", "区", "县"):
                if seg.endswith(suf) and seg[:-len(suf)] in local_map:
                    return local_map[seg[:-len(suf)]]
        # 英文/拼音（仅本地 JSON）
        ascii_name = re.sub(r"[^a-zA-Z]", "", raw).lower()
        if ascii_name and ascii_name in local_map:
            return local_map[ascii_name]
        return None

    async def resolve_city_code(self, city: str) -> Dict[str, Any]:
        """解析输入城市名称，仅使用本地 JSON，返回9位城市代码。"""
        try:
            self._ensure_local_city_codes_file()
            self.logger.info(f"城市代码解析输入(本地): {city}")
            code = self._fallback_city_code(city)
            # 仅接受 9 位标准代码
            if code and len(str(code)) != 9:
                code = None
            if code:
                return {"success": True, "code": code, "city": city, "source": "resolve_city_code_local"}
            else:
                return {"success": False, "error": "未获取到城市代码", "city": city, "source": "resolve_city_code_local"}
        except Exception as e:
            self.logger.error(f"城市代码解析异常: {e}")
            return {"success": False, "error": str(e), "city": city, "source": "resolve_city_code_local"}

    # ===== 本地城市代码 JSON 存取 =====
    def _local_store_path(self) -> str:
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        # 到项目根目录
        root = os.path.abspath(os.path.join(here, os.pardir, os.pardir, os.pardir))
        return os.path.join(root, "data", "local_city_codes.json")

    def _ensure_local_city_codes_file(self) -> None:
        import os
        import json
        path = self._local_store_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            # 若文件不存在，初始化为空字典，后续由用户维护
            initial: Dict[str, str] = {}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(initial, f, ensure_ascii=False, indent=2)

    def _load_local_city_codes(self) -> Dict[str, str]:
        import json
        path = self._local_store_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                # 仅保留形如 "name": "9位码" 的条目
                return {str(k): str(v) for k, v in obj.items() if isinstance(v, (str, int))}
        except Exception:
            return {}
        return {}

    async def _fetch_cma_blob(self, code: str) -> Dict[str, Any]:
        """获取并解析 CMA 天气 JS blob。"""
        ts = str(int(time.time() * 1000))
        url = f"http://d1.weather.com.cn/weather_index/{code}.html?_={ts}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "http://www.weather.com.cn/",
        }
        try:
            if self.session:
                async with self.session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                    else:
                        data = b""
            else:
                r = requests.get(url, headers=headers, timeout=10)
                data = r.content if r.status_code == 200 else b""
            text: str = ""
            for enc in ("utf-8", "gbk", "gb2312"):
                if not data:
                    break
                try:
                    text = data.decode(enc)
                    break
                except Exception:
                    continue
            if not text and data:
                try:
                    text = data.decode("utf-8", errors="ignore")
                except Exception:
                    text = ""
            return self._parse_cma_js_blob(text)
        except Exception as e:
            self.logger.error(f"获取 CMA 天气数据失败: {e}")
            return {}

    def _summarize_from_dataFC(self, data_fc: Dict[str, Any], days: int) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            f_list = data_fc.get("f") or []
            for i, item in enumerate(f_list[: max(1, days)]):
                out.append(
                    {
                        "date": item.get("fa") or item.get("date"),
                        "max_temp_C": item.get("fd") or item.get("max"),
                        "min_temp_C": item.get("fe") or item.get("min"),
                        "summary": item.get("fb") or "",
                        "source": "cma_weather",
                    }
                )
        except Exception as e:
            self.logger.debug(f"解析 dataFC 失败: {e}")
        return out

    async def get_forecast(self, city: str, days: int = 1) -> List[Dict[str, Any]]:
        """获取城市天气（官方接口优先）。"""
        try:
            self.logger.info(f"天气查询输入城市: {city}")
            # 将城市代码查询逻辑完全分离到 resolve_city_code 并复用
            code_info = await self.resolve_city_code(city)
            code = code_info.get("code") if code_info.get("success") else None
            if code:
                self.logger.info(f"解析到城市代码: {code}")
            if not code:
                self.logger.error("未获取到城市代码，无法查询官方天气接口")
                return []
            results: List[Dict[str, Any]] = []
            # 3) 根据代码查询实况： http://www.weather.com.cn/data/sk/{code}.html
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Referer": "http://www.weather.com.cn/",
            }
            sk_url = f"http://www.weather.com.cn/data/sk/{code}.html"
            try:
                if self.session:
                    async with self.session.get(sk_url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                        else:
                            data = b""
                else:
                    r = requests.get(sk_url, headers=headers, timeout=10)
                    data = r.content if r.status_code == 200 else b""
                # 编码容错：优先 utf-8，失败则尝试 gbk/gb2312
                sk_text: str = ""
                for enc in ("utf-8", "gbk", "gb2312"):
                    if not data:
                        break
                    try:
                        sk_text = data.decode(enc)
                        break
                    except Exception:
                        continue
                if not sk_text and data:
                    try:
                        sk_text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        sk_text = ""
                # JSONP/脚本清洗：提取花括号包裹的 JSON 片段
                import json
                if sk_text and not sk_text.strip().startswith("{"):
                    lb = sk_text.find("{")
                    rb = sk_text.rfind("}")
                    if lb != -1 and rb > lb:
                        sk_text = sk_text[lb : rb + 1]
                sk = json.loads(sk_text) if sk_text else {}
                sk_info = sk.get("weatherinfo") or {}
                if sk_info:
                    results.append(
                        {
                            "date": "now",
                            "max_temp_C": sk_info.get("temp"),
                            "min_temp_C": sk_info.get("temp"),
                            "summary": (sk_info.get("WD", "") + sk_info.get("WS", "")).strip(),
                            "source": "cma_weather",
                            "city": sk_info.get("city"),
                            "cityid": sk_info.get("cityid"),
                            "humidity": sk_info.get("SD"),
                            "time": sk_info.get("time"),
                        }
                    )
            except Exception:
                pass

            # 4) 若实况失败或需补充，尝试 d1 接口的实况/日预报
            blob = await self._fetch_cma_blob(code)
            # 优先使用 dataSK 实况
            if blob.get("dataSK"):
                sk_info = blob["dataSK"]
                results.append(
                    {
                        "date": "now",
                        "max_temp_C": sk_info.get("temp"),
                        "min_temp_C": sk_info.get("temp"),
                        "summary": (sk_info.get("WD", "") + sk_info.get("WS", "")).strip(),
                        "source": "cma_weather",
                        "city": sk_info.get("cityname") or sk_info.get("city"),
                        "cityid": code,
                        "humidity": sk_info.get("SD") or sk_info.get("sd"),
                        "time": sk_info.get("time"),
                    }
                )
            if blob.get("dataFC"):
                results.extend(self._summarize_from_dataFC(blob["dataFC"], days))

            # 旧版 JSON 简报兜底（部分地区仍可用）
            cityinfo_url = f"http://www.weather.com.cn/data/cityinfo/{code}.html"
            try:
                if self.session:
                    async with self.session.get(cityinfo_url, headers=headers) as resp:
                        if resp.status == 200:
                            ci = await resp.json()
                        else:
                            ci = None
                else:
                    r = requests.get(cityinfo_url, headers=headers, timeout=10)
                    ci = r.json() if r.status_code == 200 else None
                if ci and isinstance(ci, dict):
                    wi = ci.get("weatherinfo") or {}
                    tmax, tmin = self._extract_temps(wi.get("temp1"))
                    results.append(
                        {
                            "date": "today",
                            "max_temp_C": tmax or wi.get("temp1"),
                            "min_temp_C": tmin or wi.get("temp2"),
                            "summary": wi.get("weather", ""),
                            "source": "cma_weather_cityinfo",
                        }
                    )
            except Exception:
                pass

            # 移动端 5-6 天预报
            mobile = await self._fetch_mobile_forecast(code)
            if isinstance(mobile, dict):
                wi = mobile.get("weatherinfo") or {}
                if wi:
                    results.extend(self._summarize_from_mobile_weatherinfo(wi, days))

            # 统一补全城市字段为用户输入（若官方返回为空）
            if results:
                for item in results:
                    if not item.get("city"):
                        item["city"] = city

            return [] if not results else results
        except Exception as e:
            self.logger.error(f"天气查询异常: {e}")
            return []

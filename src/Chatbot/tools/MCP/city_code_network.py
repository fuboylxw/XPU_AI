from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import requests


class CityCodeNetworkTool:
    """
    纯网络城市代码查询工具：通过中国天气网 city3jdata 层级接口解析城市代码。

    查询流程：
    1) 获取省份映射：`http://www.weather.com.cn/data/city3jdata/china.html`
    2) 逐省获取城市映射：优先 `china.html?level=2&code=<省代码>`，回退 `city3jdata/<省代码>.html`
    3) 获取站点（区县）映射：优先 `china.html?level=3&code=<市代码>`，回退 `city3jdata/<市代码>.html`

    返回 9 位城市代码（如 `101110101`）。不包含本地兜底映射与拼音映射。
    """

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings
        # 简易本地存储路径缓存
        self._store_path_cache: Optional[str] = None

    def _get_text(self, url: str, timeout: float = 8.0) -> Optional[str]:
        try:
            resp = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36",
                    "Referer": "http://www.weather.com.cn/",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
                timeout=timeout,
            )
            # 某些接口返回 200 但内容为空或异常
            content = resp.content or b""
            # 逐编码尝试解码中文
            for enc in ("utf-8", "gbk", "gb2312"):
                try:
                    return content.decode(enc)
                except Exception:
                    continue
            return content.decode(errors="ignore")
        except Exception:
            return None

    def _parse_js_like_object(self, text: str) -> Optional[Dict[str, Any]]:
        """将单引号 JS 对象文本转换为 Python dict。

        例：{'01':'北京','02':'上海'} 或 `var something = {'xx':'yy'}`
        """
        if not text:
            return None
        s = text.strip()
        # 去除可能的前缀，如 "var city_data ="
        m = re.search(r"\{.*\}", s, re.S)
        if not m:
            return None
        obj_text = m.group(0)
        # 将单引号替换为双引号，便于 json 解析
        obj_text = obj_text.replace("'", '"')
        try:
            return json.loads(obj_text)
        except Exception:
            return None

    def _fetch_city3j_json(self, url: str) -> Optional[Dict[str, Any]]:
        txt = self._get_text(url)
        if not txt:
            return None
        return self._parse_js_like_object(txt)

    def _valid_city_map(self, mp: Optional[Dict[str, Any]], prov_code: str) -> bool:
        if not isinstance(mp, dict) or not mp:
            return False
        keys = [str(k) for k in mp.keys()]
        # 情形1：provshi 结构，键为两位索引
        if any(len(k) == 2 for k in keys):
            return True
        # 情形2：全部键以省代码为前缀，且长度至少为 7（城市 7 位码）
        if keys and all(k.startswith(str(prov_code)) and len(k) >= 7 for k in keys):
            return True
        # 否则视为无效，以避免把上级省份列表（5位码集合）误判为城市列表
        return False

    def _valid_station_map(self, mp: Optional[Dict[str, Any]], city_code: str) -> bool:
        if not isinstance(mp, dict) or not mp:
            return False
        keys = [str(k) for k in mp.keys()]
        # 情形1：station 结构，键为两位索引
        if any(len(k) == 2 for k in keys):
            return True
        # 情形2：全部键以城市代码为前缀，且长度为 9（站点码）
        if keys and all(k.startswith(str(city_code)) and len(k) == 9 for k in keys):
            return True
        return False

    def _search_city_code_hierarchy(self, city: str) -> Optional[str]:
        city_name = (city or "").strip()
        for suf in ("市", "区", "县"):
            if city_name.endswith(suf):
                city_name = city_name[: -len(suf)]
                break

        prov_url = "http://www.weather.com.cn/data/city3jdata/china.html"
        prov_map = self._fetch_city3j_json(prov_url) or {}
        if not isinstance(prov_map, dict) or not prov_map:
            return None

        # 遍历所有省份并在其城市列表中查找匹配的城市
        for prov_code, _prov_name in prov_map.items():
            # 城市层级：多重回退以适配不同部署
            city_map: Optional[Dict[str, Any]] = None
            for city_url in [
                f"http://www.weather.com.cn/data/city3jdata/china.html?level=2&code={prov_code}",
                f"http://www.weather.com.cn/data/city3jdata/{prov_code}.html",
                f"http://www.weather.com.cn/data/city3jdata/provshi/{prov_code}.html",
            ]:
                mp = self._fetch_city3j_json(city_url)
                if self._valid_city_map(mp, prov_code):
                    city_map = mp
                    break
            if not self._valid_city_map(city_map, prov_code):
                continue

            # 规范城市代码：如 provshi 返回索引 '01'，拼接为 7 位码
            normalized_city_map: Dict[str, Any] = {}
            for c_code, c_name in city_map.items():
                cc = str(c_code)
                if not cc.startswith(str(prov_code)) and len(cc) == 2:
                    cc = f"{prov_code}{cc}"
                normalized_city_map[cc] = c_name

            matched_city_code: Optional[str] = None
            for c_code, c_name in normalized_city_map.items():
                if str(c_name) == city_name or (city_name and city_name in str(c_name)):
                    matched_city_code = str(c_code)
                    break
            
            if not matched_city_code:
                continue

            # 站点层级：多重回退以适配不同部署
            station_map: Optional[Dict[str, Any]] = None
            for station_url in [
                f"http://www.weather.com.cn/data/city3jdata/china.html?level=3&code={matched_city_code}",
                f"http://www.weather.com.cn/data/city3jdata/{matched_city_code}.html",
                f"http://www.weather.com.cn/data/city3jdata/station/{matched_city_code}.html",
            ]:
                mp = self._fetch_city3j_json(station_url)
                if self._valid_station_map(mp, matched_city_code):
                    station_map = mp
                    break

            if isinstance(station_map, dict) and station_map:
                # 规范站点代码：若键是索引 '01'，拼接形成 9 位码
                normalized_station_map: Dict[str, Any] = {}
                for s_code, s_name in station_map.items():
                    sc = str(s_code)
                    if not sc.startswith(str(matched_city_code)) and len(sc) == 2:
                        sc = f"{matched_city_code}{sc}"
                    normalized_station_map[sc] = s_name

                # 先精确匹配与城市同名的区县/站点
                for s_code, s_name in normalized_station_map.items():
                    if str(s_name) == city_name:
                        return str(s_code)
                # 包含匹配（如 “常州市区” 包含 “常州”）
                for s_code, s_name in normalized_station_map.items():
                    if city_name and city_name in str(s_name):
                        return str(s_code)
                # 无匹配时优先返回 '01' 对应的中心站
                fallback_code = f"{matched_city_code}01"
                if fallback_code in normalized_station_map:
                    return fallback_code

            # 若无站点列表，尝试 7 位后补 "00" -> 9 位
            if len(matched_city_code) == 7:
                return matched_city_code + "00"
            if len(matched_city_code) == 9:
                return matched_city_code

        return None

    async def resolve_city_code(self, city: str) -> Dict[str, Any]:
        try:
            code = self._search_city_code_hierarchy(city)
            if code:
                # 成功后写入本地 JSON（去重）
                try:
                    self._save_city_code_local(city, code)
                except Exception:
                    pass
                return {"success": True, "code": code, "city": city, "source": "resolve_city_code_network"}
            return {"success": False, "error": "未通过网络接口解析到城市代码", "city": city, "source": "resolve_city_code_network"}
        except Exception as e:
            return {"success": False, "error": str(e), "city": city, "source": "resolve_city_code_network"}

    # ===== 本地 JSON 存取：将网络解析到的城市代码写入 data/local_city_codes.json =====
    def _local_store_path(self) -> str:
        import os
        if self._store_path_cache:
            return self._store_path_cache
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.abspath(os.path.join(here, os.pardir, os.pardir, os.pardir))
        self._store_path_cache = os.path.join(root, "data", "local_city_codes.json")
        return self._store_path_cache

    def _ensure_local_city_codes_file(self) -> None:
        import os
        path = self._local_store_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def _load_local_city_codes(self) -> Dict[str, str]:
        import json
        path = self._local_store_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                return {str(k): str(v) for k, v in obj.items() if isinstance(v, (str, int))}
        except Exception:
            return {}
        return {}

    def _save_city_code_local(self, city: str, code: str) -> None:
        """将网络解析到的城市代码写入本地 JSON（去重）。

        - 保留键为用户输入的城市名称；值为 9 位代码
        - 若已存在且值一致则不改动；若值不同则更新
        - 同时保存去后缀的规范名（如“西安市”→“西安”），便于后续匹配
        """
        import json
        self._ensure_local_city_codes_file()
        mp = self._load_local_city_codes()
        changed = False

        raw_key = (city or "").strip()
        if raw_key:
            val = str(code)
            if mp.get(raw_key) != val:
                mp[raw_key] = val
                changed = True

        # 规范名（去后缀 市/区/县）
        norm = raw_key
        for suf in ("市", "区", "县"):
            if norm.endswith(suf):
                norm = norm[:-len(suf)]
                break
        if norm and norm != raw_key:
            if mp.get(norm) != str(code):
                mp[norm] = str(code)
                changed = True

        if changed:
            path = self._local_store_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(mp, f, ensure_ascii=False, indent=2)
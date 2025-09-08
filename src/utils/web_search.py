"""
网络搜索工具类
支持百度搜索功能
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote, urljoin
import time
import re
import json
from src.utils.logger import setup_logger
from src.config.settings import Settings

class WebSearchTool:
    """网络搜索工具类 - 仅支持百度搜索"""
    
    def __init__(self, settings: Settings):
        """初始化搜索工具"""
        self.settings = settings
        self.logger = setup_logger(settings)  # 传递settings对象而不是__name__
        self.session = None
        self.available_engines = ["baidu"]
        
        # 频率限制相关
        self.last_search_time = {}
        self.min_search_interval = 2  # 最小搜索间隔（秒）
        self.max_retries = 3  # 最大重试次数
    
    def _check_available_engines(self) -> List[str]:
        """检查可用的搜索引擎"""
        return ["baidu"]
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    def _should_skip_engine(self, engine: str) -> bool:
        """检查是否应该跳过某个搜索引擎（基于频率限制）"""
        current_time = time.time()
        last_time = self.last_search_time.get(engine, 0)
        
        if current_time - last_time < self.min_search_interval:
            return True
        return False
    
    def _update_search_time(self, engine: str):
        """更新搜索时间记录"""
        self.last_search_time[engine] = time.time()
    
    async def search_baidu(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """百度搜索"""
        try:
            encoded_query = quote(query)
            url = f"https://www.baidu.com/s?wd={encoded_query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            if self.session:
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        return self._parse_baidu_results(content, max_results)
            else:
                # 同步请求作为备用
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    return self._parse_baidu_results(response.text, max_results)
            
            return []
            
        except Exception as e:
            self.logger.error(f"百度搜索失败: {e}")
            return []
    
    async def search_baidu_ai(self, query: str, max_results: int = 5, search_recency_filter: str = "day") -> List[Dict[str, Any]]:
        """使用百度AI搜索API进行搜索"""
        try:
            if not self.settings.baidu_ai_search_token:
                self.logger.warning("百度AI搜索Token未配置，返回空结果")
                return []
            
            url = self.settings.baidu_ai_search_url
            
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "search_source": "baidu_search_v2",
                "search_recency_filter": search_recency_filter
            }
            
            headers = {
                'Authorization': f'Bearer {self.settings.baidu_ai_search_token}',
                'Content-Type': 'application/json'
            }
            
            # 添加调试信息
            self.logger.info(f"百度AI搜索请求URL: {url}")
            self.logger.info(f"百度AI搜索请求payload: {payload}")
            self.logger.info(f"百度AI搜索Token前缀: {self.settings.baidu_ai_search_token[:20]}...")
            
            # 使用异步请求
            if self.session:
                async with self.session.post(
                    url, 
                    json=payload, 
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._parse_baidu_ai_results(result, max_results)
                    else:
                        self.logger.error(f"百度AI搜索API请求失败: {response.status}")
                        response_text = await response.text()
                        self.logger.error(f"错误响应: {response_text}")
            else:
                # 同步请求作为备用
                response = requests.post(
                    url, 
                    json=payload, 
                    headers=headers, 
                    timeout=30
                )
                if response.status_code == 200:
                    result = response.json()
                    return self._parse_baidu_ai_results(result, max_results)
                else:
                    self.logger.error(f"百度AI搜索API请求失败: {response.status_code}")
                    self.logger.error(f"错误响应: {response.text}")
            
            # 不回退，返回空结果
            self.logger.info("百度AI搜索API请求失败，返回空结果")
            return []
            
        except Exception as e:
            self.logger.error(f"百度AI搜索异常: {e}")
            # 不回退，返回空结果
            return []
    
    def _parse_baidu_ai_results(self, api_result: Dict[str, Any], max_results: int) -> List[Dict[str, Any]]:
        """解析百度AI搜索API结果"""
        try:
            results = []
            
            # 添加调试信息
            self.logger.info(f"百度AI搜索API返回结果: {api_result}")
            
            # 检查API响应结构 - 处理references字段
            if "references" in api_result and isinstance(api_result["references"], list):
                references = api_result["references"]
                self.logger.info(f"找到 {len(references)} 个references结果")
                
                for i, item in enumerate(references[:max_results]):
                    try:
                        result = {
                            'title': item.get('title', ''),
                            'url': item.get('url', ''),
                            'snippet': item.get('content', '')[:3000] + '...' if len(item.get('content', '')) > 300 else item.get('content', ''),
                            'source': '百度AI搜索',
                            'date': item.get('date', ''),
                            'website': item.get('website', '')
                        }
                        
                        if result['title'] and result['url']:
                            results.append(result)
                            self.logger.info(f"成功解析第 {i+1} 个结果: {result['title']}")
                            
                    except Exception as e:
                        self.logger.debug(f"解析单个百度AI搜索结果失败: {e}")
                        continue
            
            # 兼容旧的API响应格式
            elif "choices" in api_result and len(api_result["choices"]) > 0:
                choice = api_result["choices"][0]
                
                # 提取搜索结果
                if "search_results" in choice:
                    search_results = choice["search_results"]
                    
                    for i, item in enumerate(search_results[:max_results]):
                        try:
                            result = {
                                'title': item.get('title', ''),
                                'url': item.get('url', ''),
                                'snippet': item.get('snippet', ''),
                                'source': '百度AI搜索'
                            }
                            
                            if result['title'] and result['url']:
                                results.append(result)
                                
                        except Exception as e:
                            self.logger.debug(f"解析单个百度AI搜索结果失败: {e}")
                            continue
                
                # 如果没有search_results字段，尝试从message content中提取
                elif "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]
                    # 这里可以添加从AI回答中提取搜索结果的逻辑
                    # 暂时返回一个包含AI回答的结果
                    results.append({
                        'title': '百度AI搜索结果',
                        'url': '',
                        'snippet': content[:200] + '...' if len(content) > 200 else content,
                        'source': '百度AI搜索'
                    })
            
            self.logger.info(f"百度AI搜索解析完成，返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            self.logger.error(f"解析百度AI搜索结果失败: {e}")
            return []
    
    def _parse_baidu_results(self, html_content: str, max_results: int) -> List[Dict[str, Any]]:
        """解析百度搜索结果"""
        try:
            print(f"🔍 开始解析百度HTML，内容长度: {len(html_content)}")
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            
            # 多种CSS选择器，提高解析成功率
            selectors = [
                'div.result.c-container',
                'div[class*="result"]',
                '.c-container',
                'div.c-container',
                'div[tpl]',  # 新增百度结果选择器
                '.result',   # 通用结果选择器
                'div[mu]'    # 百度移动端选择器
            ]
            
            items = []
            for selector in selectors:
                items = soup.select(selector)
                print(f"🔍 选择器 '{selector}' 找到 {len(items)} 个元素")
                if items:
                    break
            
            print(f"🔍 开始处理 {len(items[:max_results])} 个搜索结果项")
            for i, item in enumerate(items[:max_results]):
                try:
                    print(f"🔍 处理第 {i+1} 个结果项")
                    
                    # 提取标题 - 扩展选择器
                    title_selectors = ['h3 a', '.t a', 'a[data-click]', 'h3', '.c-title a', 'a[href*="baidu.com/link"]']
                    title_elem = None
                    title = ''
                    
                    for selector in title_selectors:
                        title_elem = item.select_one(selector)
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            print(f"🔍 标题选择器 '{selector}' 成功，标题: {title[:50]}...")
                            break
                    
                    # 提取链接
                    url = ''
                    if title_elem and title_elem.get('href'):
                        url = title_elem['href']
                        print(f"🔍 提取到链接: {url[:100]}...")
                    
                    # 提取摘要 - 扩展选择器
                    snippet_selectors = ['.c-abstract', '.c-span9', '.c-span-last', '.c-summary', 'p']
                    snippet = ''
                    for selector in snippet_selectors:
                        snippet_elem = item.select_one(selector)
                        if snippet_elem:
                            snippet = snippet_elem.get_text(strip=True)
                            if snippet:
                                print(f"🔍 摘要选择器 '{selector}' 成功，摘要: {snippet[:50]}...")
                                break
                    
                    if title and url:
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet,
                            'source': '百度'
                        })
                        print(f"✅ 成功添加第 {i+1} 个结果")
                    else:
                        print(f"❌ 第 {i+1} 个结果缺少标题或链接: title={bool(title)}, url={bool(url)}")
                        
                except Exception as e:
                    self.logger.debug(f"解析单个百度结果失败: {e}")
                    continue
            
            return results
            
        except Exception as e:
            self.logger.error(f"解析百度搜索结果失败: {e}")
            return []
    
    def _search_baidu_sync(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """百度同步搜索"""
        try:
            encoded_query = quote(query)
            url = f"https://www.baidu.com/s?wd={encoded_query}"
            print(f"🌐 百度搜索URL: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            print(f"🌐 发送HTTP请求...")
            response = requests.get(url, headers=headers, timeout=10)
            print(f"🌐 HTTP响应状态: {response.status_code}")
            print(f"🌐 响应内容长度: {len(response.text)}")
            
            if response.status_code == 200:
                if len(response.text) < 1000:
                    print(f"⚠️ 响应内容过短，可能被反爬虫拦截")
                    print(f"🌐 响应内容预览: {response.text[:500]}")
                return self._parse_baidu_results(response.text, max_results)
            else:
                print(f"❌ HTTP请求失败，状态码: {response.status_code}")
            
            return []
            
        except Exception as e:
            self.logger.error(f"百度同步搜索失败: {e}")
            return []
    
    async def search_with_fallback(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """带回退机制的搜索 - 仅使用百度"""
        if self._should_skip_engine("baidu"):
            self.logger.warning("百度搜索频率限制，跳过搜索")
            return []
        
        self._update_search_time("baidu")
        
        for attempt in range(self.max_retries):
            try:
                results = await self.search_baidu(query, max_results)
                if results:
                    return results
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)  # 重试前等待
                    
            except Exception as e:
                self.logger.error(f"百度搜索第{attempt + 1}次尝试失败: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2)  # 重试前等待更长时间
        
        return []
    
    async def comprehensive_search(self, query: str, max_results: int = 5, engines: List[str] = None) -> List[Dict[str, Any]]:
        """综合搜索 - 仅使用百度"""
        return await self.search_with_fallback(query, max_results)
    
    async def search_and_extract(self, query: str, max_results: int = 3, engines: List[str] = None) -> List[Dict[str, Any]]:
        """搜索并提取内容 - 仅使用百度"""
        results = await self.search_with_fallback(query, max_results)
        return results
    
    def search_sync(self, query: str, engine: str = "auto", max_results: int = 5) -> List[Dict[str, Any]]:
        """同步搜索方法 - 仅使用百度"""
        if self._should_skip_engine("baidu"):
            self.logger.warning("百度搜索频率限制，跳过搜索")
            return []
        
        self._update_search_time("baidu")
        
        for attempt in range(self.max_retries):
            try:
                results = self._search_baidu_sync(query, max_results)
                if results:
                    return results
                
                if attempt < self.max_retries - 1:
                    time.sleep(1)  # 重试前等待
                    
            except Exception as e:
                self.logger.error(f"百度同步搜索第{attempt + 1}次尝试失败: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2)  # 重试前等待更长时间
        
        return []
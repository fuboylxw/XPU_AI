"""时间查询工具类"""

import datetime
import pytz
from typing import Optional, Dict, Any
from src.utils.logger import setup_logger
from src.config.settings import Settings

class TimeQueryTool:
    """时间查询工具"""
    
    def __init__(self, settings: Settings = None):
        self.logger = setup_logger(settings) if settings else None
        # 常用时区映射
        self.timezone_map = {
            '北京': 'Asia/Shanghai',
            '上海': 'Asia/Shanghai',
            '中国': 'Asia/Shanghai',
            '东京': 'Asia/Tokyo',
            '纽约': 'America/New_York',
            '伦敦': 'Europe/London',
            '巴黎': 'Europe/Paris',
            '悉尼': 'Australia/Sydney',
            '洛杉矶': 'America/Los_Angeles',
            '芝加哥': 'America/Chicago',
            '莫斯科': 'Europe/Moscow',
            '新德里': 'Asia/Kolkata',
            '迪拜': 'Asia/Dubai'
        }
    
    def get_current_time(self, timezone_name: str = 'Asia/Shanghai') -> Dict[str, Any]:
        """获取当前时间"""
        try:
            # 获取指定时区
            if timezone_name in self.timezone_map:
                timezone_name = self.timezone_map[timezone_name]
            
            tz = pytz.timezone(timezone_name)
            current_time = datetime.datetime.now(tz)
            
            return {
                'success': True,
                'datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                'date': current_time.strftime('%Y-%m-%d'),
                'time': current_time.strftime('%H:%M:%S'),
                'weekday': current_time.strftime('%A'),
                'weekday_cn': self._get_chinese_weekday(current_time.weekday()),
                'timezone': timezone_name,
                'timestamp': current_time.timestamp(),
                'formatted': f"{current_time.strftime('%Y年%m月%d日 %H:%M:%S')} ({self._get_chinese_weekday(current_time.weekday())})"
            }
        except Exception as e:
            if self.logger:
                self.logger.error(f"获取时间失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '获取时间失败，请检查时区设置'
            }
    
    def get_time_difference(self, timezone1: str = 'Asia/Shanghai', timezone2: str = 'UTC') -> Dict[str, Any]:
        """计算两个时区的时间差"""
        try:
            # 处理时区名称映射
            if timezone1 in self.timezone_map:
                timezone1 = self.timezone_map[timezone1]
            if timezone2 in self.timezone_map:
                timezone2 = self.timezone_map[timezone2]
            
            tz1 = pytz.timezone(timezone1)
            tz2 = pytz.timezone(timezone2)
            
            now = datetime.datetime.now()
            time1 = tz1.localize(now.replace(tzinfo=None))
            time2 = tz2.localize(now.replace(tzinfo=None))
            
            # 转换为UTC进行比较
            utc_time1 = time1.astimezone(pytz.UTC)
            utc_time2 = time2.astimezone(pytz.UTC)
            
            diff = utc_time1 - utc_time2
            hours_diff = diff.total_seconds() / 3600
            
            return {
                'success': True,
                'timezone1': timezone1,
                'timezone2': timezone2,
                'time1': time1.strftime('%Y-%m-%d %H:%M:%S'),
                'time2': time2.strftime('%Y-%m-%d %H:%M:%S'),
                'difference_hours': hours_diff,
                'difference_formatted': f"{int(hours_diff)}小时{int((abs(hours_diff) % 1) * 60)}分钟"
            }
        except Exception as e:
            if self.logger:
                self.logger.error(f"计算时间差失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '计算时间差失败，请检查时区设置'
            }
    
    def parse_time_query(self, query: str) -> Dict[str, Any]:
        """解析时间查询"""
        query_lower = query.lower()
        
        # 检测时区
        detected_timezone = 'Asia/Shanghai'  # 默认北京时间
        for city, tz in self.timezone_map.items():
            if city in query:
                detected_timezone = tz
                break
        
        # 检测查询类型
        if any(keyword in query_lower for keyword in ['现在', '当前', '几点', '时间']):
            return self.get_current_time(detected_timezone)
        elif any(keyword in query_lower for keyword in ['日期', '今天', '几号']):
            result = self.get_current_time(detected_timezone)
            if result['success']:
                result['message'] = f"今天是{result['formatted'].split(' ')[0]}"
            return result
        elif any(keyword in query_lower for keyword in ['星期', '周几', '礼拜']):
            result = self.get_current_time(detected_timezone)
            if result['success']:
                result['message'] = f"今天是{result['weekday_cn']}"
            return result
        else:
            return self.get_current_time(detected_timezone)
    
    def _get_chinese_weekday(self, weekday: int) -> str:
        """获取中文星期"""
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        return weekdays[weekday]
    
    def get_tool_schema(self) -> Dict[str, Any]:
        """获取工具模式定义"""
        return {
            "type": "function",
            "function": {
                "name": "get_time_info",
                "description": "获取当前时间、日期信息，支持不同时区查询",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "时间查询内容，如'现在几点了'、'今天几号'、'北京时间'等"
                        },
                        "timezone": {
                            "type": "string",
                            "description": "时区名称，如'Asia/Shanghai'、'UTC'等，可选",
                            "default": "Asia/Shanghai"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    
    def execute_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行时间查询工具"""
        try:
            # 从参数中提取查询内容
            query = args.get('query', '现在几点')
            timezone = args.get('timezone', 'Asia/Shanghai')
            
            if self.logger:
                self.logger.info(f"执行时间查询: {query}")
            
            result = self.parse_time_query(query)
            
            if self.logger:
                self.logger.info(f"时间查询结果: {result}")
            
            return result
        except Exception as e:
            if self.logger:
                self.logger.error(f"时间查询工具执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '时间查询失败'
            }
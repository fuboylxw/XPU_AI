from typing import Dict, Any, List, Optional
import sqlite3
import json
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config.settings import settings
from src.chatbi.utils.logger import setup_logger

logger = setup_logger("query_tools")

class QueryTool:
    """数据库查询工具类"""
    
    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
    
    def query(self, query_text: str) -> str:
        """
        执行数据库查询
        
        Args:
            query_text: 用户查询文本
            
        Returns:
            查询结果
        """
        try:
            logger.info(f"数据库查询: {query_text}")
            
            # 检测查询类型
            query_type = self._detect_query_type(query_text)
            
            if query_type == "sql":
                return self._execute_sql_query(query_text)
            elif query_type == "natural_language":
                return self._execute_natural_language_query(query_text)
            elif query_type == "table_info":
                return self._get_table_info(query_text)
            else:
                return "请提供更具体的查询需求，比如：SQL查询、自然语言查询或表信息查询。"
                
        except Exception as e:
            logger.error(f"数据库查询错误: {e}")
            return f"数据库查询过程中出现错误: {str(e)}"
    
    def _detect_query_type(self, query_text: str) -> str:
        """检测查询类型"""
        query_lower = query_text.lower().strip()
        
        # 检测是否为SQL查询
        sql_keywords = ['select', 'insert', 'update', 'delete', 'create', 'alter', 'drop', 'show', 'describe']
        if any(query_lower.startswith(keyword) for keyword in sql_keywords):
            return "sql"
        
        # 检测是否为表信息查询
        if any(word in query_lower for word in ['表', 'table', '结构', 'schema', '字段', 'columns']):
            return "table_info"
        
        # 默认为自然语言查询
        return "natural_language"
    
    def _execute_sql_query(self, sql_query: str) -> str:
        """执行SQL查询"""
        try:
            with self.Session() as session:
                result = session.execute(text(sql_query))
                
                # 获取列名
                columns = list(result.keys())
                
                # 获取数据
                rows = result.fetchall()
                
                if not rows:
                    return "查询结果为空。"
                
                # 转换为DataFrame便于展示
                df = pd.DataFrame(rows, columns=columns)
                
                # 格式化输出
                output = f"查询结果（共{len(rows)}行）：\n\n"
                output += df.to_string(index=False)
                
                logger.info(f"SQL查询执行成功，返回{len(rows)}行数据")
                return output
                
        except Exception as e:
            logger.error(f"SQL查询执行错误: {e}")
            return f"SQL查询执行错误: {str(e)}"
    
    def _execute_natural_language_query(self, natural_query: str) -> str:
        """执行自然语言查询"""
        try:
            # 这里可以实现自然语言到SQL的转换
            # 目前返回示例数据
            
            # 模拟不同查询的结果
            if '用户' in natural_query or 'user' in natural_query.lower():
                return self._get_sample_user_data()
            elif '订单' in natural_query or 'order' in natural_query.lower():
                return self._get_sample_order_data()
            elif '销售' in natural_query or 'sale' in natural_query.lower():
                return self._get_sample_sales_data()
            else:
                return self._get_general_info()
                
        except Exception as e:
            logger.error(f"自然语言查询执行错误: {e}")
            return f"自然语言查询执行错误: {str(e)}"
    
    def _get_table_info(self, query_text: str) -> str:
        """获取表信息"""
        try:
            # 获取所有表名
            with self.Session() as session:
                if 'sqlite' in self.db_url:
                    result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
                else:
                    result = session.execute(text("SHOW TABLES;"))
                
                tables = [row[0] for row in result.fetchall()]
                
                if not tables:
                    return "数据库中没有找到表。"
                
                info = "数据库中的表：\n"
                for table in tables:
                    info += f"- {table}\n"
                
                logger.info(f"返回表信息，共{len(tables)}个表")
                return info
                
        except Exception as e:
            logger.error(f"获取表信息错误: {e}")
            return f"获取表信息错误: {str(e)}"
    
    def _get_sample_user_data(self) -> str:
        """获取示例用户数据"""
        sample_data = [
            {"用户ID": 1, "用户名": "张三", "邮箱": "zhangsan@example.com", "注册时间": "2024-01-15"},
            {"用户ID": 2, "用户名": "李四", "邮箱": "lisi@example.com", "注册时间": "2024-02-20"},
            {"用户ID": 3, "用户名": "王五", "邮箱": "wangwu@example.com", "注册时间": "2024-03-10"},
        ]
        
        result = "用户数据查询结果：\n\n"
        for user in sample_data:
            result += f"- 用户ID: {user['用户ID']}, 用户名: {user['用户名']}, 邮箱: {user['邮箱']}, 注册时间: {user['注册时间']}\n"
        
        return result
    
    def _get_sample_order_data(self) -> str:
        """获取示例订单数据"""
        sample_data = [
            {"订单ID": 1001, "用户ID": 1, "订单金额": 299.99, "订单状态": "已完成", "下单时间": "2024-09-01 10:30:00"},
            {"订单ID": 1002, "用户ID": 2, "订单金额": 599.50, "订单状态": "处理中", "下单时间": "2024-09-02 14:15:00"},
            {"订单ID": 1003, "用户ID": 3, "订单金额": 149.99, "订单状态": "已取消", "下单时间": "2024-09-03 09:45:00"},
        ]
        
        result = "订单数据查询结果：\n\n"
        for order in sample_data:
            result += f"- 订单ID: {order['订单ID']}, 用户ID: {order['用户ID']}, 订单金额: ¥{order['订单金额']}, 状态: {order['订单状态']}, 下单时间: {order['下单时间']}\n"
        
        return result
    
    def _get_sample_sales_data(self) -> str:
        """获取示例销售数据"""
        sample_data = [
            {"日期": "2024-09-01", "销售额": 12500.00, "订单数": 45, "平均订单金额": 277.78},
            {"日期": "2024-09-02", "销售额": 15800.50, "订单数": 52, "平均订单金额": 303.86},
            {"日期": "2024-09-03", "销售额": 13200.25, "订单数": 38, "平均订单金额": 347.38},
        ]
        
        result = "销售数据查询结果：\n\n"
        for sale in sample_data:
            result += f"- 日期: {sale['日期']}, 销售额: ¥{sale['销售额']}, 订单数: {sale['订单数']}, 平均订单金额: ¥{sale['平均订单金额']}\n"
        
        return result
    
    def _get_general_info(self) -> str:
        """获取通用信息"""
        return "欢迎使用数据库查询功能！您可以：\n\n" \
               "1. 执行SQL查询（如：SELECT * FROM users LIMIT 10）\n" \
               "2. 进行自然语言查询（如：显示用户数据）\n" \
               "3. 获取表信息（如：显示所有表）\n\n" \
               "请告诉我您想要查询什么数据？"
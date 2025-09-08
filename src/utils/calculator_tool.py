"""计算器工具类"""

import re
import math
from typing import Dict, Any, Optional
from src.utils.logger import setup_logger
from src.config.settings import Settings

class CalculatorTool:
    """计算器工具"""
    
    def __init__(self, settings: Settings = None):
        self.logger = setup_logger(settings) if settings else None
        
        # 支持的数学函数
        self.math_functions = {
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'asin': math.asin,
            'acos': math.acos,
            'atan': math.atan,
            'log': math.log10,
            'ln': math.log,
            'sqrt': math.sqrt,
            'abs': abs,
            'ceil': math.ceil,
            'floor': math.floor,
            'round': round,
            'exp': math.exp,
            'pi': math.pi,
            'e': math.e
        }
    
    def _is_valid_expression(self, expression: str) -> bool:
        """检查是否为有效的数学表达式"""
        try:
            # 移除空格
            expr = expression.strip().replace(' ', '')
            
            # 检查是否包含数学运算符或函数
            math_pattern = r'[+\-*/()^]|\d+|sin|cos|tan|log|sqrt|pi|e'
            if not re.search(math_pattern, expr):
                return False
            
            # 简单的安全检查
            dangerous_patterns = ['import', 'exec', 'eval', '__', 'open', 'file']
            for pattern in dangerous_patterns:
                if pattern in expr.lower():
                    return False
            
            return True
        except:
            return False
    
    def _safe_eval(self, expression: str) -> float:
        """安全地计算数学表达式"""
        try:
            # 预处理表达式
            expr = expression.strip().replace(' ', '')
            
            # 替换数学函数
            for func_name, func in self.math_functions.items():
                if isinstance(func, (int, float)):
                    expr = expr.replace(func_name, str(func))
                else:
                    # 处理函数调用
                    pattern = f'{func_name}\\(([^)]+)\\)'
                    matches = re.findall(pattern, expr)
                    for match in matches:
                        try:
                            arg_value = self._safe_eval(match)
                            result = func(arg_value)
                            expr = expr.replace(f'{func_name}({match})', str(result))
                        except:
                            continue
            
            # 替换^为**（幂运算）
            expr = expr.replace('^', '**')
            
            # 使用eval计算（在受限环境中）
            allowed_names = {
                '__builtins__': {},
                'abs': abs,
                'round': round,
                'pow': pow,
                'max': max,
                'min': min
            }
            
            result = eval(expr, allowed_names)
            return float(result)
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"计算表达式失败: {expression}, 错误: {e}")
            raise ValueError(f"无法计算表达式: {expression}")
    
    def parse_calculation_query(self, query: str) -> Dict[str, Any]:
        """解析计算查询"""
        try:
            # 提取数学表达式
            # 移除常见的中文描述词
            clean_query = query
            remove_words = ['计算', '算一下', '等于多少', '结果是', '帮我算', '请算']
            for word in remove_words:
                clean_query = clean_query.replace(word, '')
            
            clean_query = clean_query.strip()
            
            if not self._is_valid_expression(clean_query):
                return {
                    'success': False,
                    'error': '无效的数学表达式',
                    'message': '请输入有效的数学表达式'
                }
            
            # 计算结果
            result = self._safe_eval(clean_query)
            
            # 格式化结果
            if result.is_integer():
                formatted_result = str(int(result))
            else:
                formatted_result = f"{result:.6f}".rstrip('0').rstrip('.')
            
            return {
                'success': True,
                'expression': clean_query,
                'result': result,
                'formatted_result': formatted_result,
                'message': f'{clean_query} = {formatted_result}'
            }
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"解析计算查询失败: {query}, 错误: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '计算失败，请检查表达式是否正确'
            }
    
    def get_tool_schema(self) -> Dict[str, Any]:
        """获取工具模式定义"""
        return {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "执行数学计算，支持基本运算、三角函数、对数等",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "要计算的数学表达式，如'2+3*4'、'sin(30)'、'sqrt(16)'等"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
    
    def execute_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行计算工具"""
        try:
            expression = args.get('expression', '')
            if self.logger:
                self.logger.info(f"执行计算: {expression}")
            
            result = self.parse_calculation_query(expression)
            
            if self.logger:
                self.logger.info(f"计算结果: {result}")
            
            return result
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"计算工具执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '计算工具执行失败'
            }
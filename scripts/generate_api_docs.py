#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API文档生成脚本

该脚本用于自动生成API文档、OpenAPI规范和接口测试报告。

功能:
1. 生成OpenAPI JSON/YAML文档
2. 生成HTML格式的API文档
3. 运行API测试并生成报告
4. 验证API规范的完整性

使用方法:
    python scripts/generate_api_docs.py [options]

选项:
    --format: 输出格式 (json, yaml, html, all)
    --output: 输出目录
    --test: 是否运行测试
    --serve: 是否启动文档服务器
"""

import os
import sys
import json
import yaml
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from fastapi import FastAPI
    from fastapi.openapi.utils import get_openapi
    import uvicorn
except ImportError:
    print("错误: 缺少必要的依赖包，请运行: pip install fastapi uvicorn")
    sys.exit(1)


class APIDocGenerator:
    """API文档生成器"""
    
    def __init__(self, output_dir: str = "docs/api"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.app = None
        
    def load_app(self) -> Optional[FastAPI]:
        """加载FastAPI应用"""
        try:
            # 尝试导入API应用
            from api.main import app
            self.app = app
            return app
        except ImportError as e:
            print(f"警告: 无法导入API应用: {e}")
            # 创建一个基础的FastAPI应用用于文档生成
            app = FastAPI(
                title="XPU AI API",
                description="西安石油大学AI助手API接口文档",
                version="1.0.0"
            )
            self.app = app
            return app
    
    def generate_openapi_spec(self) -> Dict[str, Any]:
        """生成OpenAPI规范"""
        if not self.app:
            self.load_app()
            
        # 自定义OpenAPI规范
        openapi_schema = get_openapi(
            title="XPU AI API",
            version="1.0.0",
            description="""
            # XPU AI API 接口文档
            
            西安石油大学AI助手系统的RESTful API接口文档。
            
            ## 功能特性
            
            - 🤖 智能对话：支持上下文理解的AI对话
            - 📚 文档管理：文档上传、搜索和管理
            - 🔍 语义搜索：基于向量的智能文档搜索
            - 💬 会话管理：多会话支持和历史记录
            - 🔒 安全认证：API密钥和权限控制
            - 📊 流式响应：支持实时流式对话
            
            ## 认证方式
            
            API使用API密钥进行认证，请在请求头中包含：
            ```
            X-API-Key: your-api-key
            ```
            
            ## 错误处理
            
            API使用标准HTTP状态码，错误响应格式：
            ```json
            {
                "success": false,
                "error": {
                    "code": "ERROR_CODE",
                    "message": "错误描述",
                    "details": {}
                }
            }
            ```
            
            ## 限流
            
            API实施限流策略：
            - 每分钟最多100次请求
            - 每小时最多1000次请求
            - 超出限制返回429状态码
            """,
            routes=self.app.routes,
            servers=[
                {"url": "http://202.200.206.248:8000", "description": "开发环境"},
                {"url": "https://api.xpu.edu.cn", "description": "生产环境"}
            ]
        )
        
        # 添加安全方案
        openapi_schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API密钥认证"
            }
        }
        
        # 为所有路径添加安全要求
        for path in openapi_schema["paths"].values():
            for method in path.values():
                if isinstance(method, dict) and "security" not in method:
                    method["security"] = [{"ApiKeyAuth": []}]
        
        # 添加通用响应模型
        openapi_schema["components"]["schemas"].update({
            "SuccessResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "data": {"type": "object"},
                    "message": {"type": "string", "example": "操作成功"}
                },
                "required": ["success"]
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": False},
                    "error": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "example": "VALIDATION_ERROR"},
                            "message": {"type": "string", "example": "请求参数验证失败"},
                            "details": {"type": "object"}
                        },
                        "required": ["code", "message"]
                    }
                },
                "required": ["success", "error"]
            }
        })
        
        return openapi_schema
    
    def save_json(self, spec: Dict[str, Any], filename: str = "openapi.json") -> Path:
        """保存JSON格式的OpenAPI规范"""
        file_path = self.output_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
        print(f"✓ JSON文档已保存到: {file_path}")
        return file_path
    
    def save_yaml(self, spec: Dict[str, Any], filename: str = "openapi.yaml") -> Path:
        """保存YAML格式的OpenAPI规范"""
        file_path = self.output_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(spec, f, default_flow_style=False, allow_unicode=True, indent=2)
        print(f"✓ YAML文档已保存到: {file_path}")
        return file_path
    
    def generate_html_docs(self, spec: Dict[str, Any], filename: str = "index.html") -> Path:
        """生成HTML格式的API文档"""
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XPU AI API 文档</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        html {
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }
        *, *:before, *:after {
            box-sizing: inherit;
        }
        body {
            margin:0;
            background: #fafafa;
        }
        .swagger-ui .topbar {
            background-color: #1976d2;
        }
        .swagger-ui .topbar .download-url-wrapper .select-label {
            color: #fff;
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                spec: {spec_json},
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                defaultModelsExpandDepth: 1,
                defaultModelExpandDepth: 1,
                docExpansion: "list",
                filter: true,
                showExtensions: true,
                showCommonExtensions: true,
                tryItOutEnabled: true
            });
        };
    </script>
</body>
</html>
        """
        
        html_content = html_template.replace(
            "{spec_json}", 
            json.dumps(spec, ensure_ascii=False)
        )
        
        file_path = self.output_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ HTML文档已保存到: {file_path}")
        return file_path
    
    def run_api_tests(self) -> bool:
        """运行API测试"""
        print("\n🧪 运行API测试...")
        
        test_dir = project_root / "tests"
        if not test_dir.exists():
            print("❌ 测试目录不存在")
            return False
        
        try:
            # 运行pytest并生成HTML报告
            cmd = [
                sys.executable, "-m", "pytest", 
                str(test_dir / "test_api.py"),
                "-v",
                "--tb=short",
                "--html=" + str(self.output_dir / "test_report.html"),
                "--self-contained-html",
                "--maxfail=10"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            # 保存测试输出
            with open(self.output_dir / "test_output.txt", 'w', encoding='utf-8') as f:
                f.write(f"命令: {' '.join(cmd)}\n\n")
                f.write(f"返回码: {result.returncode}\n\n")
                f.write("标准输出:\n")
                f.write(result.stdout)
                f.write("\n\n标准错误:\n")
                f.write(result.stderr)
            
            if result.returncode == 0:
                print("✓ API测试全部通过")
                return True
            else:
                print(f"⚠ API测试完成，部分测试失败 (退出码: {result.returncode})")
                print("详细信息请查看测试报告")
                return False
                
        except Exception as e:
            print(f"❌ 运行测试时出错: {e}")
            return False
    
    def validate_spec(self, spec: Dict[str, Any]) -> bool:
        """验证OpenAPI规范的完整性"""
        print("\n🔍 验证API规范...")
        
        required_fields = ['openapi', 'info', 'paths']
        missing_fields = [field for field in required_fields if field not in spec]
        
        if missing_fields:
            print(f"❌ 缺少必需字段: {missing_fields}")
            return False
        
        # 检查路径数量
        path_count = len(spec.get('paths', {}))
        if path_count == 0:
            print("⚠ 警告: 没有定义任何API路径")
        else:
            print(f"✓ 发现 {path_count} 个API端点")
        
        # 检查组件
        components = spec.get('components', {})
        schema_count = len(components.get('schemas', {}))
        security_count = len(components.get('securitySchemes', {}))
        
        print(f"✓ 发现 {schema_count} 个数据模型")
        print(f"✓ 发现 {security_count} 个安全方案")
        
        # 检查每个路径的方法
        total_operations = 0
        for path, methods in spec.get('paths', {}).items():
            for method, operation in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']:
                    total_operations += 1
        
        print(f"✓ 总共 {total_operations} 个API操作")
        print("✓ API规范验证通过")
        return True
    
    def serve_docs(self, port: int = 8080):
        """启动文档服务器"""
        html_file = self.output_dir / "index.html"
        if not html_file.exists():
            print("❌ HTML文档不存在，请先生成文档")
            return
        
        print(f"\n🌐 启动文档服务器...")
        print(f"📖 文档地址: http://202.200.206.248:{port}")
        print("按 Ctrl+C 停止服务器")
        
        try:
            import http.server
            import socketserver
            import webbrowser
            
            os.chdir(self.output_dir)
            
            handler = http.server.SimpleHTTPRequestHandler
            with socketserver.TCPServer(("", port), handler) as httpd:
                # 自动打开浏览器
                webbrowser.open(f"http://202.200.206.248:{port}")
                httpd.serve_forever()
                
        except KeyboardInterrupt:
            print("\n👋 文档服务器已停止")
        except Exception as e:
            print(f"❌ 启动服务器失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="生成API文档和测试报告",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--format", 
        choices=["json", "yaml", "html", "all"],
        default="all",
        help="输出格式 (默认: all)"
    )
    
    parser.add_argument(
        "--output", 
        default="docs/api",
        help="输出目录 (默认: docs/api)"
    )
    
    parser.add_argument(
        "--test", 
        action="store_true",
        help="运行API测试"
    )
    
    parser.add_argument(
        "--serve", 
        action="store_true",
        help="启动文档服务器"
    )
    
    parser.add_argument(
        "--port", 
        type=int,
        default=8080,
        help="文档服务器端口 (默认: 8080)"
    )
    
    args = parser.parse_args()
    
    print("🚀 XPU AI API 文档生成器")
    print("=" * 50)
    
    # 创建文档生成器
    generator = APIDocGenerator(args.output)
    
    # 生成OpenAPI规范
    print("\n📝 生成API规范...")
    spec = generator.generate_openapi_spec()
    
    # 验证规范
    if not generator.validate_spec(spec):
        print("❌ API规范验证失败")
        return 1
    
    # 生成文档
    print("\n📚 生成文档文件...")
    
    if args.format in ["json", "all"]:
        generator.save_json(spec)
    
    if args.format in ["yaml", "all"]:
        generator.save_yaml(spec)
    
    if args.format in ["html", "all"]:
        generator.generate_html_docs(spec)
    
    # 运行测试
    if args.test:
        test_success = generator.run_api_tests()
        if not test_success:
            print("⚠ 测试未全部通过，请检查测试报告")
    
    # 启动文档服务器
    if args.serve:
        generator.serve_docs(args.port)
    
    print("\n✅ 文档生成完成!")
    print(f"📁 输出目录: {generator.output_dir.absolute()}")
    
    if not args.serve:
        print(f"\n💡 提示: 使用 --serve 参数可以启动文档服务器")
        print(f"   python {__file__} --serve")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
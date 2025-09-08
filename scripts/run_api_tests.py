#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API测试和文档生成自动化脚本

该脚本用于自动化运行API相关的所有测试和文档生成任务。

功能:
1. 运行API单元测试
2. 运行API集成测试
3. 生成API文档
4. 运行性能测试
5. 生成测试报告
6. 检查代码覆盖率

使用方法:
    python scripts/run_api_tests.py [options]

选项:
    --skip-unit: 跳过单元测试
    --skip-integration: 跳过集成测试
    --skip-docs: 跳过文档生成
    --skip-performance: 跳过性能测试
    --coverage: 生成代码覆盖率报告
    --output: 报告输出目录
"""

import os
import sys
import time
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Colors:
    """终端颜色常量"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class TestRunner:
    """测试运行器"""
    
    def __init__(self, project_root: Path, output_dir: str = "reports"):
        self.project_root = project_root
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 测试结果
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'project_root': str(project_root),
            'tests': {}
        }
    
    def print_header(self, title: str):
        """打印标题"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{title.center(60)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")
    
    def print_step(self, step: str):
        """打印步骤"""
        print(f"{Colors.BOLD}{Colors.BLUE}🔄 {step}{Colors.END}")
    
    def print_success(self, message: str):
        """打印成功消息"""
        print(f"{Colors.GREEN}✅ {message}{Colors.END}")
    
    def print_warning(self, message: str):
        """打印警告消息"""
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")
    
    def print_error(self, message: str):
        """打印错误消息"""
        print(f"{Colors.RED}❌ {message}{Colors.END}")
    
    def run_command(self, command: List[str], cwd: Optional[Path] = None, 
                   capture_output: bool = True, timeout: int = 300) -> Tuple[bool, str, str]:
        """运行命令"""
        if cwd is None:
            cwd = self.project_root
        
        try:
            print(f"  运行命令: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", f"命令超时 ({timeout}秒)"
        except Exception as e:
            return False, "", f"命令执行失败: {str(e)}"
    
    def check_dependencies(self) -> bool:
        """检查依赖"""
        self.print_step("检查依赖")
        
        required_packages = [
            'pytest', 'fastapi', 'uvicorn', 'requests', 
            'aiohttp', 'psutil', 'matplotlib', 'pandas'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            success, _, _ = self.run_command([sys.executable, '-c', f'import {package}'])
            if not success:
                missing_packages.append(package)
        
        if missing_packages:
            self.print_error(f"缺少依赖包: {', '.join(missing_packages)}")
            print(f"请运行: pip install {' '.join(missing_packages)}")
            return False
        
        self.print_success("所有依赖已安装")
        return True
    
    def start_api_server(self) -> Optional[subprocess.Popen]:
        """启动API服务器"""
        self.print_step("启动API服务器")
        
        try:
            # 检查API服务器是否已经运行
            success, _, _ = self.run_command(
                        ['curl', '-s', 'http://202.200.206.248:8000/health'],
                        timeout=5
                    )
            
            if success:
                self.print_success("API服务器已在运行")
                return None
            
            # 启动API服务器
            api_script = self.project_root / 'api' / 'main.py'
            if not api_script.exists():
                self.print_error(f"API脚本不存在: {api_script}")
                return None
            
            process = subprocess.Popen(
                [sys.executable, str(api_script)],
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务器启动
            for i in range(30):  # 最多等待30秒
                time.sleep(1)
                try:
                    success, _, _ = self.run_command(
                        ['curl', '-s', 'http://202.200.206.248:8000/health'],
                        timeout=2
                    )
                    if success:
                        self.print_success("API服务器启动成功")
                        return process
                except:
                    pass
                
                print(f"  等待服务器启动... ({i+1}/30)")
            
            self.print_error("API服务器启动超时")
            process.terminate()
            return None
            
        except Exception as e:
            self.print_error(f"启动API服务器失败: {e}")
            return None
    
    def run_unit_tests(self, coverage: bool = False) -> bool:
        """运行单元测试"""
        self.print_step("运行单元测试")
        
        test_dir = self.project_root / 'tests'
        if not test_dir.exists():
            self.print_error(f"测试目录不存在: {test_dir}")
            return False
        
        # 构建pytest命令
        cmd = [sys.executable, '-m', 'pytest']
        
        if coverage:
            cmd.extend(['--cov=src', '--cov=api', '--cov-report=html', '--cov-report=term'])
            cmd.append(f'--cov-report=html:{self.output_dir}/coverage')
        
        cmd.extend([
            str(test_dir),
            '-v',
            '--tb=short',
            f'--junitxml={self.output_dir}/unit_tests.xml',
            '--disable-warnings'
        ])
        
        success, stdout, stderr = self.run_command(cmd, timeout=600)
        
        # 保存测试结果
        self.test_results['tests']['unit_tests'] = {
            'success': success,
            'stdout': stdout,
            'stderr': stderr,
            'command': ' '.join(cmd)
        }
        
        if success:
            self.print_success("单元测试通过")
        else:
            self.print_error("单元测试失败")
            print(f"错误输出: {stderr}")
        
        return success
    
    def run_integration_tests(self) -> bool:
        """运行集成测试"""
        self.print_step("运行集成测试")
        
        # 运行API集成测试
        test_file = self.project_root / 'tests' / 'test_api.py'
        if not test_file.exists():
            self.print_error(f"API测试文件不存在: {test_file}")
            return False
        
        cmd = [
            sys.executable, '-m', 'pytest',
            str(test_file),
            '-v',
            '--tb=short',
            f'--junitxml={self.output_dir}/integration_tests.xml',
            '-k', 'test_',  # 只运行测试函数
            '--disable-warnings'
        ]
        
        success, stdout, stderr = self.run_command(cmd, timeout=600)
        
        # 保存测试结果
        self.test_results['tests']['integration_tests'] = {
            'success': success,
            'stdout': stdout,
            'stderr': stderr,
            'command': ' '.join(cmd)
        }
        
        if success:
            self.print_success("集成测试通过")
        else:
            self.print_error("集成测试失败")
            print(f"错误输出: {stderr}")
        
        return success
    
    def generate_api_docs(self) -> bool:
        """生成API文档"""
        self.print_step("生成API文档")
        
        docs_script = self.project_root / 'scripts' / 'generate_api_docs.py'
        if not docs_script.exists():
            self.print_error(f"文档生成脚本不存在: {docs_script}")
            return False
        
        docs_output = self.output_dir / 'api_docs'
        
        cmd = [
            sys.executable, str(docs_script),
            '--output', str(docs_output),
            '--format', 'all'
        ]
        
        success, stdout, stderr = self.run_command(cmd, timeout=300)
        
        # 保存结果
        self.test_results['tests']['api_docs'] = {
            'success': success,
            'stdout': stdout,
            'stderr': stderr,
            'command': ' '.join(cmd),
            'output_dir': str(docs_output)
        }
        
        if success:
            self.print_success(f"API文档已生成: {docs_output}")
        else:
            self.print_error("API文档生成失败")
            print(f"错误输出: {stderr}")
        
        return success
    
    def run_performance_tests(self) -> bool:
        """运行性能测试"""
        self.print_step("运行性能测试")
        
        perf_script = self.project_root / 'scripts' / 'api_performance_test.py'
        if not perf_script.exists():
            self.print_error(f"性能测试脚本不存在: {perf_script}")
            return False
        
        perf_output = self.output_dir / 'performance'
        
        cmd = [
            sys.executable, str(perf_script),
            '--url', 'http://202.200.206.248:8000',
            '--test-type', 'response',  # 只运行响应时间测试，避免过长时间
            '--output', str(perf_output)
        ]
        
        success, stdout, stderr = self.run_command(cmd, timeout=600)
        
        # 保存结果
        self.test_results['tests']['performance_tests'] = {
            'success': success,
            'stdout': stdout,
            'stderr': stderr,
            'command': ' '.join(cmd),
            'output_dir': str(perf_output)
        }
        
        if success:
            self.print_success(f"性能测试完成: {perf_output}")
        else:
            self.print_error("性能测试失败")
            print(f"错误输出: {stderr}")
        
        return success
    
    def generate_summary_report(self):
        """生成汇总报告"""
        self.print_step("生成汇总报告")
        
        # 计算总体统计
        total_tests = len(self.test_results['tests'])
        passed_tests = sum(1 for test in self.test_results['tests'].values() if test['success'])
        failed_tests = total_tests - passed_tests
        
        # 生成JSON报告
        json_report = {
            **self.test_results,
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            }
        }
        
        with open(self.output_dir / 'test_summary.json', 'w', encoding='utf-8') as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2)
        
        # 生成HTML报告
        html_report = self._generate_html_summary(json_report)
        with open(self.output_dir / 'test_summary.html', 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        self.print_success(f"汇总报告已生成: {self.output_dir}")
        
        # 打印摘要
        print(f"\n{Colors.BOLD}📊 测试摘要:{Colors.END}")
        print(f"  总测试数: {total_tests}")
        print(f"  通过: {Colors.GREEN}{passed_tests}{Colors.END}")
        print(f"  失败: {Colors.RED}{failed_tests}{Colors.END}")
        print(f"  成功率: {Colors.CYAN}{passed_tests/total_tests*100:.1f}%{Colors.END}")
    
    def _generate_html_summary(self, report_data: Dict) -> str:
        """生成HTML汇总报告"""
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API测试汇总报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1, h2 { color: #333; }
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .summary-card { background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }
        .summary-card.success { border-left: 4px solid #28a745; }
        .summary-card.error { border-left: 4px solid #dc3545; }
        .summary-card.info { border-left: 4px solid #007bff; }
        .metric-value { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
        .metric-label { color: #666; font-size: 14px; }
        .test-results { margin: 20px 0; }
        .test-item { background: #f8f9fa; margin: 10px 0; padding: 15px; border-radius: 6px; }
        .test-item.success { border-left: 4px solid #28a745; }
        .test-item.error { border-left: 4px solid #dc3545; }
        .test-name { font-weight: bold; margin-bottom: 10px; }
        .test-command { font-family: monospace; background: #e9ecef; padding: 5px; border-radius: 3px; font-size: 12px; }
        .success { color: #28a745; }
        .error { color: #dc3545; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 API测试汇总报告</h1>
        <p><strong>生成时间:</strong> {timestamp}</p>
        <p><strong>项目路径:</strong> {project_root}</p>
        
        <div class="summary-grid">
            <div class="summary-card info">
                <div class="metric-value">{total_tests}</div>
                <div class="metric-label">总测试数</div>
            </div>
            <div class="summary-card success">
                <div class="metric-value success">{passed_tests}</div>
                <div class="metric-label">通过测试</div>
            </div>
            <div class="summary-card error">
                <div class="metric-value error">{failed_tests}</div>
                <div class="metric-label">失败测试</div>
            </div>
            <div class="summary-card info">
                <div class="metric-value">{success_rate:.1f}%</div>
                <div class="metric-label">成功率</div>
            </div>
        </div>
        
        <h2>📋 测试详情</h2>
        <div class="test-results">
            {test_details}
        </div>
    </div>
</body>
</html>
        """
        
        # 生成测试详情
        test_details = []
        for test_name, test_data in report_data['tests'].items():
            status_class = 'success' if test_data['success'] else 'error'
            status_text = '✅ 通过' if test_data['success'] else '❌ 失败'
            
            test_html = f"""
            <div class="test-item {status_class}">
                <div class="test-name">{test_name} - {status_text}</div>
                <div class="test-command">{test_data['command']}</div>
                {f'<pre>{test_data["stderr"]}</pre>' if test_data['stderr'] and not test_data['success'] else ''}
            </div>
            """
            test_details.append(test_html)
        
        return html_template.format(
            timestamp=report_data['timestamp'],
            project_root=report_data['project_root'],
            total_tests=report_data['summary']['total_tests'],
            passed_tests=report_data['summary']['passed_tests'],
            failed_tests=report_data['summary']['failed_tests'],
            success_rate=report_data['summary']['success_rate'],
            test_details=''.join(test_details)
        )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="API测试和文档生成自动化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--skip-unit",
        action="store_true",
        help="跳过单元测试"
    )
    
    parser.add_argument(
        "--skip-integration",
        action="store_true",
        help="跳过集成测试"
    )
    
    parser.add_argument(
        "--skip-docs",
        action="store_true",
        help="跳过文档生成"
    )
    
    parser.add_argument(
        "--skip-performance",
        action="store_true",
        help="跳过性能测试"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="生成代码覆盖率报告"
    )
    
    parser.add_argument(
        "--output",
        default="reports",
        help="报告输出目录 (默认: reports)"
    )
    
    parser.add_argument(
        "--no-server",
        action="store_true",
        help="不启动API服务器（假设已在运行）"
    )
    
    args = parser.parse_args()
    
    # 创建测试运行器
    runner = TestRunner(project_root, args.output)
    
    runner.print_header("API测试和文档生成自动化工具")
    
    # 检查依赖
    if not runner.check_dependencies():
        return 1
    
    # 启动API服务器
    api_process = None
    if not args.no_server:
        api_process = runner.start_api_server()
        if api_process is None and not args.skip_integration and not args.skip_performance:
            runner.print_error("无法启动API服务器，跳过需要服务器的测试")
            args.skip_integration = True
            args.skip_performance = True
    
    try:
        # 运行测试
        all_passed = True
        
        if not args.skip_unit:
            if not runner.run_unit_tests(args.coverage):
                all_passed = False
        
        if not args.skip_integration:
            if not runner.run_integration_tests():
                all_passed = False
        
        if not args.skip_docs:
            if not runner.generate_api_docs():
                all_passed = False
        
        if not args.skip_performance:
            if not runner.run_performance_tests():
                all_passed = False
        
        # 生成汇总报告
        runner.generate_summary_report()
        
        # 最终结果
        if all_passed:
            runner.print_success("所有测试通过！")
            return 0
        else:
            runner.print_error("部分测试失败")
            return 1
    
    finally:
        # 清理API服务器
        if api_process:
            runner.print_step("停止API服务器")
            api_process.terminate()
            try:
                api_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api_process.kill()
            runner.print_success("API服务器已停止")


if __name__ == "__main__":
    sys.exit(main())
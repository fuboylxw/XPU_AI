#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API性能测试脚本

该脚本用于测试API的性能指标，包括响应时间、吞吐量、并发能力等。

功能:
1. 响应时间测试
2. 并发性能测试
3. 负载测试
4. 压力测试
5. 内存和CPU使用率监控
6. 生成性能报告

使用方法:
    python scripts/api_performance_test.py [options]

选项:
    --url: API基础URL
    --duration: 测试持续时间(秒)
    --concurrent: 并发用户数
    --rps: 每秒请求数
    --output: 报告输出目录
"""

import os
import sys
import time
import json
import asyncio
import argparse
import threading
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    import aiohttp
    import psutil
    import matplotlib.pyplot as plt
    import pandas as pd
except ImportError as e:
    print(f"错误: 缺少必要的依赖包: {e}")
    print("请运行: pip install requests aiohttp psutil matplotlib pandas")
    sys.exit(1)


@dataclass
class TestResult:
    """测试结果数据类"""
    timestamp: float
    response_time: float
    status_code: int
    success: bool
    error_message: Optional[str] = None
    request_size: int = 0
    response_size: int = 0


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p90_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    total_duration: float
    avg_cpu_usage: float
    avg_memory_usage: float
    peak_memory_usage: float


class SystemMonitor:
    """系统资源监控器"""
    
    def __init__(self):
        self.cpu_samples = []
        self.memory_samples = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self, interval: float = 1.0):
        """开始监控系统资源"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,)
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_info = psutil.virtual_memory()
                
                self.cpu_samples.append(cpu_percent)
                self.memory_samples.append(memory_info.percent)
                
                time.sleep(interval)
            except Exception as e:
                print(f"监控错误: {e}")
                break
    
    def get_metrics(self) -> Dict[str, float]:
        """获取监控指标"""
        if not self.cpu_samples or not self.memory_samples:
            return {
                'avg_cpu': 0.0,
                'avg_memory': 0.0,
                'peak_memory': 0.0
            }
        
        return {
            'avg_cpu': statistics.mean(self.cpu_samples),
            'avg_memory': statistics.mean(self.memory_samples),
            'peak_memory': max(self.memory_samples)
        }


class APIPerformanceTester:
    """API性能测试器"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        # 设置请求头
        if api_key:
            self.session.headers.update({'X-API-Key': api_key})
        
        self.session.headers.update({
            'User-Agent': 'API-Performance-Tester/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        self.results: List[TestResult] = []
        self.monitor = SystemMonitor()
    
    def test_endpoint(self, endpoint: str, method: str = 'GET', 
                     payload: Optional[Dict] = None, timeout: float = 30.0) -> TestResult:
        """测试单个端点"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=payload, timeout=timeout)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=payload, timeout=timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, timeout=timeout)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # 计算请求和响应大小
            request_size = len(json.dumps(payload).encode()) if payload else 0
            response_size = len(response.content)
            
            return TestResult(
                timestamp=start_time,
                response_time=response_time,
                status_code=response.status_code,
                success=200 <= response.status_code < 300,
                request_size=request_size,
                response_size=response_size
            )
            
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            
            return TestResult(
                timestamp=start_time,
                response_time=response_time,
                status_code=0,
                success=False,
                error_message=str(e)
            )
    
    def response_time_test(self, endpoint: str, iterations: int = 100) -> List[TestResult]:
        """响应时间测试"""
        print(f"\n🕐 响应时间测试: {endpoint} ({iterations}次请求)")
        
        results = []
        for i in range(iterations):
            result = self.test_endpoint(endpoint)
            results.append(result)
            
            if (i + 1) % 10 == 0:
                print(f"  进度: {i + 1}/{iterations}")
        
        return results
    
    def concurrent_test(self, endpoint: str, concurrent_users: int = 10, 
                       requests_per_user: int = 10) -> List[TestResult]:
        """并发测试"""
        print(f"\n🚀 并发测试: {endpoint} ({concurrent_users}个并发用户, 每用户{requests_per_user}次请求)")
        
        results = []
        
        def user_requests():
            user_results = []
            for _ in range(requests_per_user):
                result = self.test_endpoint(endpoint)
                user_results.append(result)
            return user_results
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_requests) for _ in range(concurrent_users)]
            
            for i, future in enumerate(as_completed(futures)):
                user_results = future.result()
                results.extend(user_results)
                print(f"  用户 {i + 1}/{concurrent_users} 完成")
        
        return results
    
    def load_test(self, endpoint: str, duration: int = 60, 
                 target_rps: int = 10) -> List[TestResult]:
        """负载测试"""
        print(f"\n📊 负载测试: {endpoint} (持续{duration}秒, 目标{target_rps} RPS)")
        
        results = []
        start_time = time.time()
        request_interval = 1.0 / target_rps
        
        self.monitor.start_monitoring()
        
        try:
            while time.time() - start_time < duration:
                request_start = time.time()
                
                result = self.test_endpoint(endpoint)
                results.append(result)
                
                # 控制请求频率
                elapsed = time.time() - request_start
                sleep_time = max(0, request_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                # 每10秒报告一次进度
                if len(results) % (target_rps * 10) == 0:
                    elapsed_time = time.time() - start_time
                    current_rps = len(results) / elapsed_time
                    print(f"  进度: {elapsed_time:.0f}s, 当前RPS: {current_rps:.1f}")
        
        finally:
            self.monitor.stop_monitoring()
        
        return results
    
    def stress_test(self, endpoint: str, max_concurrent: int = 100, 
                   step: int = 10, duration_per_step: int = 30) -> Dict[int, List[TestResult]]:
        """压力测试"""
        print(f"\n💥 压力测试: {endpoint} (最大{max_concurrent}并发, 步长{step}, 每步{duration_per_step}秒)")
        
        stress_results = {}
        
        for concurrent in range(step, max_concurrent + 1, step):
            print(f"\n  测试 {concurrent} 并发用户...")
            
            # 计算每个用户的请求数
            requests_per_user = max(1, duration_per_step // 2)
            
            results = self.concurrent_test(endpoint, concurrent, requests_per_user)
            stress_results[concurrent] = results
            
            # 计算当前步骤的成功率
            success_rate = sum(1 for r in results if r.success) / len(results) * 100
            avg_response_time = statistics.mean([r.response_time for r in results])
            
            print(f"    成功率: {success_rate:.1f}%, 平均响应时间: {avg_response_time:.3f}s")
            
            # 如果成功率低于50%，停止测试
            if success_rate < 50:
                print(f"    成功率过低，停止压力测试")
                break
            
            # 短暂休息
            time.sleep(2)
        
        return stress_results
    
    async def async_test(self, endpoint: str, concurrent: int = 10, 
                        total_requests: int = 100) -> List[TestResult]:
        """异步测试"""
        print(f"\n⚡ 异步测试: {endpoint} ({concurrent}并发, {total_requests}总请求)")
        
        url = f"{self.base_url}{endpoint}"
        results = []
        
        async def make_request(session, semaphore):
            async with semaphore:
                start_time = time.time()
                try:
                    headers = {}
                    if self.api_key:
                        headers['X-API-Key'] = self.api_key
                    
                    async with session.get(url, headers=headers, timeout=30) as response:
                        await response.read()  # 确保完全读取响应
                        end_time = time.time()
                        
                        return TestResult(
                            timestamp=start_time,
                            response_time=end_time - start_time,
                            status_code=response.status,
                            success=200 <= response.status < 300
                        )
                except Exception as e:
                    end_time = time.time()
                    return TestResult(
                        timestamp=start_time,
                        response_time=end_time - start_time,
                        status_code=0,
                        success=False,
                        error_message=str(e)
                    )
        
        semaphore = asyncio.Semaphore(concurrent)
        
        async with aiohttp.ClientSession() as session:
            tasks = [make_request(session, semaphore) for _ in range(total_requests)]
            results = await asyncio.gather(*tasks)
        
        return results
    
    def calculate_metrics(self, results: List[TestResult]) -> PerformanceMetrics:
        """计算性能指标"""
        if not results:
            return PerformanceMetrics(
                total_requests=0, successful_requests=0, failed_requests=0,
                avg_response_time=0, min_response_time=0, max_response_time=0,
                p50_response_time=0, p90_response_time=0, p95_response_time=0, p99_response_time=0,
                requests_per_second=0, error_rate=0, total_duration=0,
                avg_cpu_usage=0, avg_memory_usage=0, peak_memory_usage=0
            )
        
        # 基本统计
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r.success)
        failed_requests = total_requests - successful_requests
        
        # 响应时间统计
        response_times = [r.response_time for r in results]
        avg_response_time = statistics.mean(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        
        # 百分位数
        sorted_times = sorted(response_times)
        p50_response_time = sorted_times[int(len(sorted_times) * 0.5)]
        p90_response_time = sorted_times[int(len(sorted_times) * 0.9)]
        p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]
        p99_response_time = sorted_times[int(len(sorted_times) * 0.99)]
        
        # 时间范围和RPS
        timestamps = [r.timestamp for r in results]
        total_duration = max(timestamps) - min(timestamps) if timestamps else 0
        requests_per_second = total_requests / total_duration if total_duration > 0 else 0
        
        # 错误率
        error_rate = failed_requests / total_requests * 100 if total_requests > 0 else 0
        
        # 系统资源指标
        system_metrics = self.monitor.get_metrics()
        
        return PerformanceMetrics(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p50_response_time=p50_response_time,
            p90_response_time=p90_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            total_duration=total_duration,
            avg_cpu_usage=system_metrics['avg_cpu'],
            avg_memory_usage=system_metrics['avg_memory'],
            peak_memory_usage=system_metrics['peak_memory']
        )
    
    def generate_report(self, test_results: Dict[str, Any], output_dir: str):
        """生成性能测试报告"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成JSON报告
        json_report = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'base_url': self.base_url,
                'tester_version': '1.0.0'
            },
            'results': test_results
        }
        
        with open(output_path / 'performance_report.json', 'w', encoding='utf-8') as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2, default=str)
        
        # 生成HTML报告
        self._generate_html_report(test_results, output_path)
        
        # 生成图表
        self._generate_charts(test_results, output_path)
        
        print(f"\n📊 性能报告已生成: {output_path.absolute()}")
    
    def _generate_html_report(self, test_results: Dict[str, Any], output_path: Path):
        """生成HTML报告"""
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API性能测试报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1, h2 { color: #333; }
        .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
        .metric-card { background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; }
        .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
        .metric-label { color: #666; font-size: 14px; }
        .chart-container { margin: 20px 0; text-align: center; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; font-weight: bold; }
        .success { color: #28a745; }
        .error { color: #dc3545; }
        .warning { color: #ffc107; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 API性能测试报告</h1>
        <p><strong>测试时间:</strong> {timestamp}</p>
        <p><strong>测试目标:</strong> {base_url}</p>
        
        {content}
    </div>
</body>
</html>
        """
        
        content_parts = []
        
        for test_name, data in test_results.items():
            if 'metrics' in data:
                metrics = data['metrics']
                
                content_parts.append(f"<h2>📊 {test_name}</h2>")
                
                # 关键指标卡片
                content_parts.append('<div class="metric-grid">')
                
                metric_cards = [
                    ('总请求数', metrics.total_requests, ''),
                    ('成功请求', metrics.successful_requests, 'success'),
                    ('失败请求', metrics.failed_requests, 'error' if metrics.failed_requests > 0 else ''),
                    ('平均响应时间', f"{metrics.avg_response_time:.3f}s", ''),
                    ('P95响应时间', f"{metrics.p95_response_time:.3f}s", ''),
                    ('RPS', f"{metrics.requests_per_second:.1f}", ''),
                    ('错误率', f"{metrics.error_rate:.1f}%", 'error' if metrics.error_rate > 5 else ''),
                    ('CPU使用率', f"{metrics.avg_cpu_usage:.1f}%", '')
                ]
                
                for label, value, css_class in metric_cards:
                    content_parts.append(f'''
                    <div class="metric-card">
                        <div class="metric-value {css_class}">{value}</div>
                        <div class="metric-label">{label}</div>
                    </div>
                    ''')
                
                content_parts.append('</div>')
                
                # 详细指标表格
                content_parts.append('''
                <table>
                    <tr><th>指标</th><th>值</th></tr>
                ''')
                
                detailed_metrics = [
                    ('最小响应时间', f"{metrics.min_response_time:.3f}s"),
                    ('最大响应时间', f"{metrics.max_response_time:.3f}s"),
                    ('P50响应时间', f"{metrics.p50_response_time:.3f}s"),
                    ('P90响应时间', f"{metrics.p90_response_time:.3f}s"),
                    ('P99响应时间', f"{metrics.p99_response_time:.3f}s"),
                    ('测试持续时间', f"{metrics.total_duration:.1f}s"),
                    ('平均内存使用', f"{metrics.avg_memory_usage:.1f}%"),
                    ('峰值内存使用', f"{metrics.peak_memory_usage:.1f}%")
                ]
                
                for label, value in detailed_metrics:
                    content_parts.append(f'<tr><td>{label}</td><td>{value}</td></tr>')
                
                content_parts.append('</table>')
        
        html_content = html_template.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            base_url=self.base_url,
            content=''.join(content_parts)
        )
        
        with open(output_path / 'performance_report.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _generate_charts(self, test_results: Dict[str, Any], output_path: Path):
        """生成性能图表"""
        try:
            # 响应时间分布图
            plt.figure(figsize=(12, 8))
            
            for i, (test_name, data) in enumerate(test_results.items()):
                if 'results' in data:
                    response_times = [r.response_time for r in data['results']]
                    plt.subplot(2, 2, i + 1)
                    plt.hist(response_times, bins=50, alpha=0.7, edgecolor='black')
                    plt.title(f'{test_name} - 响应时间分布')
                    plt.xlabel('响应时间 (秒)')
                    plt.ylabel('频次')
                    plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_path / 'response_time_distribution.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # 时间序列图
            plt.figure(figsize=(15, 6))
            
            for test_name, data in test_results.items():
                if 'results' in data:
                    results = data['results']
                    timestamps = [(r.timestamp - results[0].timestamp) for r in results]
                    response_times = [r.response_time for r in results]
                    
                    plt.plot(timestamps, response_times, label=test_name, alpha=0.7)
            
            plt.title('响应时间时间序列')
            plt.xlabel('时间 (秒)')
            plt.ylabel('响应时间 (秒)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig(output_path / 'response_time_series.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            print("✓ 性能图表已生成")
            
        except Exception as e:
            print(f"⚠ 生成图表时出错: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="API性能测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--url",
        default="http://202.200.206.248:8000",
        help="API基础URL (默认: http://202.200.206.248:8000)"
    )
    
    parser.add_argument(
        "--api-key",
        help="API密钥"
    )
    
    parser.add_argument(
        "--endpoint",
        default="/health",
        help="测试端点 (默认: /health)"
    )
    
    parser.add_argument(
        "--test-type",
        choices=["response", "concurrent", "load", "stress", "async", "all"],
        default="all",
        help="测试类型 (默认: all)"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="负载测试持续时间(秒) (默认: 60)"
    )
    
    parser.add_argument(
        "--concurrent",
        type=int,
        default=10,
        help="并发用户数 (默认: 10)"
    )
    
    parser.add_argument(
        "--rps",
        type=int,
        default=10,
        help="目标每秒请求数 (默认: 10)"
    )
    
    parser.add_argument(
        "--output",
        default="reports/performance",
        help="报告输出目录 (默认: reports/performance)"
    )
    
    args = parser.parse_args()
    
    print("🚀 API性能测试工具")
    print("=" * 50)
    print(f"目标URL: {args.url}")
    print(f"测试端点: {args.endpoint}")
    print(f"测试类型: {args.test_type}")
    
    # 创建测试器
    tester = APIPerformanceTester(args.url, args.api_key)
    
    # 检查API可用性
    print("\n🔍 检查API可用性...")
    health_result = tester.test_endpoint('/health')
    if not health_result.success:
        print(f"❌ API不可用: {health_result.error_message}")
        return 1
    
    print(f"✅ API可用 (响应时间: {health_result.response_time:.3f}s)")
    
    # 执行测试
    test_results = {}
    
    if args.test_type in ["response", "all"]:
        results = tester.response_time_test(args.endpoint, 100)
        metrics = tester.calculate_metrics(results)
        test_results["响应时间测试"] = {"results": results, "metrics": metrics}
    
    if args.test_type in ["concurrent", "all"]:
        results = tester.concurrent_test(args.endpoint, args.concurrent, 10)
        metrics = tester.calculate_metrics(results)
        test_results["并发测试"] = {"results": results, "metrics": metrics}
    
    if args.test_type in ["load", "all"]:
        results = tester.load_test(args.endpoint, args.duration, args.rps)
        metrics = tester.calculate_metrics(results)
        test_results["负载测试"] = {"results": results, "metrics": metrics}
    
    if args.test_type in ["stress", "all"]:
        stress_results = tester.stress_test(args.endpoint, args.concurrent * 2, 5, 20)
        # 合并所有压力测试结果
        all_stress_results = []
        for concurrent_level, results in stress_results.items():
            all_stress_results.extend(results)
        
        if all_stress_results:
            metrics = tester.calculate_metrics(all_stress_results)
            test_results["压力测试"] = {"results": all_stress_results, "metrics": metrics}
    
    if args.test_type in ["async", "all"]:
        print("\n⚡ 运行异步测试...")
        async_results = asyncio.run(tester.async_test(args.endpoint, args.concurrent, 100))
        metrics = tester.calculate_metrics(async_results)
        test_results["异步测试"] = {"results": async_results, "metrics": metrics}
    
    # 生成报告
    print("\n📊 生成性能报告...")
    tester.generate_report(test_results, args.output)
    
    # 输出摘要
    print("\n📈 测试摘要:")
    print("=" * 30)
    
    for test_name, data in test_results.items():
        if 'metrics' in data:
            metrics = data['metrics']
            print(f"\n{test_name}:")
            print(f"  总请求: {metrics.total_requests}")
            print(f"  成功率: {(metrics.successful_requests/metrics.total_requests*100):.1f}%")
            print(f"  平均响应时间: {metrics.avg_response_time:.3f}s")
            print(f"  P95响应时间: {metrics.p95_response_time:.3f}s")
            print(f"  RPS: {metrics.requests_per_second:.1f}")
    
    print("\n✅ 性能测试完成!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
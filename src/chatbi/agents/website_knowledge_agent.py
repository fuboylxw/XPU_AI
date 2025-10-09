#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网站知识库构建Agent
用于爬取指定网站的所有信息并将其整理成知识库便于检索的文本文件
"""

import os
import re
import time
import logging
import argparse
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin

# 网络爬虫相关导入
import requests
from bs4 import BeautifulSoup

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class WebsiteKnowledgeAgent:
    """网站知识库构建Agent"""
    
    def __init__(self, base_url: str, output_dir: str = "knowledge_base", 
                 max_pages: int = 100, delay: float = 1.0):
        """
        初始化网站知识库构建Agent
        
        Args:
            base_url: 要爬取的网站基础URL
            output_dir: 知识库输出目录
            max_pages: 最大爬取页面数
            delay: 爬取延迟(秒)，避免请求过快
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.max_pages = max_pages
        self.delay = delay
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 初始化已访问URL集合和待访问URL队列
        self.visited_urls = set()
        self.url_queue = [base_url]
        
        # 初始化文档存储
        self.documents = []
        
        logger.info(f"初始化网站知识库构建Agent，目标网站: {base_url}")
    
    def extract_links(self, url: str, html_content: str) -> List[str]:
        """
        从HTML内容中提取链接
        
        Args:
            url: 当前页面URL
            html_content: HTML内容
            
        Returns:
            链接列表
        """
        soup = BeautifulSoup(html_content, 'html.parser', from_encoding='utf-8')
        base_domain = urlparse(self.base_url).netloc
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # 处理相对URL
            full_url = urljoin(url, href)
            # 只保留同一域名下的URL
            if urlparse(full_url).netloc == base_domain:
                links.append(full_url)
        
        return list(set(links))  # 去重
    
    def clean_text(self, text: str) -> str:
        """
        清理文本内容
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        # 移除多余空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符，但保留中文字符
        text = re.sub(r'[^\w\s.,?!:;()\[\]{}\-"\'""''，。？！：；（）【】{}]', '', text)
        return text.strip()
        
    def format_content(self, text: str, category: str = None) -> str:
        """
        格式化内容，提高可读性
        
        Args:
            text: 原始文本
            category: 内容类别
            
        Returns:
            格式化后的文本
        """
        # 清理文本
        text = self.clean_text(text)
        
        # 根据类别应用不同的格式化规则
        if category == "学校概况":
            # 为段落添加缩进
            lines = text.split('\n')
            formatted_lines = ["    " + line if line.strip() else line for line in lines]
            text = '\n'.join(formatted_lines)
        elif category == "新闻动态" or category == "通知公告":
            # 为新闻和通知添加时间标记（如果有）
            date_pattern = r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)'
            date_match = re.search(date_pattern, text)
            if date_match:
                date_str = date_match.group(1)
                # 将日期移到内容开头
                if date_str not in text[:20]:
                    text = f"[{date_str}] {text}"
        
        # 添加适当的分隔符
        if len(text) > 100:  # 只对较长的文本添加分隔符
            paragraphs = text.split('\n\n')
            if len(paragraphs) > 1:
                text = '\n\n'.join(paragraphs)
            else:
                # 尝试按句子分段
                sentences = re.split(r'([.。!！?？]\s*)', text)
                if len(sentences) > 2:
                    new_text = ""
                    for i in range(0, len(sentences), 2):
                        if i+1 < len(sentences):
                            new_text += sentences[i] + sentences[i+1]
                            if i+2 < len(sentences):
                                new_text += "\n"
                    text = new_text
        
        return text
    
    def extract_content(self, url: str, html_content: str) -> Dict[str, Any]:
        """
        从HTML内容中提取有用信息并按类别分类
        
        Args:
            url: 当前页面URL
            html_content: HTML内容
            
        Returns:
            包含提取信息的字典，按类别组织
        """
        soup = BeautifulSoup(html_content, 'html.parser', from_encoding='utf-8')
        
        # 移除脚本和样式元素
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
        
        # 提取标题
        title = soup.title.string if soup.title else "无标题"
        
        # 初始化分类内容字典
        categorized_content = {
            "学校概况": [],
            "新闻动态": [],
            "教学科研": [],
            "招生就业": [],
            "校园生活": [],
            "通知公告": [],
            "其他信息": []
        }
        
        # 提取新闻和通知
        news_elements = soup.find_all(['div', 'section', 'article'], class_=lambda c: c and ('news' in c.lower() or 'notice' in c.lower() or '新闻' in c or '通知' in c))
        for element in news_elements:
            text = element.get_text(strip=True)
            if '通知' in text or '公告' in text:
                categorized_content["通知公告"].append(text)
            elif '新闻' in text or '动态' in text:
                categorized_content["新闻动态"].append(text)
        
        # 提取学校概况
        about_elements = soup.find_all(['div', 'section', 'article'], class_=lambda c: c and ('about' in c.lower() or '学校' in c or '概况' in c or '简介' in c))
        for element in about_elements:
            categorized_content["学校概况"].append(element.get_text(strip=True))
        
        # 提取教学科研
        academic_elements = soup.find_all(['div', 'section', 'article'], class_=lambda c: c and ('academic' in c.lower() or '教学' in c or '科研' in c or '学术' in c))
        for element in academic_elements:
            categorized_content["教学科研"].append(element.get_text(strip=True))
        
        # 提取招生就业
        admission_elements = soup.find_all(['div', 'section', 'article'], class_=lambda c: c and ('admission' in c.lower() or '招生' in c or '就业' in c))
        for element in admission_elements:
            categorized_content["招生就业"].append(element.get_text(strip=True))
        
        # 提取校园生活
        campus_elements = soup.find_all(['div', 'section', 'article'], class_=lambda c: c and ('campus' in c.lower() or '校园' in c or '生活' in c or '活动' in c))
        for element in campus_elements:
            categorized_content["校园生活"].append(element.get_text(strip=True))
        
        # 尝试通过标题和内容关键词进行分类
        main_elements = soup.find_all(['div', 'section', 'article', 'p', 'h1', 'h2', 'h3', 'h4', 'h5'])
        for element in main_elements:
            text = element.get_text(strip=True)
            if not text:
                continue
                
            # 根据关键词分类
            if any(keyword in text for keyword in ['学校简介', '历史沿革', '学校概况']):
                categorized_content["学校概况"].append(text)
            elif any(keyword in text for keyword in ['新闻', '动态', '要闻', '头条']):
                categorized_content["新闻动态"].append(text)
            elif any(keyword in text for keyword in ['教学', '科研', '学术', '实验室', '学院', '专业']):
                categorized_content["教学科研"].append(text)
            elif any(keyword in text for keyword in ['招生', '就业', '考研', '考博', '录取']):
                categorized_content["招生就业"].append(text)
            elif any(keyword in text for keyword in ['校园', '学生', '社团', '活动', '文化', '生活']):
                categorized_content["校园生活"].append(text)
            elif any(keyword in text for keyword in ['通知', '公告', '通告', '提醒']):
                categorized_content["通知公告"].append(text)
            else:
                # 如果没有匹配到任何类别，放入其他信息
                categorized_content["其他信息"].append(text)
        
        # 清理、格式化和去重每个类别的内容
        for category in categorized_content:
            # 去除重复内容
            unique_content = []
            for item in categorized_content[category]:
                # 使用新的格式化功能
                formatted_item = self.format_content(item, category)
                if formatted_item and formatted_item not in unique_content:
                    unique_content.append(formatted_item)
            categorized_content[category] = unique_content
        
        # 确保所有内容都是UTF-8编码
        for category in categorized_content:
            for i, content in enumerate(categorized_content[category]):
                if isinstance(content, bytes):
                    categorized_content[category][i] = content.decode('utf-8', errors='replace')
        
        return {
            "url": url,
            "title": title,
            "categorized_content": categorized_content,
            "metadata": {
                "source": url,
                "title": title
            }
        }
    
    def crawl_website(self) -> List[Dict]:
        """
        爬取网站内容
        
        Returns:
            文档列表
        """
        logger.info(f"开始爬取网站: {self.base_url}")
        
        page_count = 0
        
        while self.url_queue and page_count < self.max_pages:
            # 获取下一个URL
            current_url = self.url_queue.pop(0)
            
            # 如果已经访问过，跳过
            if current_url in self.visited_urls:
                continue
            
            logger.info(f"爬取页面 ({page_count+1}/{self.max_pages}): {current_url}")
            
            try:
                # 使用requests获取页面内容
                response = requests.get(current_url, timeout=10)
                response.raise_for_status()
                
                # 确保正确的编码处理
                if response.encoding == 'ISO-8859-1':
                    response.encoding = 'utf-8'
                
                # 标记为已访问
                self.visited_urls.add(current_url)
                page_count += 1
                
                # 提取内容
                page_data = self.extract_content(current_url, response.text)
                
                # 添加到文档列表
                self.documents.append(page_data)
                
                # 提取链接并添加到队列
                new_links = self.extract_links(current_url, response.text)
                for link in new_links:
                    if link not in self.visited_urls and link not in self.url_queue:
                        self.url_queue.append(link)
                
                # 延迟，避免请求过快
                time.sleep(self.delay)
                
            except Exception as e:
                logger.error(f"爬取页面 {current_url} 时出错: {str(e)}")
        
        logger.info(f"网站爬取完成，共爬取 {page_count} 个页面")
        return self.documents
    
    def save_to_text_files(self) -> None:
        """
        将文档保存为文本文件，按信息类别整理
        """
        logger.info(f"开始保存文档到文本文件，输出目录: {self.output_dir}")
        
        # 创建索引文件，使用UTF-8-SIG编码确保中文正确显示
        index_file_path = os.path.join(self.output_dir, "index.txt")
        with open(index_file_path, "w", encoding="utf-8-sig") as index_file:
            index_file.write(f"网站知识库索引\n")
            index_file.write(f"基础URL: {self.base_url}\n")
            index_file.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 按URL分组保存文档
            url_to_docs = {}
            for doc in self.documents:
                url = doc["metadata"]["source"]
                if url not in url_to_docs:
                    url_to_docs[url] = []
                url_to_docs[url].append(doc)
            
            # 为每个URL创建一个文件
            for i, (url, docs) in enumerate(url_to_docs.items()):
                # 创建安全的文件名
                safe_filename = f"page_{i+1}.txt"
                file_path = os.path.join(self.output_dir, safe_filename)
                
                # 写入文档内容，确保使用UTF-8编码且不带BOM
                with open(file_path, "w", encoding="utf-8-sig") as f:
                    title = docs[0]["metadata"]["title"]
                    f.write(f"标题: {title}\n")
                    f.write(f"URL: {url}\n")
                    f.write("-" * 80 + "\n\n")
                    
                    # 按类别组织内容
                    for doc in docs:
                        if "categorized_content" in doc:
                            # 遍历每个类别
                            for category, contents in doc["categorized_content"].items():
                                if contents:  # 只有当该类别有内容时才显示
                                    f.write(f"## {category}\n")
                                    f.write("-" * 50 + "\n\n")
                                    
                                    # 写入该类别的所有内容
                                    for content in contents:
                                        f.write(f"{content}\n\n")
                                    
                                    f.write("\n")
                        else:
                            # 兼容旧版本，如果没有分类内容，则直接写入
                            if "content" in doc:
                                f.write(doc["content"])
                                f.write("\n\n" + "-" * 40 + "\n\n")
                
                # 添加到索引
                index_file.write(f"{i+1}. {title}\n")
                index_file.write(f"   文件: {safe_filename}\n")
                index_file.write(f"   URL: {url}\n")
                
                # 添加类别信息到索引
                if docs and "categorized_content" in docs[0]:
                    categories = []
                    for category, contents in docs[0]["categorized_content"].items():
                        if contents:  # 只有当该类别有内容时才显示
                            categories.append(category)
                    
                    if categories:
                        index_file.write(f"   包含类别: {', '.join(categories)}\n")
                
                index_file.write("\n")
        
        logger.info(f"文档保存完成，索引文件: {index_file_path}")
    
    def run(self) -> None:
        """
        运行网站知识库构建流程
        """
        logger.info("开始运行网站知识库构建流程")
        
        # 1. 爬取网站
        self.crawl_website()
        
        # 2. 保存为文本文件
        self.save_to_text_files()
        
        logger.info("网站知识库构建流程完成")


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description="网站知识库构建工具")
    parser.add_argument("url", help="要爬取的网站URL")
    parser.add_argument("--output", "-o", default="knowledge_base", 
                        help="知识库输出目录")
    parser.add_argument("--max-pages", "-m", type=int, default=100, 
                        help="最大爬取页面数")
    parser.add_argument("--delay", "-d", type=float, default=1.0, 
                        help="爬取延迟(秒)")
    
    args = parser.parse_args()
    
    # 创建并运行Agent
    agent = WebsiteKnowledgeAgent(
        base_url=args.url,
        output_dir=args.output,
        max_pages=args.max_pages,
        delay=args.delay
    )
    agent.run()


if __name__ == "__main__":
    main()
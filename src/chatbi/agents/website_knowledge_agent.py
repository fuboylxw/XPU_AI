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
                 max_pages: int = 100, delay: float = 1.0, use_llm: bool = True):
        """
        初始化网站知识库构建Agent
        
        Args:
            base_url: 要爬取的网站基础URL
            output_dir: 知识库输出目录
            max_pages: 最大爬取页面数
            delay: 爬取延迟(秒)，避免请求过快
            use_llm: 是否使用大模型进行内容分类
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.max_pages = max_pages
        self.delay = delay
        self.use_llm = use_llm
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 初始化已访问URL集合和待访问URL队列
        self.visited_urls = set()
        self.url_queue = [base_url]
        
        # 初始化文档存储
        self.documents = []
        
        # 定义知识库类别（与knowledge_query_agent.py中保持一致）
        self.knowledge_categories = {
            "学校概况": {
                "description": "西安工程大学基本信息、历史沿革、办学特色",
                "keywords": ["学校介绍", "历史", "概况", "特色", "校训"],
                "priority": 1
            },
            "学院专业": {
                "description": "各学院介绍、专业设置、培养方案",
                "keywords": ["学院", "专业", "培养方案", "课程设置"],
                "priority": 2
            },
            "招生信息": {
                "description": "招生政策、录取分数线、报考指南",
                "keywords": ["招生", "录取", "分数线", "报考", "入学"],
                "priority": 2
            },
            "教务管理": {
                "description": "课程安排、选课指南、考试制度、成绩管理",
                "keywords": ["课程", "选课", "考试", "成绩", "学分"],
                "priority": 3
            },
            "学生事务": {
                "description": "学籍管理、奖助学金、评优评奖、处分规定",
                "keywords": ["学籍", "奖学金", "助学金", "评优", "处分"],
                "priority": 3
            },
            "校园生活": {
                "description": "宿舍管理、饮食服务、校园卡、网络服务",
                "keywords": ["宿舍", "饮食", "校园卡", "网络", "生活"],
                "priority": 4
            },
            "规章制度": {
                "description": "校规校纪、管理办法、各类制度文件",
                "keywords": ["校规", "制度", "办法", "规定", "文件"],
                "priority": 3
            },
            "就业指导": {
                "description": "就业政策、实习安排、职业规划、招聘信息",
                "keywords": ["就业", "实习", "职业", "招聘", "工作"],
                "priority": 4
            }
        }
        
        # 尝试导入大模型支持
        if self.use_llm:
            try:
                import openai
                from dotenv import load_dotenv
                load_dotenv()
                self.openai_api_key = os.getenv("OPENAI_API_KEY")
                if self.openai_api_key:
                    openai.api_key = self.openai_api_key
                    self.llm_available = True
                    logger.info("大模型分类功能已启用")
                else:
                    self.llm_available = False
                    logger.warning("未找到OpenAI API密钥，大模型分类功能将被禁用")
            except ImportError:
                self.llm_available = False
                logger.warning("未安装openai或dotenv库，大模型分类功能将被禁用")
        else:
            self.llm_available = False
        
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
    
    def classify_with_llm(self, text: str) -> str:
        """
        使用大模型对文本进行分类
        
        Args:
            text: 要分类的文本
            
        Returns:
            分类结果（类别名称）
        """
        if not self.llm_available:
            return "其他信息"
            
        try:
            import openai
            
            # 构建提示词
            prompt = f"""请将以下文本分类到最合适的一个类别中。类别及其描述如下：

{chr(10).join([f"- {category}: {details['description']}" for category, details in self.knowledge_categories.items()])}

文本内容：
{text[:1000]}  # 限制长度，避免token过多

请只返回一个最匹配的类别名称，不要有任何其他解释。
"""
            
            # 调用API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个专业的文本分类助手，擅长将文本精确分类到预定义的类别中。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 低温度，提高确定性
                max_tokens=20     # 只需要返回类别名称
            )
            
            # 提取结果
            result = response.choices[0].message.content.strip()
            
            # 确保结果是有效的类别
            for category in self.knowledge_categories.keys():
                if category in result:
                    return category
                    
            # 如果没有匹配到任何类别，返回其他信息
            return "其他信息"
            
        except Exception as e:
            logger.error(f"使用大模型分类时出错: {str(e)}")
            return "其他信息"
    
    def classify_text(self, text: str) -> str:
        """
        对文本进行分类，结合关键词和大模型方法
        
        Args:
            text: 要分类的文本
            
        Returns:
            分类结果（类别名称）
        """
        # 计算每个类别的匹配分数
        category_scores = {}
        
        # 首先尝试使用关键词匹配
        for category, details in self.knowledge_categories.items():
            keywords = details.get("keywords", [])
            # 计算匹配的关键词数量
            score = sum(1 for keyword in keywords if keyword in text)
            category_scores[category] = score
        
        # 找出得分最高的类别
        max_score = max(category_scores.values()) if category_scores else 0
        
        # 如果有明确的最高分类别且分数大于0，直接返回
        if max_score > 0:
            max_categories = [cat for cat, score in category_scores.items() if score == max_score]
            if len(max_categories) == 1:
                return max_categories[0]
        
        # 如果关键词匹配不明确，尝试使用大模型
        if self.llm_available and self.use_llm:
            llm_category = self.classify_with_llm(text)
            if llm_category != "其他信息":
                return llm_category
        
        # 如果以上方法都不明确，使用更详细的启发式规则
        # 学校概况
        if '学校' in text or '校史' in text or '历史' in text or '概况' in text or '简介' in text or '校训' in text:
            return "学校概况"
        # 学院专业
        elif '学院' in text or '专业' in text or '系' in text or '培养' in text or '课程设置' in text:
            return "学院专业"
        # 招生信息
        elif '招生' in text or '录取' in text or '报考' in text or '分数线' in text or '入学' in text:
            return "招生信息"
        # 教务管理
        elif '课程' in text or '教务' in text or '考试' in text or '选课' in text or '学分' in text:
            return "教务管理"
        # 学生事务
        elif '学生' in text or '奖学金' in text or '助学金' in text or '学籍' in text or '评优' in text:
            return "学生事务"
        # 校园生活
        elif '宿舍' in text or '食堂' in text or '校园卡' in text or '生活' in text or '网络' in text:
            return "校园生活"
        # 规章制度
        elif '规章' in text or '制度' in text or '办法' in text or '规定' in text or '文件' in text:
            return "规章制度"
        # 就业指导
        elif '就业' in text or '实习' in text or '职业' in text or '招聘' in text or '工作' in text:
            return "就业指导"
        # 新闻动态
        elif '新闻' in text or '动态' in text or '通知' in text or '公告' in text or '活动' in text:
            return "新闻动态"
        # 默认分类
        else:
            return "其他信息"

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
        
        # 初始化分类内容字典，使用knowledge_categories中的类别
        categorized_content = {category: [] for category in self.knowledge_categories.keys()}
        categorized_content["其他信息"] = []  # 添加一个其他信息类别
        
        # 提取主要内容区域
        main_content = ""
        main_elements = soup.find_all(['div', 'section', 'article'], 
                                     class_=lambda c: c and ('content' in c.lower() or 'main' in c.lower()))
        if main_elements:
            for element in main_elements:
                main_content += element.get_text(strip=True) + "\n\n"
        
        # 如果找不到主要内容区域，则提取所有可能的内容
        if not main_content:
            # 提取所有可能包含有用信息的元素
            content_elements = soup.find_all(['div', 'section', 'article', 'p', 'h1', 'h2', 'h3', 'h4', 'h5'])
            for element in content_elements:
                text = element.get_text(strip=True)
                if text and len(text) > 50:  # 只考虑有一定长度的文本
                    main_content += text + "\n\n"
        
        # 如果页面有明确的标题，将其添加到内容开头
        if title and title != "无标题":
            main_content = f"标题: {title}\n\n" + main_content
            
        # 如果提取到了内容，进行分类
        if main_content:
            # 对整个页面内容进行分类
            category = self.classify_text(main_content)
            categorized_content[category].append(main_content)
            
        # 尝试提取更细粒度的内容并分类
        sections = soup.find_all(['div', 'section', 'article'], class_=lambda c: c and len(c) > 5)
        for section in sections:
            text = section.get_text(strip=True)
            if text and len(text) > 100:  # 只考虑有一定长度的文本
                # 对每个部分进行单独分类
                category = self.classify_text(text)
                formatted_text = self.format_content(text, category)
                if formatted_text:
                    categorized_content[category].append(formatted_text)
        
        # 清理、格式化和去重每个类别的内容
        for category in categorized_content:
            # 去除重复内容
            unique_content = []
            for item in categorized_content[category]:
                # 使用格式化功能
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
        将文档保存为文本文件，按知识库类别整理
        """
        logger.info(f"开始保存文档到文本文件，输出目录: {self.output_dir}")
        
        # 创建索引文件，使用UTF-8-SIG编码确保中文正确显示
        index_file_path = os.path.join(self.output_dir, "index.txt")
        with open(index_file_path, "w", encoding="utf-8-sig") as index_file:
            index_file.write(f"西安工程大学知识库索引\n")
            index_file.write(f"基础URL: {self.base_url}\n")
            index_file.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 按类别整理内容
            category_contents = {category: [] for category in self.knowledge_categories.keys()}
            category_contents["其他信息"] = []
            
            # 收集所有文档中的内容，按类别组织
            for doc in self.documents:
                if "categorized_content" in doc:
                    for category, contents in doc["categorized_content"].items():
                        if contents:  # 只有当该类别有内容时才添加
                            # 为每个内容添加来源信息
                            for content in contents:
                                if content:
                                    source_info = f"来源: {doc['url']}\n"
                                    if "title" in doc:
                                        source_info += f"标题: {doc['title']}\n"
                                    category_contents[category].append(source_info + "\n" + content)
            
            # 为每个类别创建一个文件
            for category, contents in category_contents.items():
                if not contents:  # 跳过没有内容的类别
                    continue
                    
                # 创建安全的文件名
                safe_filename = f"{category}.txt"
                file_path = os.path.join(self.output_dir, safe_filename)
                
                # 写入文档内容，确保使用UTF-8编码且不带BOM
                with open(file_path, "w", encoding="utf-8-sig") as f:
                    f.write(f"# {category}\n\n")
                    
                    # 如果有类别描述，添加描述
                    if category in self.knowledge_categories:
                        f.write(f"描述: {self.knowledge_categories[category]['description']}\n\n")
                    
                    f.write("-" * 80 + "\n\n")
                    
                    # 写入该类别的所有内容
                    for i, content in enumerate(contents):
                        f.write(f"## 文档 {i+1}\n\n")
                        f.write(f"{content}\n\n")
                        f.write("-" * 50 + "\n\n")
                
                # 添加到索引
                index_file.write(f"{category}\n")
                index_file.write(f"   文件: {safe_filename}\n")
                index_file.write(f"   文档数量: {len(contents)}\n")
                
                # 如果有类别描述，添加描述
                if category in self.knowledge_categories:
                    index_file.write(f"   描述: {self.knowledge_categories[category]['description']}\n")
                
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
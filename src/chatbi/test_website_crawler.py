import os
import time
import re
import requests
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import sys
sys.path.append("d:\\pythonProject\\ChatAgent_XPU")
from src.chatbi.agents.website_knowledge_agent import WebsiteKnowledgeAgent

# 设置输出目录和基础URL
output_dir = "d:\\pythonProject\\ChatAgent_XPU\\src\\chatbi\\Knowledge"
base_url = "https://www.xpu.edu.cn/"

# 从knowledge_query_agent中获取分类定义
knowledge_categories = {
    "学校概况": {
        "description": "西安工程大学基本信息、历史沿革、办学特色",
        "keywords": ["学校介绍", "历史", "概况", "特色", "校训", "学校简介", "校史", "现任领导", "机构设置", "组织机构"],
        "priority": 1
    },
    "学院专业": {
        "description": "各学院介绍、专业设置、培养方案",
        "keywords": ["学院", "专业", "培养方案", "课程设置", "系部", "学科", "教学单位", "培养", "师资队伍"],
        "priority": 2
    },
    "招生信息": {
        "description": "招生政策、录取分数线、报考指南",
        "keywords": ["招生", "录取", "分数线", "报考", "入学", "考试", "招生简章", "研究生招生", "本科生招生"],
        "priority": 2
    },
    "教务管理": {
        "description": "课程安排、选课指南、考试制度、成绩管理",
        "keywords": ["课程", "选课", "考试", "成绩", "学分", "教务", "教学管理", "本科生教育", "研究生教育"],
        "priority": 3
    },
    "学生事务": {
        "description": "学籍管理、奖助学金、评优评奖、处分规定",
        "keywords": ["学籍", "奖学金", "助学金", "评优", "处分", "学生", "证书", "学生工作"],
        "priority": 3
    },
    "校园生活": {
        "description": "宿舍管理、饮食服务、校园卡、网络服务",
        "keywords": ["宿舍", "饮食", "校园卡", "网络", "生活", "食堂", "活动", "社团"],
        "priority": 4
    },
    "规章制度": {
        "description": "校规校纪、管理办法、各类制度文件",
        "keywords": ["校规", "制度", "办法", "规定", "文件", "规章", "条例"],
        "priority": 3
    },
    "就业指导": {
        "description": "就业政策、实习安排、职业规划、招聘信息",
        "keywords": ["就业", "实习", "职业", "招聘", "工作"],
        "priority": 4
    },
    "新闻动态": {
        "description": "学校新闻、通知公告、活动信息",
        "keywords": ["新闻", "动态", "通知", "公告", "活动", "讲座", "头条"],
        "priority": 5
    }
}

# 定义要移除的导航栏和页脚模式
nav_patterns = [
    r'网上办事大厅回到首页.*?国际交流',
    r'学校概况学校简介学校章程.*?国际交流',
    r'CopyRight ©西安工程大学.*?官方微博',
    r'联系我们：webmaster@xpu\.edu\.cn.*?官方微博',
    r'地址：.*?邮编：\d+',
    r'版权所有.*?西安工程大学',
    r'学校地图.*?联系我们'
]

# 设置请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# 初始化爬虫参数
max_pages = 100  # 增加爬取页面数量
max_depth = 3    # 设置最大爬取深度
delay_range = (0.5, 1.5)  # 随机延迟范围，避免被封

# 初始化URL队列，使用元组(url, depth)存储URL和深度
url_queue = [(base_url, 0)]
visited_urls = set()
crawled_count = 0
category_counts = {}
start_time = time.time()

# 子网站入口点，确保覆盖所有重要子网站
important_subdomains = [
    "https://www.xpu.edu.cn/xxgk.htm",  # 学校概况
    "https://www.xpu.edu.cn/xyjs.htm",  # 学院介绍
    "https://www.xpu.edu.cn/zsjy.htm",  # 招生就业
    "https://www.xpu.edu.cn/jyjx.htm",  # 教育教学
    "https://www.xpu.edu.cn/xkjs.htm",  # 学科建设
    "https://www.xpu.edu.cn/xsgz.htm",  # 学生工作
    "https://www.xpu.edu.cn/zsb/",      # 招生办
    "https://www.xpu.edu.cn/jwc/",      # 教务处
    "https://www.xpu.edu.cn/xsc/"       # 学生处
]

# 将重要子网站添加到队列
for subdomain in important_subdomains:
    if subdomain not in visited_urls:
        url_queue.append((subdomain, 0))

print(f"开始爬取网站: {base_url}")
print(f"最大爬取页面数: {max_pages}, 最大爬取深度: {max_depth}")

def classify_content(title, content):
    """使用knowledge_query_agent中的分类对内容进行分类"""
    text_to_classify = title + " " + content[:1000]  # 使用更多内容进行分类
    
    # 计算每个分类的匹配分数
    scores = {}
    for cat, info in knowledge_categories.items():
        score = 0
        # 标题匹配权重更高
        for keyword in info["keywords"]:
            if keyword in title:
                score += 3  # 标题中的关键词权重更高
            if keyword in content[:1000]:
                score += 1
        
        # 考虑优先级
        scores[cat] = score * (1 + 0.1 * (6 - info["priority"]))
    
    # 找出得分最高的分类
    max_score = 0
    best_category = "学校概况"  # 默认分类
    
    for cat, score in scores.items():
        if score > max_score:
            max_score = score
            best_category = cat
    
    # 如果没有明确的分类，使用更简单的规则
    if max_score == 0:
        if "招生" in text_to_classify:
            best_category = "招生信息"
        elif "新闻" in text_to_classify or "动态" in text_to_classify or "通知" in text_to_classify:
            best_category = "新闻动态"
        elif "学院" in text_to_classify or "专业" in text_to_classify:
            best_category = "学院专业"
        elif "就业" in text_to_classify or "实习" in text_to_classify:
            best_category = "就业指导"
        elif "学生" in text_to_classify:
            best_category = "学生事务"
        elif "规章" in text_to_classify or "制度" in text_to_classify:
            best_category = "规章制度"
        elif "校园" in text_to_classify or "生活" in text_to_classify:
            best_category = "校园生活"
        elif "教务" in text_to_classify or "课程" in text_to_classify:
            best_category = "教务管理"
        else:
            best_category = "学校概况"
    
    return best_category

def clean_text(text):
    """清理文本，移除导航栏、页脚和重复内容"""
    # 移除导航栏和页脚
    for pattern in nav_patterns:
        text = re.sub(pattern, '', text)
    
    # 移除多余空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 移除重复内容
    lines = text.split('\n')
    unique_lines = []
    seen = set()
    
    for line in lines:
        line = line.strip()
        # 只保留有意义的内容
        if line and len(line) > 10 and line not in seen:
            seen.add(line)
            unique_lines.append(line)
    
    return '\n\n'.join(unique_lines)

# 清理现有文件
for filename in os.listdir(output_dir):
    if filename.endswith(".txt") and filename != "index.txt":
        os.remove(os.path.join(output_dir, filename))

# 开始爬取
while url_queue and crawled_count < max_pages:
    current_url, depth = url_queue.pop(0)
    
    # 跳过已访问的URL
    if current_url in visited_urls:
        continue
    
    # 标记为已访问
    visited_urls.add(current_url)
    
    # 检查深度限制
    if depth > max_depth:
        continue
    
    try:
        # 获取页面内容
        response = requests.get(current_url, headers=headers, timeout=15)
        
        # 处理编码问题
        if response.encoding == 'ISO-8859-1':
            response.encoding = 'utf-8'
        
        html_content = response.text
        
        # 提取内容
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 清理标题
        title = soup.title.text if soup.title else "无标题"
        title = re.sub(r'[\r\n\t]+', ' ', title).strip()
        
        # 提取正文内容
        content = ""
        
        # 尝试找到主要内容区域
        main_content = soup.find('div', class_=lambda c: c and ('content' in c.lower() or 'article' in c.lower()))
        
        if main_content:
            # 如果找到主要内容区域，优先使用
            paragraphs = main_content.find_all(['p', 'div', 'article', 'section'])
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 30:  # 只保留较长的文本段落
                    content += text + "\n\n"
        else:
            # 否则使用所有内容元素
            content_elements = soup.find_all(['p', 'div', 'article', 'section'])
            for element in content_elements:
                text = element.get_text(strip=True)
                if len(text) > 50:  # 只保留较长的文本段落
                    content += text + "\n\n"
        
        # 清理内容
        content = clean_text(content)
        
        # 如果内容太少，可能是无效页面，跳过
        if len(content) < 100:
            print(f"跳过内容过少的页面: {current_url}")
            continue
        
        # 分类内容
        category = classify_content(title, content)
        
        # 更新分类计数
        category_counts[category] = category_counts.get(category, 0) + 1
        
        # 优化内容格式
        formatted_content = f"""
标题: {title}
URL: {current_url}
分类: {category}
爬取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}

内容:
{content}
"""
        
        # 保存内容
        category_file = os.path.join(output_dir, f"{category}.txt")
        with open(category_file, "a", encoding="utf-8") as f:
            f.write(formatted_content)
            f.write("\n" + "-"*80 + "\n\n")
        
        crawled_count += 1
        print(f"已爬取 ({crawled_count}/{max_pages}): {current_url} -> {category}")
        
        # 提取链接
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            full_url = urljoin(current_url, href)
            
            # 只处理同一域名下的URL
            parsed_url = urlparse(full_url)
            base_domain = urlparse(base_url).netloc
            
            if (parsed_url.netloc == base_domain and 
                full_url not in visited_urls and 
                full_url not in [u for u, _ in url_queue] and
                not full_url.endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.jpg', '.png', '.gif'))):
                url_queue.append((full_url, depth + 1))
        
        # 添加随机延迟，避免请求过快
        time.sleep(random.uniform(*delay_range))
        
    except Exception as e:
        print(f"爬取 {current_url} 时出错: {str(e)}")

# 创建索引文件
index_content = f"""西安工程大学知识库索引
爬取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
爬取页面总数: {crawled_count}
爬取用时: {(time.time() - start_time):.2f} 秒

各分类文档数量:
"""

for category, count in category_counts.items():
    index_content += f"- {category}: {count} 个文档\n"

index_file = os.path.join(output_dir, "index.txt")
with open(index_file, "w", encoding="utf-8") as f:
    f.write(index_content)

# 打印统计信息
elapsed_time = time.time() - start_time
print(f"\n爬取完成! 共爬取了 {crawled_count} 个页面，耗时 {elapsed_time:.2f} 秒")
print("各分类文档数量:")
for category, count in category_counts.items():
    print(f"- {category}: {count} 个文档")
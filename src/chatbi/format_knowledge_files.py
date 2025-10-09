import os
import re

# 知识文件目录
knowledge_dir = "d:\\pythonProject\\ChatAgent_XPU\\src\\chatbi\\Knowledge"

# 从knowledge_query_agent中获取的分类定义
knowledge_categories = {
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
    },
    "新闻动态": {
        "description": "学校新闻、通知公告、活动信息",
        "keywords": ["新闻", "动态", "通知", "公告", "活动"],
        "priority": 5
    }
}

def format_document(content):
    """格式化文档内容，提高可读性"""
    # 提取文档的各个部分
    title_match = re.search(r'标题:\s*(.*?)(?:\n|$)', content)
    url_match = re.search(r'URL:\s*(.*?)(?:\n|$)', content)
    category_match = re.search(r'分类:\s*(.*?)(?:\n|$)', content)
    time_match = re.search(r'爬取时间:\s*(.*?)(?:\n|$)', content)
    
    # 提取正文内容
    content_match = re.search(r'内容:\s*([\s\S]*?)(?=\n-{80}|\Z)', content)
    
    if not (title_match and content_match):
        return None  # 格式不符合预期
    
    title = title_match.group(1).strip()
    url = url_match.group(1).strip() if url_match else "未知URL"
    category = category_match.group(1).strip() if category_match else "未分类"
    crawl_time = time_match.group(1).strip() if time_match else "未知时间"
    doc_content = content_match.group(1).strip()
    
    # 清理内容，去除多余空行和空格
    doc_content = re.sub(r'\n{3,}', '\n\n', doc_content)
    doc_content = re.sub(r'\s+$', '', doc_content, flags=re.MULTILINE)
    
    # 格式化为更易读的格式
    formatted_doc = f"""{'='*80}
【标题】{title}
{'='*80}

【分类】{category}
【来源】{url}
【时间】{crawl_time}

【内容摘要】
{knowledge_categories.get(category, {}).get('description', '未知分类描述')}

【正文内容】
{doc_content}

{'-'*80}
"""
    return formatted_doc, category

def process_knowledge_files():
    """处理知识文件，优化格式和分类"""
    # 创建临时目录存放格式化后的文件
    temp_dir = os.path.join(knowledge_dir, "temp")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    # 处理每个分类文件
    for category in knowledge_categories.keys():
        category_file = os.path.join(knowledge_dir, f"{category}.txt")
        if not os.path.exists(category_file):
            continue
        
        # 读取原始文件内容
        with open(category_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 分割为单独的文档
        documents = content.split('\n' + '-'*80 + '\n')
        
        # 创建新的分类文件
        new_category_file = os.path.join(temp_dir, f"{category}.txt")
        with open(new_category_file, 'w', encoding='utf-8') as f:
            # 写入分类说明
            f.write(f"""{'#'*80}
# {category} - 知识库
{'#'*80}

【分类说明】
{knowledge_categories[category]['description']}

【关键词】
{', '.join(knowledge_categories[category]['keywords'])}

【优先级】
{knowledge_categories[category]['priority']}

{'#'*80}

""")
            
            # 处理每个文档
            doc_count = 0
            for doc in documents:
                if not doc.strip():
                    continue
                
                formatted_doc = format_document(doc)
                if formatted_doc:
                    doc_text, doc_category = formatted_doc
                    # 只写入属于当前分类的文档
                    if doc_category == category:
                        f.write(doc_text)
                        doc_count += 1
            
            # 写入文档计数
            f.write(f"\n总计: {doc_count} 个文档\n")
    
    # 创建索引文件
    create_index_file(temp_dir)
    
    # 替换原始文件
    for filename in os.listdir(temp_dir):
        src_file = os.path.join(temp_dir, filename)
        dst_file = os.path.join(knowledge_dir, filename)
        
        # 读取临时文件内容
        with open(src_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 写入到原始文件位置
        with open(dst_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    # 删除临时目录
    for filename in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, filename))
    os.rmdir(temp_dir)
    
    print("知识文件格式化完成！")

def create_index_file(directory):
    """创建索引文件"""
    index_content = """西安工程大学知识库索引
====================

本知识库包含以下分类的信息：
"""
    
    # 添加分类信息
    for category, info in sorted(knowledge_categories.items(), key=lambda x: x[1]['priority']):
        category_file = os.path.join(directory, f"{category}.txt")
        if os.path.exists(category_file):
            # 计算文档数量
            with open(category_file, 'r', encoding='utf-8') as f:
                content = f.read()
                doc_count = content.count('【标题】')
            
            index_content += f"\n{category}（优先级：{info['priority']}）：{doc_count} 个文档"
            index_content += f"\n  - {info['description']}"
            index_content += f"\n  - 关键词：{', '.join(info['keywords'])}"
    
    # 写入索引文件
    with open(os.path.join(directory, "index.txt"), 'w', encoding='utf-8') as f:
        f.write(index_content)

if __name__ == "__main__":
    process_knowledge_files()
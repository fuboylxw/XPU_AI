# ChatBI_XPU - 西安工程大学智能对话系统

ChatBI_XPU是一个基于大语言模型的智能对话系统，专为西安工程大学设计，能够回答关于学校的各类问题，进行数据分析，并提供智能对话服务。

## 功能特点

- **智能对话**：基于大语言模型的自然语言交互
- **知识库管理**：自动爬取学校网站信息，构建结构化知识库
- **数据分析**：支持自然语言查询数据，生成分析报告
- **Web搜索**：支持在线搜索补充信息
- **文档处理**：支持上传和处理各类文档（PDF、Word等）
- **流式输出**：支持大模型回答的流式输出，提升用户体验

## 项目结构

```
ChatBI_XPU/
├── config/                 # 配置文件
├── data/                   # 数据文件
├── logs/                   # 日志文件
├── models/                 # 模型文件
├── src/                    # 源代码
│   ├── chatbi/            # 核心模块
│   │   ├── agents/        # 智能代理
│   │   ├── Knowledge/     # 知识库管理
│   │   ├── prompts/       # 提示词模板
│   │   ├── tools/         # 工具函数
│   │   └── utils/         # 实用工具
│   └── main.py            # 主程序入口
├── static/                 # 静态资源
├── xpu_knowledge_base/    # 西安工程大学知识库
├── .env                    # 环境变量
├── .env.example           # 环境变量示例
├── chat_api.py            # 对话API服务
└── requirements.txt       # 项目依赖
```

## 安装与配置

1. 克隆项目
```bash
git clone https://github.com/yourusername/ChatBI_XPU.git
cd ChatBI_XPU
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，填入必要的API密钥和配置
```

## 使用方法

### 启动Web界面

```bash
python src/main.py
```
访问 http://localhost:8501 使用Streamlit界面

### 启动API服务

```bash
python chat_api.py
```
API文档: http://localhost:8003/docs

### 构建知识库

```bash
python src/chatbi/agents/website_knowledge_agent.py https://www.xpu.edu.cn/ --output xpu_knowledge_base --max-pages 30 --delay 1.0
```

## 主要功能模块

### 1. 网站知识库构建

自动爬取西安工程大学网站信息，并按类别整理保存，包括：
- 学校概况
- 新闻动态
- 教学科研
- 招生就业
- 校园生活
- 通知公告
- 其他信息

### 2. 智能对话系统

基于大语言模型的对话系统，能够：
- 回答关于学校的各类问题
- 进行数据分析和可视化
- 支持上下文理解和多轮对话

### 3. 文档处理

支持上传和处理各类文档：
- PDF文档
- Word文档
- Excel表格
- 文本文件

## 技术栈

- Python 3.9+
- FastAPI
- Streamlit
- LangChain
- OpenAI API
- BeautifulSoup
- SQLAlchemy
- Sentence Transformers
- FAISS向量数据库

## 许可证

MIT License
# ChatAgent_XPU - 西安工程大学智能问答系统

## 项目概述

ChatAgent_XPU是一个基于大语言模型的智能问答系统，专为西安工程大学设计，能够回答关于学校概况、学院专业、招生信息、教务管理等方面的问题。系统通过爬取学校官方网站内容，构建知识库，并使用向量检索技术实现精准的问答功能。

## 主要功能

- **智能问答**：回答关于西安工程大学的各类问题
- **知识库管理**：自动爬取、分类和存储学校网站信息
- **多模态理解**：支持图像识别和多模态输入
- **安全审核**：内置内容过滤和敏感词检测功能
- **数据查询**：支持权限控制的数据查询功能
- **网站爬取**：自动爬取学校网站内容并分类存储

## 技术架构

- 基于LangChain框架构建的智能问答系统
- 使用FAISS向量数据库进行高效相似度检索
- 采用Sentence-Transformers进行文本向量化
- 基于Streamlit和FastAPI构建Web界面和API服务
- 支持OpenAI和其他大语言模型接口

## 快速开始

### 环境要求

- Python 3.8+
- 安装requirements.txt中的依赖包

### 安装步骤

1. 克隆项目到本地
```
git clone https://github.com/yourusername/ChatAgent_XPU.git
cd ChatAgent_XPU
```

2. 安装依赖
```
pip install -r requirements.txt
```

3. 配置环境变量
创建.env文件，添加以下内容：
```
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=your_model_name
OPENAI_MODEL_BASE_URL=your_model_base_url
```

4. 运行Web界面
```
python src/main.py
```

5. 运行API服务
```
uvicorn chat_api:app --host 0.0.0.0 --port 8000
```

## 知识库构建

系统支持从西安工程大学官方网站自动爬取内容并构建知识库：

```
python crawl_xpu_simple.py
```

爬取的内容将自动分类并存储在Knowledge目录下。

## 目录结构

- `src/`: 源代码目录
  - `chatbi/`: 核心模块
    - `agents/`: 各类智能体实现
    - `tools/`: 工具类实现
    - `utils/`: 工具函数
- `config/`: 配置文件
- `Knowledge/`: 知识库文件
- `models/`: 模型文件
- `vector_db/`: 向量数据库文件

## 许可证

MIT License
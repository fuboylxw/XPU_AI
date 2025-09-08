# XPU AI Assistant 项目文档

## 项目概述

XPU AI Assistant 是一个基于大语言模型的新生信息问答系统，结合了RAG（检索增强生成）技术，为学校新生提供智能问答服务。系统支持文档上传、管理和基于文档内容的智能问答功能。

### 主要功能

- 文档管理：支持上传、处理和管理学校相关文档
- 智能问答：基于DeepSeek大语言模型的问答功能
- 向量检索：使用FAISS向量数据库进行高效文档检索
- Web界面：基于Streamlit的用户友好界面
- API服务：提供RESTful API接口

## 技术栈

- **后端框架**：FastAPI
- **前端界面**：Streamlit
- **大语言模型**：DeepSeek
- **向量数据库**：FAISS
- **嵌入模型**：Sentence Transformers
- **文档处理**：PyPDF2, python-docx, unstructured

## 安装指南

### 环境要求

- Python 3.8+
- 足够的磁盘空间用于存储模型和向量数据库

### 安装步骤

1. 克隆项目代码

```bash
git clone https://github.com/fuboylxw/XPU_AI.git
cd XPU_AI
```

2. 安装依赖包

```bash
pip install -r requirements.txt
```

3. 下载嵌入模型（可选，首次运行时会自动下载）

```bash
python scripts/download_models.py
```

## 配置说明

### 环境变量配置

复制 `.env.example` 为 `.env` 并配置以下变量：

```env
# 基础配置
ENVIRONMENT=development
DEBUG=false

# API服务配置
API__HOST=202.200.206.248
API__PORT=8000

# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 数据库配置
VECTOR_DB_PATH=data/vector_db
DOCUMENT_PATH=data/documents

# 安全配置
API_KEY=your_api_key
SECRET_KEY=your_secret_key
```

### 配置文件

项目支持多环境配置文件：

- `src/config/config.yaml` - 默认配置
- `src/config/config.development.yaml` - 开发环境
- `src/config/config.production.yaml` - 生产环境
- `src/config/config.testing.yaml` - 测试环境

## 运行指南

### 启动Web界面

```bash
streamlit run main.py
```

访问 http://localhost:8501 打开Streamlit界面

### 启动API服务

```bash
python start_api.py
```

- API服务地址: http://localhost:8316
- API文档: http://localhost:8316/docs
- 健康检查: http://localhost:8316/health

### 使用Docker部署（如果有Dockerfile）

```bash
docker build -t xpu-ai .
docker run -p 8000:8000 -p 8501:8501 xpu-ai
```

## 项目结构

```
├── api/                # API服务相关代码
├── data/               # 数据存储目录
│   ├── documents/      # 文档存储
│   ├── uploads/        # 上传文件临时存储
│   └── vector_db/      # 向量数据库
├── logs/               # 日志文件
├── models/             # 模型文件
│   └── embeddings/     # 嵌入模型
├── scripts/            # 实用脚本
├── src/                # 源代码
│   ├── agent/          # 智能代理
│   ├── config/         # 配置管理
│   ├── llm/            # 大语言模型接口
│   ├── mcp/            # MCP协议支持
│   ├── rag/            # RAG实现
│   └── utils/          # 工具函数
├── .env                # 环境变量
├── main.py             # Web界面入口
├── requirements.txt    # 依赖包列表
└── start_api.py        # API服务启动脚本
```

## 使用指南

### Web界面使用

1. 启动Web界面后，访问 http://localhost:8501
2. 在侧边栏上传学校相关文档（支持PDF、DOCX、TXT等格式）
3. 在主界面输入问题，系统会基于上传的文档内容进行回答

### API使用

详细API使用说明请参考 [API_README.md](API_README.md)

## 故障排除

### 常见问题

1. **API服务无法启动**
   - 检查端口8316是否被占用
   - 确认环境变量配置正确
   - 查看日志文件 `logs/app.log`

2. **文档上传失败**
   - 确认 `data/documents` 目录存在且可写
   - 检查文件格式是否支持
   - 检查文件大小是否超过限制

3. **模型下载失败**
   - 检查网络连接
   - 尝试手动运行 `python scripts/download_models.py`

## 开发指南

### 添加新功能

1. 在相应模块中添加功能实现
2. 更新API接口（如需）
3. 更新Web界面（如需）
4. 添加测试用例

### 运行测试

```bash
python -m pytest
```

## 许可证

[添加许可证信息]

## 联系方式

[添加联系方式]
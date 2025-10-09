# 新生信息问答Agent系统

基于LangChain、MCP协议和DeepSeek大模型的智能问答系统，专为新生提供学校信息查询服务。

## 功能特性

- 🤖 **智能问答**: 基于DeepSeek大模型的自然语言理解
- 📚 **RAG检索**: 支持文档上传和智能检索
- 🔧 **MCP协议**: 支持Model Context Protocol工具调用
- 📄 **多格式支持**: PDF、DOCX、TXT、Excel等文档格式
- 🌐 **Web界面**: 友好的Streamlit用户界面
- 📊 **向量数据库**: FAISS向量存储和相似度搜索
- 🚀 **RESTful API**: 完整的API服务支持
- 📖 **自动文档**: 自动生成API文档和测试报告

## 快速开始

### 1. 环境准备

确保已安装Python 3.8+：

```bash
python --version
```

### 2. 安装依赖

```bash
# 安装主要依赖
pip install -r requirements.txt

# 安装API服务依赖
pip install -r requirements-api.txt
```

### 3. 配置API密钥

复制 `.env.example` 为 `.env` 文件，填入您的配置：

```env
# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 基础配置
DEBUG=False
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# 安全配置
API_KEY=your_api_key_here
SECRET_KEY=your_secret_key_here
```

### 4. 启动系统

#### 启动完整服务

```bash
# Windows用户
start_all.bat

# 或手动启动
python main.py              # Streamlit界面
python api/main.py          # API服务
```

#### 单独启动服务

```bash
# 启动Streamlit界面
start.bat
# 或
streamlit run main.py

# 启动API服务
start_api.bat
# 或
python api/main.py
```

### 5. 访问系统

- **Streamlit界面**: http://202.200.206.248:8501
- **API服务**: http://202.200.206.248:8000
- **API文档**: http://202.200.206.248:8000/docs

## 使用指南

### 文档上传

1. 在左侧边栏选择"文档管理"
2. 选择文档类别（专业、课程、设施等）
3. 上传相关文档（支持PDF、DOCX、TXT、Excel）
4. 点击"处理上传的文档"按钮

### 智能问答

1. 在主界面的聊天框中输入问题
2. 系统会自动检索相关文档
3. 基于检索结果生成准确回答

### 示例问题

- "学校有哪些专业？"
- "图书馆的开放时间是什么？"
- "如何申请奖学金？"
- "宿舍条件怎么样？"

## API服务

本项目提供完整的RESTful API服务，支持聊天、文档管理、会话管理等功能。

### 启动API服务

```bash
# 启动API服务器
python api/main.py

# 或使用批处理文件
start_api.bat
```

### API文档

API服务启动后，可以访问以下地址查看文档：

- **Swagger UI**: http://202.200.206.248:8000/docs
- **ReDoc**: http://202.200.206.248:8000/redoc
- **OpenAPI JSON**: http://202.200.206.248:8000/openapi.json

### 主要API端点

- `GET /health` - 健康检查
- `POST /chat` - 聊天对话
- `POST /chat/stream` - 流式聊天
- `POST /documents/add` - 添加文档
- `POST /documents/upload` - 上传文件
- `GET /documents/search` - 搜索文档
- `GET /session/info` - 获取会话信息

### API认证

大部分API需要在请求头中包含API密钥：

```bash
X-API-Key: your_api_key_here
```

## 测试

### 运行所有测试

```bash
# 运行完整的测试套件
python scripts/run_api_tests.py

# 运行单元测试
python -m pytest tests/ -v

# 运行API集成测试
python -m pytest tests/test_api.py -v
```

### 生成测试报告

```bash
# 生成包含覆盖率的测试报告
python scripts/run_api_tests.py --coverage

# 生成API文档
python scripts/generate_api_docs.py

# 运行性能测试
python scripts/api_performance_test.py
```

### 测试选项

```bash
# 跳过特定测试
python scripts/run_api_tests.py --skip-unit --skip-performance

# 指定输出目录
python scripts/run_api_tests.py --output reports/custom

# 不启动API服务器（假设已在运行）
python scripts/run_api_tests.py --no-server
```

## 项目结构

```
XPU_AI/
├── api/                    # API服务模块
│   ├── main.py            # API主入口
│   ├── models.py          # 数据模型
│   ├── chat_service.py    # 聊天服务
│   ├── middleware.py      # 中间件
│   ├── validators.py      # 验证器
│   └── docs.py           # API文档配置
├── src/                   # 核心源码
│   ├── agent/            # 智能代理
│   ├── config/           # 配置管理
│   ├── llm/              # 大语言模型
│   ├── mcp/              # MCP协议
│   ├── rag/              # RAG检索
│   └── utils/            # 工具函数
├── tests/                # 测试文件
│   ├── test_api.py       # API测试
│   └── test_models.py    # 模型测试
├── scripts/              # 脚本工具
│   ├── generate_api_docs.py      # 文档生成
│   ├── api_performance_test.py   # 性能测试
│   └── run_api_tests.py          # 测试运行器
├── data/                 # 数据目录
│   ├── documents/        # 文档存储
│   └── vector_db/        # 向量数据库
├── logs/                 # 日志文件
├── requirements.txt      # 主要依赖
├── requirements-api.txt  # API依赖
├── .env.example         # 环境变量示例
└── README.md            # 项目说明
```

## 配置说明

### 环境变量

复制 `.env.example` 为 `.env` 并配置以下变量：

```env
# 基础配置
DEBUG=False
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 数据库配置
VECTOR_DB_PATH=data/vector_db
DOCUMENT_PATH=data/documents

# 安全配置
API_KEY=your_api_key
SECRET_KEY=your_secret_key

# 搜索引擎（可选）
BAIDU_API_KEY=your_baidu_api_key
GOOGLE_API_KEY=your_google_api_key
BING_API_KEY=your_bing_api_key
```

### 配置文件

项目支持多环境配置文件：

- `src/config/config.yaml` - 默认配置
- `src/config/config.development.yaml` - 开发环境
- `src/config/config.production.yaml` - 生产环境
- `src/config/config.testing.yaml` - 测试环境

## 部署

### 开发环境

```bash
# 启动完整服务
start_all.bat

# 或分别启动
start.bat          # Streamlit界面
start_api.bat      # API服务
```

### 生产环境

```bash
# 使用Gunicorn部署API
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 使用Docker部署（需要Dockerfile）
docker build -t xpu-ai .
docker run -p 8000:8000 -p 8501:8501 xpu-ai
```

## 故障排除

### 常见问题

1. **API服务无法启动**
   - 检查端口8000是否被占用
   - 确认环境变量配置正确
   - 查看日志文件 `logs/app.log`

2. **文档上传失败**
   - 确认 `data/documents` 目录存在且可写
   - 检查文件格式是否支持
   - 查看API响应错误信息

3. **向量数据库错误**
   - 删除 `data/vector_db` 目录重新初始化
   - 确认FAISS库安装正确

4. **测试失败**
   - 确认所有依赖已安装
   - 检查API服务是否正常运行
   - 查看测试报告了解具体错误

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# 查看API访问日志
tail -f logs/api.log
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

### 代码规范

- 使用 `black` 进行代码格式化
- 使用 `flake8` 进行代码检查
- 编写单元测试覆盖新功能
- 更新相关文档

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 项目Issues: [GitHub Issues](https://github.com/your-repo/XPU_AI/issues)
- 邮箱: your-email@example.com

---

**注意**: 请确保在生产环境中妥善保管API密钥和其他敏感信息。
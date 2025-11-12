# ChatBot XPU 3.0 - FastAPI 智能对话系统

一个基于 FastAPI 和 Vue.js 的智能对话系统，支持文本聊天、语音识别、语音合成、知识库查询、数据查询等多种功能。

## 🌟 项目特色

- **多模态交互**: 支持文本、语音、图像等多种输入方式
- **智能问答**: 集成知识库检索、网络搜索、数据分析等功能
- **语音对话**: 支持实时语音识别和语音合成
- **多语言支持**: 支持中英文等多语言对话
- **安全审计**: 内置安全审计智能体，确保对话内容安全
- **可扩展架构**: 模块化设计，易于扩展新功能

## 🏗️ 系统架构

### 技术栈
- **后端**: FastAPI + Python 3.12
- **前端**: Vue.js 3 + Vite + TDesign
- **数据库**: MySQL + PostgreSQL + Redis
- **向量数据库**: Qdrant
- **AI框架**: LangChain + OpenAI
- **语音处理**: WebRTC VAD + 多种语音识别/合成API

### 核心模块
- **对话智能体** (`chat_agent.py`): 核心对话处理引擎
- **意图识别** (`intent_recognition_agent.py`): 智能分析用户意图
- **知识查询** (`knowledge_query_agent.py`): 知识库检索和问答
- **数据查询** (`data_query_agent.py`): 结构化数据查询
- **安全审计** (`security_audit_agent.py`): 内容安全检测
- **语音识别/合成**: 语音交互处理

## 🚀 快速开始

### 环境要求
- Python 3.12+
- Node.js 18+
- MySQL 8.0+
- PostgreSQL 13+
- Redis 6.0+
- Qdrant 1.7+

### 1. 安装依赖

#### 后端依赖
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 前端依赖
```bash
cd frontend
npm install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置相关参数：
```bash
cp .env.example .env
```

主要配置项：
- **OpenAI 配置**: API密钥和模型设置
- **数据库配置**: MySQL、PostgreSQL、Redis连接信息
- **语音识别/合成**: 相关API配置
- **搜索引擎**: API配置

### 3. 启动服务

#### 启动后端服务
```bash
# 启动FastAPI服务
python fastapi_app/main.py

# 或使用uvicorn
uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 启动前端服务
```bash
cd frontend
npm run dev
```

### 4. 访问系统

- **前端界面**: http://localhost:5173
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 📋 API 接口

### 核心接口

#### 文本对话
```http
POST /api/chat/answer_question_stream
Content-Type: application/json

{
  "question": "你好",
  "conversation_id": "conv_123",
  "user_id": "user_123",
  "stream": true
}
```

#### 语音识别
```http
POST /api/voice/recognize
Content-Type: multipart/form-data

audio_file: [音频文件]
user_id: user_123
```

#### 语音合成
```http
POST /api/tts/generate
Content-Type: application/json

{
  "text": "你好，我是智能助手",
  "format": "mp3-16k",
  "lang": "zh"
}
```

#### 文件上传
```http
POST /api/upload/file
Content-Type: multipart/form-data

file: [文件]
user_id: user_123
conversation_id: conv_123
```

### 完整API文档
访问 http://localhost:8000/docs 查看完整的API文档和交互式测试界面。

## 🔧 配置说明

### 数据库配置
系统使用多数据库架构：
- **MySQL**: 存储用户信息、对话记录等核心业务数据
- **PostgreSQL**: 存储权限信息和配置数据
- **Redis**: 缓存和会话存储
- **Qdrant**: 向量数据库存储知识库嵌入

### AI模型配置
支持多种AI模型和提供商：
- **OpenAI**: GPT系列模型
- **本地模型**: 通过transformers加载
- **嵌入模型**: 用于知识库检索

### 语音配置
支持多种语音识别和合成服务：
- **语音识别**: 支持多个API提供商
- **语音合成**: 支持多种格式和语言
- **VAD**: WebRTC语音活动检测

## 📁 项目结构

```
Chatbot_XPU3.0_fastapi/
├── config/                          # 配置文件
│   ├── __init__.py
│   └── settings.py                  # 系统配置
├── docs/                            # 文档
│   └── continuous_voice_architecture.md
├── fastapi_app/                     # FastAPI应用
│   ├── routers/                     # API路由
│   │   ├── auth.py                  # 认证接口
│   │   ├── chat.py                  # 对话接口
│   │   ├── conversations.py         # 对话管理
│   │   ├── tts.py                   # 语音合成
│   │   ├── upload.py                # 文件上传
│   │   ├── voice.py                   # 语音识别
│   │   └── websocket_voice.py       # WebSocket语音
│   ├── static/                      # 静态文件
│   ├── auth.py                      # 认证逻辑
│   ├── database.py                  # 数据库连接
│   ├── email_service.py             # 邮件服务
│   ├── main.py                      # 主应用
│   ├── models.py                    # 数据模型
│   └── schemas.py                   # 数据模式
├── frontend/                        # Vue.js前端
│   ├── src/
│   │   ├── components/              # Vue组件
│   │   ├── composables/             # 组合式函数
│   │   ├── router/                  # 路由配置
│   │   ├── store/                   # 状态管理
│   │   └── utils/                   # 工具函数
│   └── package.json
├── logs/                            # 日志文件
├── models_cache/                    # 模型缓存
├── src/Chatbot/                     # 核心智能体
│   ├── agents/                      # AI智能体
│   │   ├── chat_agent.py            # 核心对话智能体
│   │   ├── intent_recognition_agent.py # 意图识别
│   │   ├── knowledge_query_agent.py # 知识查询
│   │   ├── data_query_agent.py      # 数据查询
│   │   ├── security_audit_agent.py  # 安全审计
│   │   ├── voice_recognition_agent.py # 语音识别
│   │   └── text_to_speech_agent.py  # 语音合成
│   ├── services/                    # 服务层
│   ├── tests/                       # 测试文件
│   ├── tools/                       # 工具模块
│   │   ├── llm_client.py            # LLM客户端
│   │   ├── web_search.py            # 网络搜索
│   │   ├── document_manager.py      # 文档管理
│   │   ├── dense_retrieval.py       # 稠密检索
│   │   └── sparse_retrieval.py      # 稀疏检索
│   └── utils/                       # 工具函数
│       ├── logger.py                # 日志配置
│       ├── memory_storage.py        # 内存存储
│       ├── global_initializer.py    # 全局初始化
│       └── upload_processor.py      # 上传处理
├── requirements.txt                 # Python依赖
├── .env.example                     # 环境变量示例
└── README.md                        # 项目文档
```

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest src/Chatbot/tests/

# 运行带覆盖率的测试
pytest --cov=src
```

### 测试覆盖
- **单元测试**: 核心智能体功能测试
- **集成测试**: API接口测试
- **性能测试**: 并发和负载测试

## 🚀 部署

### 生产环境部署
1. **环境配置**: 配置生产环境变量
2. **数据库初始化**: 创建和初始化数据库
3. **依赖安装**: 安装生产依赖
4. **静态文件**: 构建前端静态文件
5. **服务启动**: 使用进程管理器启动服务

### Docker部署（可选）
```dockerfile
# Dockerfile示例
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "fastapi_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔒 安全说明

### 安全特性
- **内容审计**: 内置安全审计智能体
- **权限控制**: 基于角色的访问控制
- **数据加密**: 敏感数据加密存储
- **API安全**: JWT认证和请求验证

### 安全配置
- 定期更新依赖包
- 配置HTTPS和SSL证书
- 设置适当的CORS策略
- 监控和日志审计

## 📞 支持与联系

### 问题反馈
- 提交Issue到项目仓库
- 联系开发团队
- 查看日志文件进行故障排查

### 贡献指南
1. Fork项目仓库
2. 创建功能分支
3. 提交代码更改
4. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- 感谢所有贡献者和支持者
- 感谢开源社区提供的优秀工具和框架
- 特别感谢相关AI服务提供商

---

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！**
# 新生信息问答API接口文档

## 概述

本API提供新生信息问答服务，基于RAG技术和DeepSeek大语言模型，支持文档管理和智能问答功能。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false
```

### 3. 启动服务

#### 方式一：使用启动脚本
```bash
python start_api.py
```

#### 方式二：使用批处理文件（Windows）
```bash
start_api.bat
```

### 4. 访问API

- **API服务地址**: http://202.200.206.248:8000
- **API文档**: http://202.200.206.248:8000/docs
- **健康检查**: http://202.200.206.248:8000/health

## API接口说明

### 1. 健康检查

**GET** `/health`

检查API服务状态。

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00Z",
  "version": "1.0.0"
}
```

### 2. 对话接口

**POST** `/chat`

发送消息进行对话。

**请求参数**:
```json
{
  "message": "请问学校的招生政策是什么？",
  "session_id": "user123",
  "stream": false
}
```

**响应示例**:
```json
{
  "response": "根据学校最新的招生政策...",
  "session_id": "user123",
  "timestamp": "2024-01-20T10:30:00Z",
  "context_used": true
}
```

### 3. 流式对话接口

**POST** `/chat/stream`

发送消息进行流式对话。

**请求参数**:
```json
{
  "message": "请介绍一下学校的专业设置",
  "session_id": "user123"
}
```

**响应**: Server-Sent Events (SSE) 流

### 4. 文档上传接口

**POST** `/documents/upload`

上传文档到知识库。

**请求参数** (multipart/form-data):
- `file`: 文档文件 (PDF, DOCX, TXT, XLSX)
- `category`: 文档分类 (可选)
- `description`: 文档描述 (可选)

**响应示例**:
```json
{
  "success": true,
  "document_id": "doc_20240120_001",
  "message": "文档上传成功",
  "filename": "招生简章.pdf",
  "category": "招生信息"
}
```

### 5. 文本文档添加接口

**POST** `/documents/add-text`

添加文本内容到知识库。

**请求参数**:
```json
{
  "content": "学校位于美丽的城市中心，拥有现代化的教学设施...",
  "title": "学校简介",
  "category": "学校信息",
  "description": "学校基本情况介绍"
}
```

### 6. 文档搜索接口

**POST** `/documents/search`

搜索相关文档。

**请求参数**:
```json
{
  "query": "学费标准",
  "category": "收费信息",
  "top_k": 5
}
```

**响应示例**:
```json
{
  "results": [
    {
      "content": "本科生学费标准为每年8000元...",
      "metadata": {
        "document_id": "doc_001",
        "category": "收费信息",
        "filename": "收费标准.pdf"
      },
      "score": 0.95
    }
  ],
  "total": 1
}
```

### 7. 文档摘要接口

**GET** `/documents/summary`

获取文档库摘要信息。

**响应示例**:
```json
{
  "total_documents": 25,
  "categories": {
    "招生信息": 8,
    "学校介绍": 5,
    "专业设置": 7,
    "收费标准": 3,
    "其他": 2
  },
  "last_updated": "2024-01-20T10:30:00Z"
}
```

### 8. 会话信息接口

**GET** `/sessions/{session_id}`

获取指定会话的信息。

**响应示例**:
```json
{
  "session_id": "user123",
  "created_at": "2024-01-20T10:00:00Z",
  "last_activity": "2024-01-20T10:30:00Z",
  "message_count": 5,
  "is_active": true
}
```

## 使用示例

### Python客户端示例

```python
import requests
import json

# API基础URL
BASE_URL = "http://202.200.206.248:8000"

class XPUAIClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session_id = None
    
    def health_check(self):
        """健康检查"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()
    
    def chat(self, message, session_id=None, stream=False):
        """发送对话消息"""
        data = {
            "message": message,
            "session_id": session_id or self.session_id,
            "stream": stream
        }
        response = requests.post(f"{self.base_url}/chat", json=data)
        result = response.json()
        
        # 保存会话ID
        if not self.session_id:
            self.session_id = result.get("session_id")
        
        return result
    
    def upload_document(self, file_path, category=None, description=None):
        """上传文档"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {}
            if category:
                data['category'] = category
            if description:
                data['description'] = description
            
            response = requests.post(
                f"{self.base_url}/documents/upload",
                files=files,
                data=data
            )
        return response.json()
    
    def add_text_document(self, content, title, category=None, description=None):
        """添加文本文档"""
        data = {
            "content": content,
            "title": title,
            "category": category,
            "description": description
        }
        response = requests.post(f"{self.base_url}/documents/add-text", json=data)
        return response.json()
    
    def search_documents(self, query, category=None, top_k=5):
        """搜索文档"""
        data = {
            "query": query,
            "category": category,
            "top_k": top_k
        }
        response = requests.post(f"{self.base_url}/documents/search", json=data)
        return response.json()
    
    def get_documents_summary(self):
        """获取文档摘要"""
        response = requests.get(f"{self.base_url}/documents/summary")
        return response.json()

# 使用示例
if __name__ == "__main__":
    client = XPUAIClient()
    
    # 健康检查
    print("健康检查:", client.health_check())
    
    # 上传文档
    # result = client.upload_document("招生简章.pdf", category="招生信息")
    # print("文档上传:", result)
    
    # 添加文本文档
    result = client.add_text_document(
        content="学校成立于1958年，是一所综合性大学...",
        title="学校历史",
        category="学校介绍"
    )
    print("添加文本:", result)
    
    # 对话
    response = client.chat("请介绍一下学校的历史")
    print("对话回复:", response["response"])
    
    # 搜索文档
    search_result = client.search_documents("学校历史")
    print("搜索结果:", search_result)
    
    # 获取文档摘要
    summary = client.get_documents_summary()
    print("文档摘要:", summary)
```

### JavaScript客户端示例

```javascript
class XPUAIClient {
    constructor(baseUrl = 'http://202.200.206.248:8000') {
        this.baseUrl = baseUrl;
        this.sessionId = null;
    }
    
    async healthCheck() {
        const response = await fetch(`${this.baseUrl}/health`);
        return await response.json();
    }
    
    async chat(message, sessionId = null, stream = false) {
        const data = {
            message,
            session_id: sessionId || this.sessionId,
            stream
        };
        
        const response = await fetch(`${this.baseUrl}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        // 保存会话ID
        if (!this.sessionId) {
            this.sessionId = result.session_id;
        }
        
        return result;
    }
    
    async uploadDocument(file, category = null, description = null) {
        const formData = new FormData();
        formData.append('file', file);
        if (category) formData.append('category', category);
        if (description) formData.append('description', description);
        
        const response = await fetch(`${this.baseUrl}/documents/upload`, {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    }
    
    async addTextDocument(content, title, category = null, description = null) {
        const data = {
            content,
            title,
            category,
            description
        };
        
        const response = await fetch(`${this.baseUrl}/documents/add-text`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        return await response.json();
    }
    
    async searchDocuments(query, category = null, topK = 5) {
        const data = {
            query,
            category,
            top_k: topK
        };
        
        const response = await fetch(`${this.baseUrl}/documents/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        return await response.json();
    }
    
    async getDocumentsSummary() {
        const response = await fetch(`${this.baseUrl}/documents/summary`);
        return await response.json();
    }
}

// 使用示例
async function example() {
    const client = new XPUAIClient();
    
    // 健康检查
    const health = await client.healthCheck();
    console.log('健康检查:', health);
    
    // 对话
    const chatResponse = await client.chat('请介绍一下学校的专业设置');
    console.log('对话回复:', chatResponse.response);
    
    // 搜索文档
    const searchResult = await client.searchDocuments('专业设置');
    console.log('搜索结果:', searchResult);
}

example();
```

## 错误处理

API使用标准HTTP状态码：

- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

错误响应格式：
```json
{
  "error": "错误类型",
  "message": "详细错误信息",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

## 注意事项

1. **文件上传限制**: 单个文件最大10MB
2. **支持的文件格式**: PDF, DOCX, TXT, XLSX
3. **会话超时**: 30分钟无活动自动过期
4. **并发限制**: 建议单个会话串行请求
5. **API密钥**: 生产环境建议配置API密钥认证

## 部署说明

### Docker部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "start_api.py"]
```

### 生产环境配置

```bash
# 使用Gunicorn部署
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 技术支持

如有问题，请联系技术支持团队或查看项目文档。
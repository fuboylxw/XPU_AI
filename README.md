# User AI 项目

## 项目概述

User AI 是一个基于 Node.js 和 Express 框架开发的 AI 聊天应用，提供了一个简洁美观的用户界面，支持与 AI 进行对话交互。该应用采用前后端分离架构，前端使用原生 JavaScript 实现，后端基于 Express 服务器提供 API 支持。

## 技术栈

- **前端**：HTML5, CSS3, JavaScript
- **后端**：Node.js, Express
- **第三方库**：
  - Marked.js (Markdown 渲染)
  - Highlight.js (代码高亮)

## 项目结构

```
├── package.json          # 项目配置和依赖管理
├── server.js            # 后端服务器入口文件
├── public/              # 前端静态资源目录
│   ├── index.html       # 主页面
│   ├── styles.css       # 样式表
│   └── script.js        # 前端交互逻辑
```

## 功能特性

### 1. 用户界面

- **双面板设计**：左侧为历史对话列表，右侧为当前聊天界面
- **响应式布局**：适配不同屏幕尺寸
- **Markdown 支持**：AI 回复支持 Markdown 格式，包括代码高亮
- **流式响应**：AI 回复采用流式传输，实现打字机效果

### 2. 会话管理

- **创建新会话**：支持创建多个独立的聊天会话
- **切换会话**：可在不同会话间自由切换
- **删除会话**：支持删除不需要的历史会话
- **本地存储**：使用 localStorage 保存会话历史，页面刷新后不丢失

### 3. 消息处理

- **发送消息**：支持文本消息发送
- **流式接收**：使用 SSE (Server-Sent Events) 技术接收流式响应
- **格式化显示**：支持 Markdown 格式渲染，代码块高亮

## 安装与运行

### 环境要求

- Node.js (v12.0.0 或更高版本)
- npm (v6.0.0 或更高版本)

### 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/你的用户名/User_AI.git
cd User_AI
```

2. 安装依赖

```bash
npm install
```

3. 启动服务器

```bash
npm start
```

4. 访问应用

打开浏览器，访问 http://localhost:2307

## API 接口

### 1. 聊天接口

- **端点**：`/api/chat`
- **方法**：POST
- **请求体**：
  ```json
  {
    "message": "用户消息内容"
  }
  ```
- **响应**：
  ```json
  {
    "response": "AI 回复内容（支持 Markdown 格式）"
  }
  ```

### 2. 流式聊天接口

- **端点**：`http://localhost:8316/chat/stream`
- **方法**：POST
- **请求体**：
  ```json
  {
    "message": "用户消息内容"
  }
  ```
- **响应**：SSE 格式的流式数据

## 使用说明

1. 打开应用后，系统会自动创建一个新的聊天会话
2. 在输入框中输入消息，点击发送按钮或按 Enter 键发送
3. AI 将以流式方式返回响应，支持 Markdown 格式
4. 可以点击左上角的"+ 新对话"按钮创建新的会话
5. 在左侧历史列表中点击任意会话可以切换到该会话

## 开发扩展

### 前端定制

- 样式可通过修改 `public/styles.css` 文件进行定制
- 交互逻辑可通过修改 `public/script.js` 文件进行扩展

### 后端扩展

- 可在 `server.js` 中添加新的 API 端点
- 可修改 `formatResponse` 函数以实现不同的响应格式处理

## 注意事项

- 当前版本的流式聊天接口指向 `http://localhost:8316`，实际部署时需要修改为正确的服务器地址
- 本地存储有容量限制，过多的聊天历史可能导致存储溢出
- 应用目前不支持图片、语音等多媒体消息类型

## 贡献指南

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件

## 联系方式

项目维护者 - [您的姓名](mailto:您的邮箱)

项目链接: [https://github.com/你的用户名/User_AI](https://github.com/你的用户名/User_AI)
<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  background: linear-gradient(135deg, #4A90E2 0%, #5BA7F7 100%);
  min-height: 100vh;
}

.app {
  display: flex;
  height: 100vh;
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.1) 0%, rgba(91, 167, 247, 0.1) 100%);
  backdrop-filter: blur(10px);
}

/* 左侧边栏 */
.sidebar {
  width: 280px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(229, 229, 229, 0.3);
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid rgba(229, 229, 229, 0.3);
}

.new-chat-btn {
  width: 100%;
  padding: 12px 16px;
  background: linear-gradient(135deg, #4A90E2 0%, #5BA7F7 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.new-chat-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.new-chat-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(74, 144, 226, 0.4);
}

.new-chat-btn:hover::before {
  left: 100%;
}

.new-chat-btn:active {
  transform: translateY(0);
  transition: transform 0.1s;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

/* 删除按钮样式 */
.conversation-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  margin: 4px 8px;
  cursor: pointer;
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.conv-content {
  flex: 1;
  cursor: pointer;
}

.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #999;
  cursor: pointer;
  transition: all 0.2s ease;
  opacity: 0;
  transform: scale(0.8);
}

.conversation-item:hover .delete-btn {
  opacity: 1;
  transform: scale(1);
}

.delete-btn:hover {
  background: rgba(255, 71, 87, 0.1);
  color: #ff4757;
  transform: scale(1.1);
}

/* 深色模式下的删除按钮 */
body.dark .delete-btn {
  color: #ccc;
}

body.dark .delete-btn:hover {
  background: rgba(255, 71, 87, 0.2);
  color: #ff6b7a;
}

.conversation-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.1), rgba(91, 167, 247, 0.1));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.conversation-item:hover {
  background: rgba(248, 249, 250, 0.8);
  transform: translateX(4px);
}

.conversation-item:hover::before {
  opacity: 1;
}

.conversation-item.active {
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.15), rgba(91, 167, 247, 0.15));
  border-left: 3px solid #4A90E2;
  transform: translateX(4px);
}

.conv-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
  position: relative;
  z-index: 1;
}

.conv-time {
  font-size: 12px;
  color: #666;
  position: relative;
  z-index: 1;
}

/* 主内容区域 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

/* 顶部导航栏 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  border-bottom: 1px solid rgba(229, 229, 229, 0.3);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
}

.chat-title {
  display: flex;
  align-items: center;
}

.title-icon {
  font-size: 18px;
  font-weight: 600;
  background: linear-gradient(135deg, #4A90E2 0%, #5BA7F7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 主题标签样式 */
.theme-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
  margin-right: 8px;
  transition: color 0.3s ease;
}

/* TDesign Switch 样式 */
.TDesign-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  background: #e7e7e7;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  outline: none;
}

.TDesign-switch:hover {
  background: #d9d9d9;
}

.TDesign-switch__handle {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: #ffffff;
  border-radius: 50%;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* 用户头像样式 */
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  margin-left: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid rgba(255, 255, 255, 0.2);
}

.user-avatar:hover {
  transform: scale(1.05);
  border-color: rgba(74, 144, 226, 0.5);
  box-shadow: 0 4px 12px rgba(74, 144, 226, 0.2);
}

/* 聊天区域 */
.chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
}

.messages {
  max-width: 800px;
  margin: 0 auto;
}

.message {
  margin-bottom: 24px;
  animation: messageSlideIn 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.sender {
  font-size: 12px;
  font-weight: 600;
  color: #666;
}

.time {
  font-size: 12px;
  color: #999;
}

.message-content {
  padding: 16px 20px;
  border-radius: 16px;
  line-height: 1.6;
  font-size: 14px;
  position: relative;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.message.user .message-content {
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.15), rgba(91, 167, 247, 0.15));
  color: #333;
  margin-left: auto;
  max-width: 70%;
  border: 1px solid rgba(74, 144, 226, 0.2);
}

.message.assistant .message-content {
  background: rgba(240, 240, 240, 0.8);
  color: #333;
  max-width: 85%;
  border: 1px solid rgba(229, 229, 229, 0.3);
}

.message-content:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

/* 智能体消息样式 - 无气泡格式 */
.assistant-message {
  margin-bottom: 24px;
  animation: messageSlideIn 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.assistant-content {
  line-height: 1.6;
  font-size: 14px;
  color: #333;
  max-width: 85%;
  padding: 0;
  background: transparent;
  border: none;
}

/* 深色模式下的智能体消息 */
body.dark .assistant-content {
  color: #ffffff;
}

/* Markdown 样式 */
.assistant-content strong {
  font-weight: 600;
  color: #2c3e50;
}

.assistant-content em {
  font-style: italic;
  color: #7f8c8d;
}

.assistant-content code {
  background: rgba(74, 144, 226, 0.1);
  color: #4A90E2;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
}

/* 深色模式下的 Markdown 样式 */
body.dark .assistant-content strong {
  color: #ecf0f1;
}

body.dark .assistant-content em {
  color: #bdc3c7;
}

body.dark .assistant-content code {
  background: rgba(74, 144, 226, 0.2);
  color: #5BA7F7;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  max-width: 600px;
  margin: 0 auto;
  text-align: center;
  animation: fadeInUp 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.welcome-message {
  margin-bottom: 32px;
}

.welcome-message h2 {
  font-size: 28px;
  background: linear-gradient(135deg, #4A90E2 0%, #5BA7F7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 12px;
  font-weight: 600;
}

.welcome-message p {
  font-size: 16px;
  color: #666;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
  margin-bottom: 24px;
}

.quick-btn {
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(229, 229, 229, 0.3);
  border-radius: 25px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.quick-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.1), rgba(91, 167, 247, 0.1));
  transition: left 0.3s ease;
}

.quick-btn:hover {
  border-color: #4A90E2;
}

.quick-btn:hover::before {
  left: 0;
}

.quick-btn:active {
  transition: transform 0.1s;
}

.additional-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.action-item {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(229, 229, 229, 0.3);
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.action-item:hover {
  background: rgba(248, 249, 250, 0.9);
  border-color: #4A90E2;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(74, 144, 226, 0.2);
}

/* 输入区域 */
.input-area {
  border-top: 1px solid rgba(229, 229, 229, 0.3);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  padding: 20px 24px;
}

.input-container {
  max-width: 800px;
  margin: 0 auto;
}

/* 输入框容器需要相对定位 */
.input-wrapper {
  position: relative;
  display: flex;
  align-items: flex-start;
  padding: 16px 80px 16px 16px; /* 右侧留出更多按钮空间 */
  border: 2px solid rgba(229, 229, 229, 0.3);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.input-wrapper:focus-within {
  border-color: #4A90E2;
  box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
  transform: translateY(-2px);
}

.message-input {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 14px;
  line-height: 1.5;
  min-height: 20px;
  max-height: 120px;
  font-family: inherit;
  background: transparent;
}

.message-input::placeholder {
  color: #999;
}

/* 输入区域按钮样式 */
.input-actions {
  position: absolute;
  bottom: 6px;
  right: 6px;
  display: flex;
  align-items: center;
  gap: 3px;
}

.attachment-btn,
.voice-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: rgba(245, 245, 245, 0.9);
  cursor: pointer;
  transition: all 0.2s ease;
  color: #666;
}

.attachment-btn:hover,
.voice-btn:hover {
  background: rgba(224, 224, 224, 0.9);
  transform: scale(1.05);
  color: #333;
}

/* 发送按钮样式 - 更小更紧凑 */
.send-btn {
  padding: 8px;
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #4A90E2 0%, #5BA7F7 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(74, 144, 226, 0.4);
}

.send-btn:hover:not(:disabled)::before {
  left: 100%;
}

.send-btn:active:not(:disabled) {
  transform: translateY(0);
  transition: transform 0.1s;
}

.send-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* 语音录制状态 */
.voice-btn.recording {
  background: rgba(255, 71, 87, 0.9);
  animation: pulse 1.5s infinite;
  color: white;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(255, 71, 87, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(255, 71, 87, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(255, 71, 87, 0);
  }
}

/* 深色模式下的按钮样式 */
[theme-mode="dark"] .attachment-btn,
[theme-mode="dark"] .voice-btn {
  background: rgba(44, 44, 44, 0.9);
  color: #ccc;
}

[theme-mode="dark"] .attachment-btn:hover,
[theme-mode="dark"] .voice-btn:hover {
  background: rgba(60, 60, 60, 0.9);
  color: #fff;
}

/* 悬浮工具栏样式 */
.floating-toolbar {
  position: fixed;
  top: 50%;
  right: 20px;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  z-index: 1000;
}

.main-toolbar-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, #4A90E2 0%, #5BA7F7 100%);
  color: white;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 20px rgba(74, 144, 226, 0.3);
  position: relative;
  overflow: hidden;
}

.main-toolbar-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.main-toolbar-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 25px rgba(74, 144, 226, 0.4);
}

.main-toolbar-btn:hover::before {
  left: 100%;
}

.main-toolbar-btn:active {
  transform: scale(1.05);
  transition: transform 0.1s;
}

.toolbar-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
  animation: slideInFromRight 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideInFromRight {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.toolbar-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border: none;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  color: #666;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(229, 229, 229, 0.3);
  position: relative;
  overflow: hidden;
}

.toolbar-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.1), rgba(91, 167, 247, 0.1));
  transition: left 0.3s ease;
}

.toolbar-btn:hover {
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.1), rgba(91, 167, 247, 0.1));
  border-color: #4A90E2;
  color: #4A90E2;
  transform: translateX(-8px);
  box-shadow: 0 4px 20px rgba(74, 144, 226, 0.3);
}

.toolbar-btn:hover::before {
  left: 0;
}

.toolbar-btn:active {
  transform: translateX(-4px);
  transition: transform 0.1s;
}

/* 深色模式下的悬浮工具栏 */
body.dark .toolbar-btn {
  background: rgba(45, 45, 45, 0.95);
  border-color: rgba(64, 64, 64, 0.5);
  color: #ccc;
}

body.dark .toolbar-btn:hover {
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.2), rgba(91, 167, 247, 0.2));
  border-color: #4A90E2;
  color: #4A90E2;
}

/* 响应式设计 - 移动端隐藏悬浮工具栏 */
@media (max-width: 768px) {
  .floating-toolbar {
    display: none;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 240px;
  }
  
  .chat-area {
    padding: 16px;
  }
  
  .input-area {
    padding: 16px;
  }
  
  .message.user .message-content {
    max-width: 85%;
  }
}

/* 深色主题 */
body.dark {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

body.dark .app {
  background: linear-gradient(135deg, rgba(26, 26, 46, 0.9) 0%, rgba(22, 33, 62, 0.9) 100%);
}

body.dark .sidebar {
  background: rgba(45, 45, 45, 0.95);
  border-right-color: rgba(64, 64, 64, 0.5);
}

body.dark .main-content {
  background: rgba(26, 26, 26, 0.95);
}

body.dark .header {
  background: rgba(45, 45, 45, 0.9);
  border-bottom-color: rgba(64, 64, 64, 0.5);
}

body.dark .input-area {
  background: rgba(45, 45, 45, 0.9);
  border-top-color: rgba(64, 64, 64, 0.5);
}

body.dark .conv-title {
  color: #ffffff;
}

body.dark .conv-time {
  color: #cccccc;
}

body.dark .title-icon {
  color: #ffffff;
}

/* 深色模式下的主题标签 */
[theme-mode="dark"] .theme-label {
  color: #cccccc;
}

/* 深色模式下的 Switch 样式 */
[theme-mode="dark"] .TDesign-switch {
  background: #0052d9;
}

[theme-mode="dark"] .TDesign-switch:hover {
  background: #266fe8;
}

[theme-mode="dark"] .TDesign-switch__handle {
  transform: translateX(20px);
  background: #ffffff;
}

/* 深色模式下的用户头像 */
[theme-mode="dark"] .user-avatar {
  border-color: rgba(255, 255, 255, 0.1);
}

[theme-mode="dark"] .user-avatar:hover {
  border-color: rgba(74, 144, 226, 0.6);
  box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);
}

/* 深色模式下的用户消息样式 */
body.dark .message.user .message-content {
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.3), rgba(91, 167, 247, 0.3));
  color: #ffffff;
  border-color: rgba(74, 144, 226, 0.4);
}

body.dark .message.assistant .message-content {
  background: rgba(64, 64, 64, 0.8);
  color: #ffffff;
  border-color: rgba(96, 96, 96, 0.3);
}

/* 深色模式下的消息头部样式 */
body.dark .sender {
  color: #cccccc;
}

body.dark .time {
  color: #999999;
}

body.dark .welcome-message p {
  color: #cccccc;
}

body.dark .quick-btn {
  background: rgba(64, 64, 64, 0.8);
  border-color: rgba(96, 96, 96, 0.3);
  color: #ffffff;
}

body.dark .action-item {
  background: rgba(64, 64, 64, 0.6);
  border-color: rgba(96, 96, 96, 0.3);
  color: #ffffff;
}

body.dark .input-wrapper {
  background: rgba(64, 64, 64, 0.8);
  border-color: rgba(96, 96, 96, 0.3);
}

body.dark .message-input {
  color: #ffffff;
}

body.dark .message-input::placeholder {
  color: #999;
}

body.dark .conversation-item:hover {
  background: rgba(64, 64, 64, 0.6);
}

body.dark .conversation-item.active {
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.25), rgba(91, 167, 247, 0.25));
  border-left-color: #4A90E2;
}
</style>
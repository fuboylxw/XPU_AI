document.addEventListener('DOMContentLoaded', () => {
  const chatMessages = document.getElementById('chat-messages');
  const userInput = document.getElementById('user-input');
  const sendButton = document.getElementById('send-button');
  const chatHistory = document.getElementById('chat-history');
  const newChatButton = document.getElementById('new-chat-button');

  // 聊天会话管理
  let chatSessions = [];
  let currentSessionId = null;
  let sessionIdCounter = 0;

  // 从localStorage加载聊天会话
  function loadChatSessions() {
    const saved = localStorage.getItem('chatSessions');
    if (saved) {
      chatSessions = JSON.parse(saved);
      sessionIdCounter = Math.max(...chatSessions.map(s => s.id), 0) + 1;
    }
  }

  // 保存聊天会话到localStorage
  function saveChatSessions() {
    localStorage.setItem('chatSessions', JSON.stringify(chatSessions));
  }

  // 创建新的聊天会话
  function createNewChatSession() {
    const newSession = {
      id: sessionIdCounter++,
      title: '新对话',
      createdAt: new Date().toISOString(),
      conversationHistory: [],
      currentRound: 0
    };
    chatSessions.unshift(newSession);
    currentSessionId = newSession.id;
    saveChatSessions();
    renderChatHistory();
    clearChatMessages();
    
    // 添加欢迎消息
    addWelcomeMessage();
    return newSession;
  }

  // 切换到指定的聊天会话
  function switchToChatSession(sessionId) {
    currentSessionId = sessionId;
    const session = chatSessions.find(s => s.id === sessionId);
    if (session) {
      renderConversationHistory(session.conversationHistory);
      renderChatHistory();
    }
  }

  // 删除聊天会话
  function deleteChatSession(sessionId) {
    chatSessions = chatSessions.filter(s => s.id !== sessionId);
    saveChatSessions();
    
    if (currentSessionId === sessionId) {
      if (chatSessions.length > 0) {
        switchToChatSession(chatSessions[0].id);
      } else {
        createNewChatSession();
      }
    } else {
      renderChatHistory();
    }
  }

  // 获取当前会话
  function getCurrentSession() {
    return chatSessions.find(s => s.id === currentSessionId);
  }

  // 更新会话标题
  function updateSessionTitle(sessionId, title) {
    const session = chatSessions.find(s => s.id === sessionId);
    if (session) {
      session.title = title.substring(0, 30); // 限制标题长度
      saveChatSessions();
      renderChatHistory();
    }
  }

  // 渲染聊天历史列表
  function renderChatHistory() {
    chatHistory.innerHTML = '';
    
    chatSessions.forEach(session => {
      const historyItem = document.createElement('div');
      historyItem.className = `chat-history-item ${session.id === currentSessionId ? 'active' : ''}`;
      
      const title = document.createElement('div');
      title.className = 'chat-title';
      title.textContent = session.title;
      
      const time = document.createElement('div');
      time.className = 'chat-time';
      time.textContent = formatTime(session.createdAt);
      
      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'delete-chat';
      deleteBtn.innerHTML = '×';
      deleteBtn.onclick = (e) => {
        e.stopPropagation();
        deleteChatSession(session.id);
      };
      
      historyItem.appendChild(title);
      historyItem.appendChild(time);
      historyItem.appendChild(deleteBtn);
      
      historyItem.onclick = () => switchToChatSession(session.id);
      
      chatHistory.appendChild(historyItem);
    });
  }

  // 格式化时间显示
  function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays < 7) return `${diffDays}天前`;
    
    return date.toLocaleDateString('zh-CN', {
      month: '2-digit',
      day: '2-digit'
    });
  }

  // 清空聊天消息区域
  function clearChatMessages() {
    chatMessages.innerHTML = '';
  }

  // 添加欢迎消息
  function addWelcomeMessage() {
    const session = getCurrentSession();
    if (session && session.conversationHistory.length === 0) {
      session.conversationHistory.push({
        round: 0,
        userMessage: '',
        aiMessage: '我是你的智能助手纺芽，有什么可以帮助你的吗？'
      });
      saveChatSessions();
      renderConversationHistory(session.conversationHistory);
    }
  }

  // 配置marked库以支持代码高亮
  marked.setOptions({
    highlight: function(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value;
      }
      return hljs.highlightAuto(code).value;
    },
    breaks: true
  });

  // 添加消息到聊天界面
  function addMessage(content, isUser = false, isNewRound = false) {
    const session = getCurrentSession();
    if (!session) return;

    // 更新对话历史
    if (isUser) {
      // 用户发送新消息，创建新的对话轮次
      if (isNewRound || session.conversationHistory.length === 0) {
        session.currentRound++;
        session.conversationHistory.push({
          round: session.currentRound,
          userMessage: content,
          aiMessage: ''
        });
        
        // 自动更新会话标题（使用用户消息的前20个字符）
        if (session.title === '新对话' && content.trim()) {
          updateSessionTitle(session.id, content.trim());
        }
      } else {
        // 更新当前轮次的用户消息
        session.conversationHistory[session.conversationHistory.length - 1].userMessage = content;
      }
    } else {
      // 更新当前轮次的AI消息
      if (session.conversationHistory.length > 0) {
        session.conversationHistory[session.conversationHistory.length - 1].aiMessage = content;
      }
    }

    // 保存会话并重新渲染
    saveChatSessions();
    renderConversationHistory(session.conversationHistory);
  }

  // 渲染整个对话历史
  function renderConversationHistory(conversationHistory = null) {
    const session = getCurrentSession();
    if (!session && !conversationHistory) return;
    
    const history = conversationHistory || session.conversationHistory;
    // 清空聊天区域
    chatMessages.innerHTML = '';

    // 渲染所有对话轮次
    history.forEach((round, index) => {
      // 创建对话轮次容器
      const roundDiv = document.createElement('div');
      roundDiv.className = 'conversation-round';
      roundDiv.dataset.round = round.round;

      // 添加轮次标记（可选）
      const roundIndicator = document.createElement('div');
      roundIndicator.className = 'round-indicator';
      roundIndicator.textContent = `对话 #${round.round}`;
      roundDiv.appendChild(roundIndicator);

      // 添加用户消息
      if (round.userMessage) {
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'message user-message';
        
        const userMessageContent = document.createElement('div');
        userMessageContent.className = 'message-content';
        userMessageContent.textContent = round.userMessage;
        
        userMessageDiv.appendChild(userMessageContent);
        roundDiv.appendChild(userMessageDiv);
      }

      // 添加AI消息
      if (round.aiMessage) {
        const aiMessageDiv = document.createElement('div');
        aiMessageDiv.className = 'message ai-message';
        
        const aiMessageContent = document.createElement('div');
        aiMessageContent.className = 'message-content markdown-content';
        
        // 使用marked库将Markdown文本转换为HTML
        aiMessageContent.innerHTML = marked.parse(round.aiMessage);
        
        // 对代码块应用高亮
        aiMessageContent.querySelectorAll('pre code').forEach((block) => {
          hljs.highlightBlock(block);
        });
        
        aiMessageDiv.appendChild(aiMessageContent);
        roundDiv.appendChild(aiMessageDiv);
      }

      // 将轮次添加到聊天区域
      chatMessages.appendChild(roundDiv);
    });
    
    // 滚动到最新消息
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // 显示加载指示器
  function showTypingIndicator() {
    const indicatorDiv = document.createElement('div');
    indicatorDiv.className = 'message ai-message';
    indicatorDiv.id = 'typing-indicator';
    
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<span></span><span></span><span></span>';
    
    indicatorDiv.appendChild(indicator);
    chatMessages.appendChild(indicatorDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // 移除加载指示器
  function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
      indicator.remove();
    }
  }

  // 发送消息到API并处理流式响应
  async function sendMessage(message) {
    try {
      // 显示用户消息，开始新的对话轮次
      addMessage(message, true, true);
      
      // 显示加载指示器
      showTypingIndicator();
      
      // 准备请求
      const response = await fetch('http://localhost:8316/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
      });
      
      if (!response.ok) {
        throw new Error(`API请求失败: ${response.status}`);
      }
      
      // 移除加载指示器
      removeTypingIndicator();
      
      // 使用EventSource处理SSE格式数据
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let fullContent = '';
      
      // 读取流式响应
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }
        
        // 解码并添加到缓冲区
        buffer += decoder.decode(value, { stream: true });
        
        // 处理SSE格式数据（data: {...} 格式）
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保留最后一个不完整的行
        
        for (const line of lines) {
          if (line.trim() === 'data: [DONE]') {
            // 流结束
            continue;
          }
          
          if (line.startsWith('data: ')) {
            try {
              // 提取JSON数据
              const jsonStr = line.substring(6); // 去掉 'data: '
              const data = JSON.parse(jsonStr);
              
              // 如果有内容，则添加到完整内容中
              if (data.content !== undefined) {
                fullContent += data.content;
                
                // 更新当前对话轮次的AI回复
                const session = getCurrentSession();
                if (session && session.conversationHistory.length > 0) {
                  session.conversationHistory[session.conversationHistory.length - 1].aiMessage = fullContent;
                  saveChatSessions();
                  renderConversationHistory(session.conversationHistory);
                }
              }
            } catch (e) {
              console.error('解析SSE数据出错:', e, line);
            }
          }
        }
      }
    } catch (error) {
      console.error('发送消息时出错:', error);
      removeTypingIndicator();
      
      // 在当前对话轮次中添加错误消息
      const session = getCurrentSession();
      if (session && session.conversationHistory.length > 0) {
        session.conversationHistory[session.conversationHistory.length - 1].aiMessage = `发生错误: ${error.message}`;
        saveChatSessions();
        renderConversationHistory(session.conversationHistory);
      } else {
        addMessage(`发生错误: ${error.message}`, false);
      }
    }
  }

  // 发送按钮点击事件
  sendButton.addEventListener('click', () => {
    const message = userInput.value.trim();
    if (message) {
      sendMessage(message);
      userInput.value = '';
    }
  });

  // 按Enter键发送消息
  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendButton.click();
    }
  });

  // 新建聊天按钮事件
  newChatButton.addEventListener('click', () => {
    createNewChatSession();
  });

  // 初始化应用
  function initializeApp() {
    loadChatSessions();
    
    if (chatSessions.length === 0) {
      // 如果没有聊天会话，创建一个新的
      createNewChatSession();
    } else {
      // 切换到最新的聊天会话
      currentSessionId = chatSessions[0].id;
      renderChatHistory();
      const session = getCurrentSession();
      if (session) {
        renderConversationHistory(session.conversationHistory);
      }
    }
  }

  // 启动应用
  initializeApp();
});
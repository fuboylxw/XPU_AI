<template>
  <BaseLayout :mode="'chat'" :is-dark="isDark" :user-menu-options="userMenuOptions" :username="displayUsername" :collapsed="sidebarCollapsed" @toggle-theme="toggleTheme" @set-mode="onSetMode" @app-download="showAppModal = true" @go-home="onGoHome" @school="onSchool" @user-menu-click="handleUserMenuClick">
    <template #sidebar>
      <div v-if="!sidebarCollapsed">
        <div class="sidebar-header">
          <div class="header-buttons">
            <button class="new-chat-btn" @click="createNewChat">新建对话</button>
            <button class="collapse-sidebar-btn" @click="toggleSidebar" title="收起侧边栏"><Icon type="menu-fold" :size="18" /></button>
          </div>
        </div>
        <div class="conversation-list">
          <div v-for="conv in conversations" :key="conv.id" class="conversation-item" :class="{ active: conv.id === currentConversation }">
            <div class="conv-content" @click="selectConversation(conv.id)">
              <div class="conv-title">{{ conv.title }}</div>
              <div class="conv-time">{{ conv.time }}</div>
            </div>
            <div class="conv-actions">
              <t-dropdown :options="convMoreOptions" trigger="click" :popup-props="{ attach: 'body', overlayClassName: 'task-dropdown-popup' }" @click="onConvMenuClick($event, conv.id)" placement="bottom-right">
                <button class="more-btn" title="更多">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <g id="canmore">
                      <g id="canstroke1">
                        <path d="M11.5 4H12.5V5H11.5V4ZM11.5 11.5H12.5V12.5H11.5V11.5ZM11.5 19H12.5V20H11.5V19Z" stroke-linecap="square" id="stroke1" stroke-width="2" stroke="currentColor"/>
                      </g>
                    </g>
                  </svg>
                </button>
              </t-dropdown>
              <t-popconfirm
                :visible="deleteConfirmId === conv.id"
                content="确定删除该对话？"
                theme="warning"
                placement="right-top"
                :popup-props="{ attach: 'body', overlayClassName: 'conv-popconfirm' }"
                @confirm="confirmDelete(conv.id)"
                @cancel="deleteConfirmId = null"
              >
                <span class="pop-anchor"></span>
              </t-popconfirm>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="sidebar-collapsed">
        <button class="sidebar-icon-btn" @click="toggleSidebar" title="展开侧边栏"><Icon type="menu" :size="20" /></button>
        <button class="sidebar-icon-btn" @click="createNewChat" title="新建对话"><Icon type="plus" :size="20" /></button>
      </div>
    </template>
    <div class="chat-container">
      <div class="chat-main">
        <div class="chat-scroll" ref="chatScroll">
          <div class="message-list" ref="chatArea">
            <div v-if="messages && messages.length === 0" class="empty-state">
              <div class="welcome-message"><h2>织语，知你所需。</h2></div>
              <div class="quick-actions">
                <button class="quick-btn" @click="sendQuickMessage('学校概况')">学校概况</button>
                <button class="quick-btn" @click="sendQuickMessage('招生录取')">招生录取</button>
                <button class="quick-btn" @click="sendQuickMessage('学科专业')">学科专业</button>
                <button class="quick-btn" @click="sendQuickMessage('教务服务')">教务服务</button>
                <button class="quick-btn" @click="sendQuickMessage('学生资助')">学生资助</button>
                <button class="quick-btn" @click="sendQuickMessage('就业信息')">就业信息</button>
                <button class="quick-btn" @click="sendQuickMessage('赛事信息')">赛事信息</button>
                <button class="quick-btn" @click="sendQuickMessage('科研平台')">科研平台</button>
              </div>
            </div>
            <div v-for="m in messages" :key="m.id" class="msg-wrapper">
              <div class="msg" :class="m.type">
                <div v-if="m.content" class="msg-content" v-html="renderMarkdown(m.content)"></div>
                <div v-else-if="m.fileInfo" class="file-row">{{ m.fileInfo.name }} · {{ (m.fileInfo.size/1024).toFixed(1) }}KB</div>
                <div v-if="m.type==='assistant' && m.streaming" class="streaming-indicator">
                  <span class="typing-dots"><span></span><span></span><span></span></span>
                  <span class="streaming-text">正在生成回答...</span>
                </div>
              </div>
              <div class="message-actions-external" v-if="m.type==='user'">
                <button class="action-btn edit-btn" @click="editMessage(m)" title="编辑消息"><Icon type="edit" :size="16" :fill-color="'transparent'" :stroke-color="'currentColor'" :stroke-width="2" /></button>
                <button class="action-btn copy-btn" @click="copyMessage(m.content)" title="复制消息"><Icon type="copy" :size="16" :fill-color="'transparent'" :stroke-color="'currentColor'" :stroke-width="2" /></button>
              </div>
              <div class="message-actions-external" v-else-if="m.type==='assistant' && !m.streaming">
                <button class="action-btn copy-btn" @click="copyMessage(m.content)" title="复制消息"><Icon type="copy" :size="16" :fill-color="'transparent'" :stroke-color="'currentColor'" :stroke-width="2" /></button>
              </div>
            </div>
            <div v-if="isDragOver || showDragOverlay" class="drag-overlay" @click="showDragOverlay = false">
              <div class="drag-content" @click.stop>
                <div class="drag-icon"><Icon type="file-default" :size="64" /></div>
                <h3>拖拽文件到此处上传</h3>
                <p>支持 TXT、PDF、DOC、DOCX、JPG、PNG、GIF、MP3、MP4、WAV 格式</p>
                <p>文件大小限制：50MB</p>
                <button class="drag-close" @click="showDragOverlay = false">关闭</button>
              </div>
            </div>
          </div>
        </div>
        <div class="chat-input">
          <div class="input-wrap">
            <textarea ref="messageInput" v-model="inputMessage" class="input" rows="1" @keydown.enter.prevent="handleEnterKey" @input="adjustTextareaHeight" placeholder="输入您的问题，让织语为您解答"></textarea>
            <div class="input-actions">
              <button class="icon-btn web-search-btn" :class="{ 'web-search-on': isWebSearchEnabled }" @click="isWebSearchEnabled = !isWebSearchEnabled" title="联网搜索"><Icon type="jump-icon" :size="18" /></button>
              <button class="icon-btn" @click="handleFileUpload" title="文件上传"><Icon type="file-default" :size="18" /></button>
              <button class="icon-btn voice-btn" :class="{ 'voice-on': isRecording }" @click="handleVoiceInput" title="语音输入"><Icon type="mic" :size="18" /></button>
              <button class="icon-btn" @click="openCall" title="电话输入"><Icon type="call" :size="18" /></button>
              <button class="send-btn" @click="sendMessage" :disabled="!canSend" title="发送"><Icon type="send" :size="18" /></button>
              <button class="stop-btn" v-if="isStreaming" @click="stopStreaming" title="停止"><Icon type="stop" :size="18" /></button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <CallModal 
      v-if="showCallModal"
      :visible="showCallModal"
      :call-status="callStatus"
      :call-duration="callDuration"
      :is-muted="isMuted"
      :is-speaker-on="isSpeakerOn"
      @hang-up="hangUpCall"
      @mute-toggle="handleMuteToggle"
      @speaker-toggle="handleSpeakerToggle"
    />

    <div v-if="showAppModal" class="modal-overlay" @click="showAppModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>应用下载</h3>
          <button class="close-btn" @click="showAppModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="app-clients">
            <div class="client-item"><img src="/src/pic/ios.png" alt="iOS客户端二维码" class="app-qr-image" /><p>iOS客户端</p></div>
            <div class="client-item"><img src="/src/pic/android.png" alt="安卓客户端二维码" class="app-qr-image" /><p>安卓客户端</p></div>
          </div>
        </div>
      </div>
    </div>
    <div class="voice-alerts-container">
      <t-message v-if="showVoiceSuccess" theme="success" :content="voiceSuccessMessage" :close-btn="true" @close="showVoiceSuccess = false" />
      <t-message v-if="showVoiceError" theme="error" :content="voiceErrorMessage" :close-btn="true" @close="showVoiceError = false" />
    </div>
  </BaseLayout>
</template>

<script>
import BaseLayout from '../layout/BaseLayout.vue'
import CallModal from './CallModal.vue'
import { h } from 'vue'
import Icon from '../common/Icon.vue'
import { authStore } from '../../store/auth.js'

export default {
  name: 'ChatMode',
  components: { BaseLayout, CallModal, Icon },
  emits: ['switch-mode'],
  data() {
    return {
      isDark: false,
      sidebarCollapsed: false,
      inputMessage: '',
      messages: [],
      uploadedFiles: [],
      isStreaming: false,
      currentStreamController: null,
      currentConversation: null,
      apiBaseUrl: 'http://localhost:8000/api',
      isWebSearchEnabled: false,
      conversations: [],
      showAppModal: false,
      showCallModal: false,
      callStatus: 'connecting',
      callDuration: 0,
      isMuted: false,
      isSpeakerOn: false,
      isRecording: false,
      mediaRecorder: null,
      audioChunks: [],
      callStatusTimerId: null,
      showVoiceSuccess: false,
      voiceSuccessMessage: '',
      showVoiceError: false,
      voiceErrorMessage: '',
      isDragOver: false,
      showDragOverlay: false,
      dragCounter: 0,
      userMenuOptions: [
        {
          content: '个人中心',
          value: 'profile',
          prefixIcon: () => h(Icon, { type: 'user-circle-icon', size: 16 })
        },
        {
          content: '设置',
          value: 'settings',
          prefixIcon: () => h(Icon, { type: 'settings', size: 16 })
        },
        {
          content: '退出登录',
          value: 'logout',
          prefixIcon: () => h(Icon, { type: 'rollback-icon', size: 16 })
        }
      ],
      convMoreOptions: [
        { content: () => h('span', { style: 'color:#333' }, '重命名'), value: 'rename', prefixIcon: () => h(Icon, { type: 'rename-square', size: 16, strokeColor: '#333' }) },
        { content: () => h('span', { style: 'color:#ef4444' }, '删除'), value: 'delete', prefixIcon: () => h(Icon, { type: 'delete-bin-square', size: 16, strokeColor: '#ef4444' }) }
      ],
      deleteConfirmId: null
    }
  },
  computed: {
    displayUsername() {
      const u = authStore.user || {}
      return u.nickname || u.username || ''
    },
    canSend() {
      const hasText = !!(this.inputMessage && this.inputMessage.trim())
      const hasFiles = (this.uploadedFiles || []).length > 0
      return hasText || hasFiles
    }
  },
  mounted() { this.initTheme(); this.loadConversations(); this.addDragListeners() },
  methods: {
    onSetMode(m) { try { const current = this.$route.path; if (m === 'chat' && current !== '/chat') { this.$router.push('/chat') } else if (m === 'work' && current !== '/work') { this.$router.push('/work') } } catch (_) {} },
    onSchool() { try { window.location.href = '/' } catch (e) {} },
    onConvMenuClick(e, id) { const v = e && e.value; if (v === 'rename') { this.renameConversation(id) } else if (v === 'delete') { this.deleteConfirmId = id } },
    confirmDelete(id) { this.deleteConfirmId = null; this.deleteConversation(id) },
    handleUserMenuClick(e) {
      const v = e && e.value
      if (v === 'logout') { try { localStorage.clear() } catch (err) {} location.reload() }
      if (v === 'profile') { try { window.location.href = '/profile' } catch (err) {} }
      if (v === 'settings') { try { window.location.href = '/settings' } catch (err) {} }
    },
    async createNewChat() {
      try {
        const resp = await fetch(`${this.apiBaseUrl}/conversations/create/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: `新对话 ${new Date().toLocaleString()}`, user_id: 'test_user' }) })
        if (resp.ok) {
          const c = await resp.json()
          this.currentConversation = c.conversation_id
          this.messages = []
          this.conversations.unshift({ id: c.conversation_id, title: c.title, time: '刚刚' })
        }
      } catch (e) {}
    },
    async deleteConversation(id) {
      if (this.conversations.length <= 1) return
      try { const resp = await fetch(`${this.apiBaseUrl}/conversations/${id}/delete/`, { method: 'DELETE', headers: { 'Content-Type': 'application/json' } }); if (resp.ok) { this.conversations = this.conversations.filter(c => c.id !== id); if (this.currentConversation === id) { if (this.conversations.length > 0) { this.selectConversation(this.conversations[0].id) } else { this.currentConversation = null; this.messages = []; await this.createNewChat() } } } } catch (e) {}
    },
    async renameConversation(id) {
      try { const conv = this.conversations.find(c => c.id === id); const name = prompt('重命名对话', conv ? conv.title : ''); if (!name || !name.trim()) return; const resp = await fetch(`${this.apiBaseUrl}/conversations/${encodeURIComponent(id)}/title/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: name.trim() }) }); if (resp.ok) { const data = await resp.json(); const idx = this.conversations.findIndex(c => c.id === id); if (idx >= 0) this.conversations[idx].title = data.title } } catch (e) {}
    },
    async loadConversations() {
      try {
        const response = await fetch(`${this.apiBaseUrl}/conversations/`)
        if (response.ok) {
          const data = await response.json()
          this.conversations = data.map(conv => ({ id: conv.conversation_id, title: conv.title, time: this.formatConversationTime(conv.created), created: conv.created, status: conv.status }))
          if (this.conversations.length > 0 && !this.currentConversation) { await this.selectConversation(this.conversations[0].id) }
        }
      } catch (e) {}
    },
    async selectConversation(id) { this.currentConversation = id; await this.loadConversationHistory(id) },
    async sendMessage() {
      if (!this.inputMessage.trim() && this.uploadedFiles.length === 0) return
      if (!this.currentConversation) await this.createNewChat()
      
      // 处理文件上传
      const files = [...this.uploadedFiles]
      for (const f of files) {
        this.messages.push({ 
          id: Date.now()+Math.random(), 
          type: 'user', 
          sender: 'USER', 
          fileInfo: { name: f.name, size: f.size }, 
          time: this.formatTime(new Date()) 
        })
      }
      
      // 添加用户消息
      const hasText = !!this.inputMessage.trim()
      if (hasText) {
        const userMessage = { 
          id: Date.now(), 
          type: 'user', 
          sender: 'USER', 
          content: this.inputMessage, 
          time: this.formatTime(new Date()) 
        }
        this.messages.push(userMessage)
      }
      
      const messageContent = hasText ? this.inputMessage : '请根据已上传的内容回答'
      this.inputMessage = ''
      this.scrollToBottom()
      this.adjustTextareaHeight()
      
      // 先上传文件
      for (const f of files) {
        try {
          const form = new FormData()
          form.append('conversation_id', this.currentConversation)
          form.append('file', f)
          await fetch(`${this.apiBaseUrl}/upload/file`, { method: 'POST', body: form })
        } catch (e) {
          console.error('文件上传失败:', e)
        }
      }
      this.uploadedFiles = []
      
      // 创建助手消息（流式展示）
      const assistantMessage = { 
        id: Date.now()+1, 
        type: 'assistant', 
        sender: 'assistant', 
        content: '', 
        time: this.formatTime(new Date()), 
        streaming: true 
      }
      this.messages.push(assistantMessage)
      this.scrollToBottom()
      
      // 设置流式传输状态
      this.isStreaming = true
      if (this.showCallModal) this.callStatus = 'speaking'

      try {
        // 使用fetch的ReadableStream处理SSE流式响应
        const eventSourceUrl = `${this.apiBaseUrl}/chat/stream/`
        
        const response = await fetch(eventSourceUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            conversation_id: this.currentConversation,
            message: messageContent,
            user_id: 'test_user',
            use_web_search: this.isWebSearchEnabled
          })
        })
        
        if (response.ok) {
          // 使用ReadableStream实时读取SSE数据流
          const reader = response.body.getReader()
          this.currentStreamController = reader
          const decoder = new TextDecoder('utf-8')
          let buffer = '' // 缓存未完整的数据块
          
          while (true) {
            // 检查是否被用户停止
            if (!this.isStreaming) {
              await reader.cancel()
              break
            }
            
            const { done, value } = await reader.read()
            if (done) {
              // 流结束，处理缓存中剩余的数据
              if (buffer.trim()) {
                this.processSSELine(buffer, assistantMessage)
              }
              break
            }
            
            // 解码数据块并添加到缓存
            buffer += decoder.decode(value, { stream: true })
            
            // 按行分割并处理完整的行
            const lines = buffer.split('\n')
            // 保留最后一行（可能是未完整的）
            buffer = lines.pop() || ''
            
            // 处理每一行完整的SSE数据
            for (const line of lines) {
              if (line.trim()) {
                this.processSSELine(line, assistantMessage)
              }
            }
            
            // 实时滚动到底部
            this.scrollToBottom()
          }
          
          // 流结束后确保状态正确
          if (this.isStreaming) {
            assistantMessage.streaming = false
            this.isStreaming = false
            this.currentStreamController = null
            if (this.showCallModal) this.callStatus = 'listening'
          }
        } else {
          console.error('发送消息失败:', response.status)
          assistantMessage.content = '抱歉，发送消息时出现错误，请稍后重试。'
          assistantMessage.streaming = false
          this.isStreaming = false
          this.currentStreamController = null
          if (this.showCallModal) this.callStatus = 'listening'
        }
      } catch (error) {
        console.error('发送消息出错:', error)
        assistantMessage.content = '网络连接错误，请检查网络后重试。'
        assistantMessage.streaming = false
        this.isStreaming = false
        this.currentStreamController = null
        if (this.showCallModal) this.callStatus = 'listening'
      }
    },
    sendQuickMessage(content) { this.inputMessage = content; this.sendMessage() },
    processSSELine(line, assistantMessage) {
      // 处理SSE数据行
      if (line.startsWith('data: ')) {
        try {
          const jsonStr = line.slice(6).trim()
          if (!jsonStr) return
          
          const data = JSON.parse(jsonStr)
          
          if (data.type === 'chunk' && data.chunk) {
            // 实时追加内容到助手消息，实现流式展示
            assistantMessage.content += data.chunk
            // 使用Vue3的响应式系统自动更新DOM
            this.$forceUpdate()
          } else if (data.type === 'done') {
            // 流式传输完成
            assistantMessage.streaming = false
            this.isStreaming = false
            this.currentStreamController = null
            if (this.showCallModal) this.callStatus = 'listening'
            console.log('流式传输完成，总共接收:', assistantMessage.content.length, '个字符')
          } else if (data.type === 'error') {
            // 处理错误
            assistantMessage.content = data.error || '抱歉，处理消息时出现错误。'
            assistantMessage.streaming = false
            this.isStreaming = false
            this.currentStreamController = null
            if (this.showCallModal) this.callStatus = 'listening'
          }
        } catch (parseError) {
          console.warn('解析SSE数据失败:', parseError, '原始数据:', line)
        }
      }
    },
    async loadConversationHistory(conversationId) {
      try {
        const response = await fetch(`${this.apiBaseUrl}/conversations/${conversationId}/messages/`)
        if (response.ok) {
          const data = await response.json()
          const messages = Array.isArray(data) ? data : (data.value || [])
          if (messages.length > 0) {
            this.messages = []
            messages.forEach(msg => {
              if (msg.question) { this.messages.push({ id: msg.id + '_q', type: 'user', sender: 'USER', content: msg.question, time: this.formatTime(new Date(msg.created_at)) }) }
              if (msg.answer) { this.messages.push({ id: msg.id + '_a', type: 'assistant', sender: 'assistant', content: msg.answer, time: this.formatTime(new Date(msg.created_at)) }) }
            })
          } else { this.messages = [] }
          this.scrollToBottom()
        } else { this.messages = [] }
      } catch (e) { this.messages = [] }
    },
    stopStreaming() {
      if (this.isStreaming && this.currentStreamController) {
        console.log('用户手动停止流式传输')
        
        // 1. 立即设置停止标志，阻止后续数据处理
        this.isStreaming = false
        
        // 2. 取消ReadableStream读取
        try {
          this.currentStreamController.cancel()
          console.log('ReadableStream已取消')
        } catch (error) {
          console.warn('停止流式传输时出现错误:', error)
        }
        
        // 3. 清空控制器引用
        this.currentStreamController = null
        
        // 4. 找到最后一个流式传输的消息并标记为完成
        const lastMessage = this.messages[this.messages.length - 1]
        if (lastMessage && lastMessage.streaming) {
          lastMessage.streaming = false
          // 如果内容为空，显示提示信息
          if (!lastMessage.content || !lastMessage.content.trim()) {
            lastMessage.content = '回答已停止。'
          }
          console.log('已接收内容长度:', lastMessage.content.length, '个字符')
        }
        
        // 5. 重置语音通话状态（如果启用）
        if (this.showCallModal) {
          this.callStatus = 'listening'
        }
        
        // 6. 强制更新界面
        this.$forceUpdate()
      }
    },
    handleEnterKey(e) { if (e.shiftKey) return; this.sendMessage() },
    adjustTextareaHeight() { this.$nextTick(() => { const t = this.$refs.messageInput; if (t) { t.style.height = 'auto'; t.style.height = Math.min(t.scrollHeight, 120) + 'px' } }) },
    scrollToBottom() { this.$nextTick(() => { const a = this.$refs.chatArea; if (a) { a.scrollTop = a.scrollHeight } }) },
    formatTime(d) { return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) },
    formatConversationTime(dateString) {
      const date = new Date(dateString)
      const now = new Date()
      const diffTime = Math.abs(now - date)
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      if (diffDays === 1) { return '今天' } else if (diffDays === 2) { return '昨天' } else if (diffDays <= 7) { return `${diffDays}天前` } else { return date.toLocaleDateString('zh-CN') }
    },
    toggleTheme() { this.isDark = !this.isDark; document.body.classList.toggle('dark', this.isDark); document.documentElement.setAttribute('theme-mode', this.isDark ? 'dark' : 'light'); localStorage.setItem('theme', this.isDark ? 'dark' : 'light') },
    initTheme() { const saved = localStorage.getItem('theme'); this.isDark = saved === 'dark'; document.body.classList.toggle('dark', this.isDark); document.documentElement.setAttribute('theme-mode', this.isDark ? 'dark' : 'light') },
    toggleSidebar() { this.sidebarCollapsed = !this.sidebarCollapsed },
    openCall() {
      this.showCallModal = true
      this.callStatus = 'connecting'
      this.callDuration = 0
      if (this.callStatusTimerId) { clearTimeout(this.callStatusTimerId); this.callStatusTimerId = null }
      this.callStatusTimerId = setTimeout(() => { if (this.showCallModal) this.callStatus = 'listening' }, 800)
    },
    hangUpCall() {
      this.callStatus = 'ending'
      this.showCallModal = false
      if (this.callStatusTimerId) { clearTimeout(this.callStatusTimerId); this.callStatusTimerId = null }
    },
    handleMuteToggle(v) { this.isMuted = v },
    handleSpeakerToggle(v) { this.isSpeakerOn = v },
    handleFileUpload() {
      const input = document.createElement('input')
      input.type = 'file'
      input.multiple = true
      input.accept = '.txt,.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif,.mp3,.mp4,.wav'
      input.onchange = e => {
        const files = e.target && e.target.files
        if (files && files.length) {
          for (let i = 0; i < files.length; i++) {
            const f = files[i]
            if (f.size <= 50 * 1024 * 1024) this.uploadedFiles.push(f)
          }
        }
        this.showDragOverlay = false
      }
      this.showDragOverlay = true
      input.click()
    },
    async handleVoiceInput() {
      // 如果正在录音，则停止录制并释放麦克风资源
      if (this.isRecording) {
        try {
          if (this.mediaRecorder) {
            const stream = this.mediaRecorder.stream
            try { this.mediaRecorder.stop() } catch (_) {}
            if (stream && stream.getTracks) {
              stream.getTracks().forEach(t => { try { t.stop() } catch (_) {} })
            }
            this.mediaRecorder = null
          }
        } catch (e) {}
        this.isRecording = false
      } else {
        // 开始录音并持有媒体流，onstop 中只做数据处理，释放在上面的关闭分支里统一处理
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
          this.audioChunks = []
          this.mediaRecorder = new MediaRecorder(stream)
          this.mediaRecorder.ondataavailable = e => { if (e.data && e.data.size > 0) this.audioChunks.push(e.data) }
          this.mediaRecorder.onstop = async () => {
            try {
              const blob = new Blob(this.audioChunks, { type: 'audio/webm' })
              this.showVoiceSuccess = true
              this.voiceSuccessMessage = '语音已录制'
              const file = new File([blob], `voice-${Date.now()}.webm`, { type: 'audio/webm' })
              this.uploadedFiles.push(file)
            } catch (err) {}
          }
          this.mediaRecorder.start()
          this.isRecording = true
        } catch (e) {
          this.showVoiceError = true
          this.voiceErrorMessage = '无法访问麦克风'
        }
      }
    },
    addDragListeners() {
      const onDragOver = e => { e.preventDefault(); this.isDragOver = true; this.dragCounter++ }
      const onDragLeave = e => { e.preventDefault(); this.dragCounter = Math.max(0, this.dragCounter - 1); if (this.dragCounter === 0) this.isDragOver = false }
      const onDrop = e => { e.preventDefault(); this.isDragOver = false; this.dragCounter = 0; const files = e.dataTransfer && e.dataTransfer.files; if (files && files.length) { for (let i = 0; i < files.length; i++) { const f = files[i]; if (f.size <= 50 * 1024 * 1024) this.uploadedFiles.push(f) } } }
      document.addEventListener('dragover', onDragOver)
      document.addEventListener('dragleave', onDragLeave)
      document.addEventListener('drop', onDrop)
      this._dragHandlers = { onDragOver, onDragLeave, onDrop }
    },
    removeDragListeners() {
      if (this._dragHandlers) {
        document.removeEventListener('dragover', this._dragHandlers.onDragOver)
        document.removeEventListener('dragleave', this._dragHandlers.onDragLeave)
        document.removeEventListener('drop', this._dragHandlers.onDrop)
        this._dragHandlers = null
      }
    },
    onGoHome() {},
    editMessage(message) { try { const newText = prompt('编辑消息', message && message.content ? message.content : ''); if (newText != null) { const t = String(newText).trim(); if (t) message.content = t } } catch (e) {} },
    async copyMessage(content) { try { await navigator.clipboard.writeText(String(content || '')) } catch (e) {} },
    escapeHtml(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') },
    renderMarkdown(text) {
      const src = String(text || '')
      const escaped = this.escapeHtml(src)
      const withTables = (input => {
        const lines = input.split('\n')
        let out = []
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i]
          if (line.trim().startsWith('|')) {
            const block = []
            const start = i
            while (i < lines.length && lines[i].trim().startsWith('|')) { block.push(lines[i]); i++ }
            if (block.length >= 2 && /^\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(block[1].trim())) {
              const headerCells = block[0].split('|').slice(1, -1).map(s => s.trim())
              const rows = []
              for (let r = 2; r < block.length; r++) {
                const cells = block[r].split('|').slice(1, -1).map(s => s.trim())
                rows.push(cells)
              }
              let html = '<table class="md-table"><thead><tr>'
              for (const h of headerCells) html += `<th>${h}</th>`
              html += '</tr></thead><tbody>'
              for (const row of rows) html += '<tr>' + row.map(c => `<td>${c}</td>`).join('') + '</tr>'
              html += '</tbody></table>'
              out.push(html)
            } else {
              for (const l of block) out.push(l)
            }
            i--
          } else {
            out.push(line)
          }
        }
        return out.join('\n')
      })(escaped)
      const fenced = withTables.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code}</code></pre>`)
      const inlineCode = fenced.replace(/`([^`]+)`/g, '<code>$1</code>')
      const bold = inlineCode.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      const italic = bold.replace(/\*([^*]+)\*/g, '<em>$1</em>')
      const links = italic.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      const tasks = links.replace(/^[-*]\s+\[(x|X| )\]\s+(.+)$/gm, (m, chk, label) => `<div class="md-task"><input type="checkbox" ${chk.trim().toLowerCase()==='x' ? 'checked' : ''} disabled> ${label}</div>`)
      const headings = tasks.replace(/^#{1}\s([^\n]+)$/gm, '<h1>$1</h1>').replace(/^#{2}\s([^\n]+)$/gm, '<h2>$1</h2>').replace(/^#{3}\s([^\n]+)$/gm, '<h3>$1</h3>')
      const paragraphs = headings.replace(/(^|\n)([^\n<][^\n]*)/g, (m, p1, p2) => `${p1}<p>${p2}</p>`)
      return paragraphs
    }
  }
}
</script>

<style scoped>
.chat-container { display: grid; grid-template-columns: 1fr; height: 100%; }
.chat-main { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.chat-scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 40px 24px; background: var(--surface-2); color: var(--text-1); position: relative; }
.chat-scroll::-webkit-scrollbar { width: 6px; }
.chat-scroll::-webkit-scrollbar-track { background: transparent; }
.chat-scroll::-webkit-scrollbar-thumb { background: rgba(74,144,226,0.3); border-radius: 3px; }
.chat-scroll::-webkit-scrollbar-thumb:hover { background: rgba(74,144,226,0.5); }
.chat-input { border-top: 1px solid var(--border-1); padding: 16px 12px; background: var(--surface-2); display: flex; justify-content: center; flex-shrink: 0; }
.chat-input :deep(.input-wrap) { width: 100%; max-width: 720px; }
.message-list { display: flex; flex-direction: column; gap: 12px; width: 100%; height: 100%; }
.msg-wrapper { display: flex; flex-direction: column; gap: 8px; align-items: flex-end; position: relative; }
.msg { position: relative; display: inline-flex; flex-direction: column; }
.message-actions-external { display: flex; gap: 8px; align-items: center; }
.msg-wrapper:has(.msg.assistant) { align-items: flex-start; }
.msg-wrapper:has(.msg.assistant) .message-actions-external { justify-content: flex-start; }
.action-btn { width: 28px; height: 28px; border: none; border-radius: 8px; background: transparent; color: var(--text-2); display: flex; align-items: center; justify-content: center; cursor: pointer; }
.action-btn:hover { background: rgba(74,144,226,0.1); color: var(--accent-1); }
.streaming-indicator { display: inline-flex; align-items: center; gap: 8px; color: var(--text-2); }
.typing-dots { display: inline-flex; gap: 3px; }
.typing-dots span { width: 6px; height: 6px; background: var(--text-2); border-radius: 50%; animation: blink 1.2s infinite ease-in-out; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%, 80%, 100% { opacity: 0.2 } 40% { opacity: 1 } }
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; min-height: 400px; }
.welcome-message { margin-bottom: 24px; text-align: center; }
.welcome-message h2 { font-size: 28px; font-weight: 600; color: var(--accent-1); margin: 0; letter-spacing: -0.5px; }
.quick-actions { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; max-width: 700px; }
.quick-btn { height: 36px; padding: 0 16px; border: 1px solid rgba(229,229,229,0.8); border-radius: 18px; background: rgba(255,255,255,0.7); color: var(--text-1); cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease; backdrop-filter: blur(10px); }
.quick-btn:hover { background: rgba(74,144,226,0.1); border-color: var(--accent-1); color: var(--accent-1); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(74,144,226,0.15); }
.drag-overlay { position: absolute; inset: 0; background: rgba(255,255,255,0.85); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 10; }
.drag-content { text-align: center; color: var(--text-1); }
.drag-icon { display: inline-flex; align-items: center; justify-content: center; width: 80px; height: 80px; border-radius: 16px; background: rgba(229,229,229,0.6); margin-bottom: 12px; }
.drag-close { margin-top: 12px; height: 30px; padding: 0 12px; border: none; border-radius: 8px; background: var(--accent-1); color: #fff; cursor: pointer; }
.msg { border-radius: 14px; padding: 12px; background: rgba(255,255,255,0.95); box-shadow: 0 2px 8px rgba(0,0,0,0.06); max-width: 72%; }
.msg.user { align-self: flex-end; background: linear-gradient(180deg, rgba(239,246,255,0.92) 0%, rgba(230,240,255,0.92) 100%); border-top-right-radius: 6px; }
.msg.assistant { align-self: flex-start; background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(249,250,251,0.95) 100%); border-top-left-radius: 6px; }
.msg-content { font-size: 14px; line-height: 1.7; color: #333; }
.msg-content h1, .msg-content h2, .msg-content h3 { margin: 10px 0; font-weight: 600; }
.msg-content pre { background: #0f172a0d; border-radius: 10px; padding: 10px; overflow: auto; }
.msg-content code { background: rgba(229,229,229,0.4); padding: 0 4px; border-radius: 4px; }
.msg-content a { color: #2563eb; text-decoration: none; }
.msg-content a:hover { text-decoration: underline; }
.md-table { width: 100%; border-collapse: collapse; margin: 8px 0; }
.md-table th, .md-table td { border: 1px solid rgba(229,229,229,0.7); padding: 8px; text-align: left; font-size: 13px; }
.md-task { display: flex; align-items: center; gap: 8px; font-size: 14px; }
.dark .msg.user { background: linear-gradient(180deg, rgba(36,48,74,0.6) 0%, rgba(22,33,54,0.6) 100%); color: #e5e7eb; }
.dark .msg.assistant { background: linear-gradient(180deg, rgba(30,41,59,0.6) 0%, rgba(15,23,42,0.6) 100%); color: #e5e7eb; }
.dark .msg-content { color: #e5e7eb; }
.dark .msg-content pre { background: rgba(2,6,23,0.6); }
.dark .msg-content code { background: rgba(148,163,184,0.2); }
.dark .msg-content a { color: #93c5fd; }
.dark .md-table th, .dark .md-table td { border-color: rgba(148,163,184,0.3); }
.file-row { margin-top: 6px; font-size: 13px; color: #666; }
.input-wrap { position: relative; }
.input-actions { position: absolute; right: 8px; bottom: 8px; display: flex; gap: 8px; align-items: center; }
.conversation-list { overflow-y: auto; padding: 8px 12px; }
.sidebar-header { padding: 8px 12px; }
.header-buttons { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.new-chat-btn { height: 32px; padding: 0 10px; font-size: 13px; border: none; border-radius: 8px; background: var(--accent-1); color: #fff; cursor: pointer; }
.new-chat-btn:hover { background: var(--accent-2); }
.collapse-sidebar-btn { width: 32px; height: 32px; border: none; background: transparent; color: var(--text-2); display: flex; align-items: center; justify-content: center; cursor: pointer; }
.collapse-sidebar-btn:hover { color: var(--accent-1); }
.sidebar-collapsed { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 8px 0; }
.sidebar-icon-btn { width: 40px; height: 40px; border: none; background: transparent; color: var(--text-2); display: flex; align-items: center; justify-content: center; border-radius: 8px; cursor: pointer; }
.sidebar-icon-btn:hover { background: rgba(74,144,226,0.1); color: var(--accent-1); }
.conversation-item { display: grid; grid-template-columns: 1fr auto; padding: 10px 12px; margin: 4px 0; width: 100%; cursor: pointer; }
.conversation-item.active { background: rgba(74,144,226,0.1); }
.conv-content { min-width: 0; }
.conv-title { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-time { font-size: 12px; color: var(--text-2); }
.conv-actions { display: flex; gap: 6px; align-items: center; position: relative; z-index: 2; }
.more-btn { width: 28px; height: 28px; border: none; border-radius: 6px; background: transparent; display: flex; align-items: center; justify-content: center; color: #666; cursor: pointer; opacity: 0; transform: scale(0.9); pointer-events: none; transition: all 0.2s ease; }
.conversation-item:hover .more-btn { opacity: 1; transform: scale(1); pointer-events: auto; }
.more-btn:hover { background: rgba(74,144,226,0.1); color: #4A90E2; }
.conversation-item::before { pointer-events: none; }
.pop-anchor { display: inline-block; width: 1px; height: 1px; }
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 9998; }
.modal-content { background: #fff; border-radius: 12px; width: 420px; padding: 12px; }
/* 全局深色模式 - 不使用 scoped 以支持 body.dark */
@supports selector(:has(*)) {
  :global(body.dark) .modal-content { background: rgba(30,41,59,0.95) !important; color: #e5e7eb !important; }
}
.modal-header { display: flex; align-items: center; justify-content: space-between; }
.app-clients { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.client-item { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.close-btn { border: none; background: transparent; font-size: 18px; }
.input { width: 100%; resize: none; border: 1px solid var(--border-1); border-radius: 12px; padding: 12px 12px 46px 12px; background: var(--surface-2); color: var(--text-1); font-size: 14px; line-height: 1.7; caret-color: var(--accent-1); font-family: 'Microsoft YaHei','微软雅黑',system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial; overflow-y: auto; }
.input::-webkit-scrollbar { width: 6px; }
.input::-webkit-scrollbar-track { background: transparent; border-radius: 3px; }
.input::-webkit-scrollbar-thumb { background: rgba(74,144,226,0.3); border-radius: 3px; }
.input::-webkit-scrollbar-thumb:hover { background: rgba(74,144,226,0.5); }
.input:focus { outline: none; border-color: var(--accent-1); box-shadow: 0 0 0 3px rgba(74,144,226,0.20); background: #fff; transition: box-shadow 0.2s ease, border-color 0.2s ease; }
.input::placeholder { color: var(--text-2); font-family: 'Microsoft YaHei','微软雅黑',system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial; }
.dark .input { background: rgba(30,41,59,0.6); color: #e5e7eb; border-color: rgba(148,163,184,0.2); }
.dark .input:focus { background: rgba(30,41,59,0.8) !important; border-color: var(--accent-1); }
.dark .input::placeholder { color: rgba(229,229,229,0.4); }
.dark .input::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); }
.dark .input::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.3); }
.icon-btn { width: 32px; height: 32px; border: none; background: transparent; color: var(--text-2); display: flex; align-items: center; justify-content: center; cursor: pointer; transition: color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease; }
.icon-btn:hover { color: var(--accent-1); }
.web-search-btn.web-search-on {
  background: rgba(37, 99, 235, 0.12);
  color: #2563eb;
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.4);
  border-radius: 999px;
}
.dark .web-search-btn.web-search-on {
  background: rgba(96, 165, 250, 0.18);
  color: #bfdbfe;
  box-shadow: 0 0 0 1px rgba(191, 219, 254, 0.5);
}
.voice-btn.voice-on {
  background: rgba(220, 38, 38, 0.12);
  color: #dc2626;
  box-shadow: 0 0 0 1px rgba(220, 38, 38, 0.45);
  border-radius: 999px;
}
.dark .voice-btn.voice-on {
  background: rgba(248, 113, 113, 0.2);
  color: #fecaca;
  box-shadow: 0 0 0 1px rgba(254, 202, 202, 0.55);
}
.send-btn, .stop-btn { width: 36px; height: 32px; padding: 0; border: none; border-radius: 8px; background: var(--accent-1); color: #fff; display: flex; align-items: center; justify-content: center; }
.send-btn[disabled] { background: #9aa0a6; color: #fff; cursor: not-allowed; opacity: 0.7; }
.stop-btn { background: #ef4444; }
</style>
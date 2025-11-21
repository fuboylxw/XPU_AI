<template>
  <BaseLayout :mode="'work'" :is-dark="isDark" :user-menu-options="userMenuOptions" :username="displayUsername" :collapsed="sidebarCollapsed" @toggle-theme="toggleTheme" @set-mode="$emit('switch-mode', $event)" @app-download="showAppModal = true" @go-home="onGoHome" @school="onSchool" @user-menu-click="handleUserMenuClick">
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
              <div class="conv-header">
                <div class="conv-title">{{ conv.title }}</div>
                <span v-if="conv.status" class="task-status-badge" :class="`status-${conv.status}`">{{ getStatusText(conv.status) }}</span>
              </div>
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
    <div class="chat-container withRight">
      <div class="chat-main">
        <div class="chat-scroll" ref="chatScroll">
          <div class="task-center" v-if="taskHistories && taskHistories.length">
            <div class="task-stage-card" v-for="(t, idx) in taskHistories" :key="t.id">
              <div class="stage-header">
                <div class="stage-title">任务{{ idx + 1 }}：{{ t.task_name || t.title || '任务' }}</div>
                <span class="stage-status" :class="`status-${(t.status || 'loading')}`">{{ getStatusText(t.status || 'loading') }}</span>
                <div class="stage-time">{{ formatStageTime(t) }}</div>
              </div>
              <div class="stage-body">
                <div v-if="t.result" class="stage-result" v-html="renderMarkdown(t.result)"></div>
                <div v-else class="stage-desc">{{ t.description || '执行中' }}</div>
              </div>
            </div>
          </div>
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
                <div v-if="m.fileInfo" class="file-row">{{ m.fileInfo.name }} · {{ (m.fileInfo.size/1024).toFixed(1) }}KB</div>
                <div v-if="m.type==='assistant' && m.streaming" class="streaming-indicator"><span class="typing-dots"><span></span><span></span><span></span></span><span class="streaming-text">正在生成回答...</span></div>
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
            <div v-if="uploadedFiles.length" class="file-list">
              <div v-for="(f,i) in uploadedFiles" :key="i" class="file-item">
                <span class="file-name">{{ f.name }}</span>
                <button class="del" @click="removeFile(i)">移除</button>
              </div>
            </div>
            <div class="input-actions">
              <button class="icon-btn" @click="handleFileUpload" title="附件"><Icon type="file-default" :size="18" /></button>
              <button class="icon-btn" @click="handleVoiceInput" title="语音输入"><Icon type="mic" :size="18" /></button>
              <button class="send-btn" @click="sendMessage" :disabled="!canSend" title="发送"><Icon type="send" :size="18" /></button>
              <button class="stop-btn" v-if="isStreaming" @click="stopStreaming" title="停止"><Icon type="stop" :size="18" /></button>
            </div>
          </div>
        </div>
      </div>
      <div class="chat-right">
        <TaskSidebar ref="taskSidebar" :visible="true" :conversation-id="currentConversation" :api-base-url="apiBaseUrl" :seed-title="lastUserTaskTitle" />
      </div>
    </div>
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
  </BaseLayout>
</template>

<script>
import BaseLayout from '../layout/BaseLayout.vue'
import TaskSidebar from './TaskSidebar.vue'
import { h } from 'vue'
import Icon from '../common/Icon.vue'
import { authStore } from '../../store/auth.js'

export default {
  name: 'WorkMode',
  components: { BaseLayout, TaskSidebar, Icon },
  emits: ['switch-mode'],
  data() {
    return {
      isDark: false,
      sidebarCollapsed: false,
      inputMessage: '',
      lastUserTaskTitle: '',
      messages: [],
      uploadedFiles: [],
      isStreaming: false,
      currentStreamController: null,
      currentConversation: null,
      apiBaseUrl: 'http://localhost:8000/api',
      conversations: [],
      taskHistories: [],
      showAppModal: false,
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
    toggleSidebar() { this.sidebarCollapsed = !this.sidebarCollapsed },
    onConvMenuClick(e, id) { const v = e && e.value; if (v === 'rename') { this.renameConversation(id) } else if (v === 'delete') { this.deleteConfirmId = id } },
    confirmDelete(id) { this.deleteConfirmId = null; this.deleteConversation(id) },
    handleUserMenuClick(e) { const v = e && e.value; if (v === 'logout') { try { localStorage.clear() } catch (err) {} location.reload() } if (v === 'profile') { try { window.location.href = '/profile' } catch (err) {} } if (v === 'settings') { try { window.location.href = '/settings' } catch (err) {} } },
    async createNewChat() {
      try {
        // 1. 先创建 conversation
        const convResp = await fetch(`${this.apiBaseUrl}/conversations/create/`, { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify({ title: `新任务 ${new Date().toLocaleString()}`, user_id: 'test_user' }) 
        })
        if (convResp.ok) {
          const c = await convResp.json()
          this.currentConversation = c.conversation_id
          
          // 2. 创建对应的 work_task
          const taskResp = await fetch(`${this.apiBaseUrl}/tasks/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              conversation_id: c.conversation_id,
              user_id: 'test_user',
              title: `新任务 ${new Date().toLocaleString()}`,
              status: 'loading'
            })
          })
          
          this.messages = []
          if (this.$refs.taskSidebar) await this.$refs.taskSidebar.loadTasks(this.currentConversation)
          await this.loadConversations() // 刷新左侧任务列表
        }
      } catch (e) {
        console.error('创建新任务失败:', e)
      }
    },
    async sendMessage() {
      if (!this.inputMessage.trim() && this.uploadedFiles.length === 0) return
      if (!this.currentConversation) await this.createNewChat()
      const files = [...this.uploadedFiles]
      for (const f of files) {
        this.messages.push({ id: Date.now()+Math.random(), type: 'user', sender: 'USER', fileInfo: { name: f.name, size: f.size }, time: this.formatTime(new Date()) })
        const form = new FormData()
        form.append('conversation_id', this.currentConversation)
        form.append('user_id', 'test_user')
        form.append('file', f)
        await fetch(`${this.apiBaseUrl}/work/upload/file`, { method: 'POST', body: form })
      }
      this.uploadedFiles = []
      const messageContent = this.inputMessage || '请根据已上传的内容回答'
      const titleForTask = this.inputMessage && this.inputMessage.trim() ? this.inputMessage.trim() : '任务'
      if (this.inputMessage && this.inputMessage.trim()) {
        const userMessage = { id: Date.now(), type: 'user', sender: 'USER', content: this.inputMessage, time: this.formatTime(new Date()) }
        this.messages.push(userMessage)
      }
      this.lastUserTaskTitle = titleForTask
      this.inputMessage = ''
      this.adjustTextareaHeight()
      this.scrollToBottom()
      if (this.$refs.taskSidebar) {
        await this.$refs.taskSidebar.ensureTask(this.currentConversation, titleForTask)
        await this.$refs.taskSidebar.loadTasks(this.currentConversation)
      }
      const assistantMessage = { id: Date.now()+1, type: 'assistant', sender: 'assistant', content: '', time: this.formatTime(new Date()), streaming: true }
      this.messages.push(assistantMessage)
      this.isStreaming = true
      try {
        let pendingHistId = null
        const prePayload = { task_name: titleForTask, description: messageContent, status: 'loading', result: null }
        const preHist = this.$refs.taskSidebar ? await this.$refs.taskSidebar.appendHistory(this.currentConversation, prePayload) : null
        pendingHistId = preHist && preHist.id ? preHist.id : null
        if (this.$refs.taskSidebar) await this.$refs.taskSidebar.loadTasks(this.currentConversation)
        await this.loadTaskHistories(this.currentConversation)
        const body = { conversation_id: this.currentConversation, user_id: 'test_user', message: messageContent }
        const resp = await fetch(`${this.apiBaseUrl}/chat/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        if (resp.ok) {
          const data = await resp.json()
          assistantMessage.content = data.response || ''
          assistantMessage.streaming = false
          this.isStreaming = false
          if (pendingHistId && this.$refs.taskSidebar) await this.$refs.taskSidebar.updateHistory(pendingHistId, { status: 'done', result: assistantMessage.content })
          if (this.$refs.taskSidebar) await this.$refs.taskSidebar.loadTasks(this.currentConversation)
          await this.loadTaskHistories(this.currentConversation)
        } else {
          const errText = await resp.text()
          assistantMessage.content = `请求失败: ${errText}`
          assistantMessage.streaming = false
          this.isStreaming = false
          if (pendingHistId && this.$refs.taskSidebar) await this.$refs.taskSidebar.updateHistory(pendingHistId, { status: 'fail' })
          if (this.$refs.taskSidebar) await this.$refs.taskSidebar.loadTasks(this.currentConversation)
          await this.loadTaskHistories(this.currentConversation)
        }
      } catch (e) {
        assistantMessage.content = '抱歉，处理消息时出现错误。'
        assistantMessage.streaming = false
        this.isStreaming = false
      }
    },
    sendQuickMessage(content) { this.inputMessage = content; this.sendMessage() },
    stopStreaming() { this.isStreaming = false },
    handleEnterKey(e) { if (e.shiftKey) return; this.sendMessage() },
    adjustTextareaHeight() { this.$nextTick(() => { const t = this.$refs.messageInput; if (t) { t.style.height = 'auto'; t.style.height = Math.min(t.scrollHeight, 120) + 'px' } }) },
    scrollToBottom() { this.$nextTick(() => { const a = this.$refs.chatArea; if (a) { a.scrollTop = a.scrollHeight } }) },
    formatTime(d) { return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) },
    handleVoiceInput() { try { if (this.$refs.messageInput) this.$refs.messageInput.focus() } catch (e) {} },
    handleFileUpload() {
      const input = document.createElement('input')
      input.type = 'file'
      input.multiple = true
      input.accept = '.txt,.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif,.mp3,.mp4,.wav'
      input.onchange = e => {
        const files = e.target.files
        if (files && files.length > 0) {
          for (let i = 0; i < files.length; i++) {
            const file = files[i]
            if (file.size > 50 * 1024 * 1024) continue
            this.uploadedFiles.push(file)
          }
          this.$nextTick(() => { if (this.$refs.messageInput) this.$refs.messageInput.focus() })
        }
        this.showDragOverlay = false
      }
      this.showDragOverlay = true
      input.click()
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
    editMessage(message) { try { const newText = prompt('编辑消息', message && message.content ? message.content : ''); if (newText != null) { const t = String(newText).trim(); if (t) message.content = t } } catch (e) {} },
    async copyMessage(content) { try { await navigator.clipboard.writeText(String(content || '')) } catch (e) {} },
    removeFile(i) { this.uploadedFiles.splice(i, 1) },
    async loadConversations() {
      try {
        // 从 work_task 表加载任务列表
        const response = await fetch(`${this.apiBaseUrl}/tasks/?user_id=test_user`)
        if (response.ok) {
          const data = await response.json()
          this.conversations = data.map(task => ({ 
            id: task.conversation_id, 
            title: task.title, 
            time: this.formatConversationTime(task.updated_at), 
            created: task.created_at, 
            status: task.status,
            taskId: task.id // 保存 task id 用于后续操作
          }))
          if (this.conversations.length > 0 && !this.currentConversation) { 
            await this.selectConversation(this.conversations[0].id) 
          }
        }
      } catch (e) {
        console.error('加载任务列表失败:', e)
      }
    },
    async deleteConversation(id) {
      if (this.conversations.length <= 1) return
      try { 
        const conv = this.conversations.find(c => c.id === id)
        if (!conv || !conv.taskId) return
        
        // 删除 work_task (会级联删除 work_task_history)
        const resp = await fetch(`${this.apiBaseUrl}/tasks/${conv.taskId}`, { 
          method: 'DELETE', 
          headers: { 'Content-Type': 'application/json' } 
        })
        
        if (resp.ok) { 
          // 同时删除 conversation
          await fetch(`${this.apiBaseUrl}/conversations/${id}/delete/`, { 
            method: 'DELETE', 
            headers: { 'Content-Type': 'application/json' } 
          })
          
          this.conversations = this.conversations.filter(c => c.id !== id)
          if (this.currentConversation === id) { 
            if (this.conversations.length > 0) { 
              this.selectConversation(this.conversations[0].id) 
            } else { 
              this.currentConversation = null
              this.messages = []
              await this.createNewChat() 
            } 
          }
        } 
      } catch (e) {
        console.error('删除任务失败:', e)
      }
    },
    async renameConversation(id) {
      try { 
        const conv = this.conversations.find(c => c.id === id)
        if (!conv || !conv.taskId) return
        
        const name = prompt('重命名任务', conv.title)
        if (!name || !name.trim()) return
        
        // 更新 work_task 表的标题
        const resp = await fetch(`${this.apiBaseUrl}/tasks/${conv.taskId}/title/`, { 
          method: 'PUT', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify({ title: name.trim() }) 
        })
        
        if (resp.ok) { 
          const data = await resp.json()
          const idx = this.conversations.findIndex(c => c.id === id)
          if (idx >= 0) this.conversations[idx].title = data.title
          
          // 同时更新 conversation 表的标题
          await fetch(`${this.apiBaseUrl}/conversations/${encodeURIComponent(id)}/title/`, { 
            method: 'PUT', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ title: name.trim() }) 
          })
        } 
      } catch (e) {
        console.error('重命名任务失败:', e)
      }
    },
    async selectConversation(id) { this.currentConversation = id; await this.loadConversationHistory(id); if (this.$refs.taskSidebar) { await this.$refs.taskSidebar.loadTasks(id) } await this.loadTaskHistories(id) },
    async loadTaskHistories(conversationId) {
      try {
        const resp = await fetch(`${this.apiBaseUrl}/tasks/${encodeURIComponent(conversationId)}/history/`)
        if (resp.ok) {
          const data = await resp.json()
          this.taskHistories = Array.isArray(data) ? data : []
        } else {
          this.taskHistories = []
        }
      } catch (e) { this.taskHistories = [] }
    },
    formatStageTime(t) {
      const d = new Date(t.updated_at || t.created_at || Date.now())
      return d.toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit', year: 'numeric', month: '2-digit', day: '2-digit' })
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
    toggleTheme() { this.isDark = !this.isDark; document.body.classList.toggle('dark', this.isDark); document.documentElement.setAttribute('theme-mode', this.isDark ? 'dark' : 'light'); localStorage.setItem('theme', this.isDark ? 'dark' : 'light') },
    initTheme() { const saved = localStorage.getItem('theme'); this.isDark = saved === 'dark'; document.body.classList.toggle('dark', this.isDark); document.documentElement.setAttribute('theme-mode', this.isDark ? 'dark' : 'light') },
    onAppDownload() {},
    onGoHome() {},
    getStatusText(status) {
      const statusMap = {
        'loading': '执行中',
        'done': '已完成',
        'completed': '已完成',
        'fail': '失败',
        'error': '失败',
        'pending': '待执行'
      }
      return statusMap[status] || status
    },
    formatConversationTime(dateString) { const date = new Date(dateString); const now = new Date(); const diffTime = Math.abs(now - date); const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); if (diffDays === 1) { return '今天' } else if (diffDays === 2) { return '昨天' } else if (diffDays <= 7) { return `${diffDays}天前` } else { return date.toLocaleDateString('zh-CN') } },
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
.task-center { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
.task-stage-card { border: 1px solid rgba(239,68,68,0.35); border-radius: 12px; background: rgba(255,255,255,0.95); box-shadow: 0 2px 8px rgba(0,0,0,0.06); padding: 12px; }
.stage-header { display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 10px; margin-bottom: 8px; }
.stage-title { font-weight: 600; color: #333; }
.stage-status { font-size: 12px; padding: 2px 8px; border-radius: 12px; background: rgba(74,144,226,0.12); color: #4A90E2; }
.stage-status.status-done, .stage-status.status-completed { background: rgba(34,197,94,0.15); color: #22c55e; }
.stage-status.status-fail, .stage-status.status-error { background: rgba(239,68,68,0.15); color: #ef4444; }
.stage-status.status-pending { background: rgba(156,163,175,0.15); color: #6b7280; }
.stage-time { font-size: 12px; color: var(--text-2); }
.stage-body { padding-top: 4px; }
.stage-result { font-size: 14px; line-height: 1.7; color: #333; }
.stage-desc { font-size: 13px; color: #666; }
.dark .task-stage-card { background: rgba(30,41,59,0.6); border-color: rgba(239,68,68,0.25); }
.dark .stage-title { color: #e5e7eb; }
.dark .stage-result { color: #e5e7eb; }
.chat-container { display: grid; grid-template-columns: 1fr; height: 100%; }
.chat-container.withRight { grid-template-columns: 1fr 250px; }
.chat-main { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.chat-scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 40px 24px; background: var(--surface-2); color: var(--text-1); position: relative; }
.chat-scroll::-webkit-scrollbar { width: 6px; }
.chat-scroll::-webkit-scrollbar-track { background: transparent; }
.chat-scroll::-webkit-scrollbar-thumb { background: rgba(74,144,226,0.3); border-radius: 3px; }
.chat-scroll::-webkit-scrollbar-thumb:hover { background: rgba(74,144,226,0.5); }
.chat-input { border-top: 1px solid var(--border-1); padding: 16px 12px; background: var(--surface-2); display: flex; justify-content: center; flex-shrink: 0; }
.chat-input :deep(.input-wrap) { width: 100%; max-width: 720px; }
.chat-right { border-left: 1px solid var(--border-1); background: var(--surface-1); }
.message-list { display: flex; flex-direction: column; gap: 12px; width: 100%; height: 100%; }
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
.conv-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.conv-title { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; }
.task-status-badge { font-size: 11px; padding: 2px 6px; border-radius: 10px; white-space: nowrap; flex-shrink: 0; }
.task-status-badge.status-loading { background: rgba(74,144,226,0.15); color: #4A90E2; }
.task-status-badge.status-done, .task-status-badge.status-completed { background: rgba(34,197,94,0.15); color: #22c55e; }
.task-status-badge.status-fail, .task-status-badge.status-error { background: rgba(239,68,68,0.15); color: #ef4444; }
.task-status-badge.status-pending { background: rgba(156,163,175,0.15); color: #6b7280; }
.conv-time { font-size: 12px; color: var(--text-2); }
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
.msg-content :deep(code) { background: rgba(229,229,229,0.4); padding: 0 4px; border-radius: 4px; }
.file-row { margin-top: 6px; font-size: 13px; color: #666; }
.input-wrap { position: relative; }
.input { width: 100%; resize: none; border: 1px solid var(--border-1); border-radius: 12px; padding: 12px 12px 46px 12px; background: var(--surface-2); color: var(--text-1); min-height: 44px; font-size: 14px; line-height: 1.7; caret-color: var(--accent-1); font-family: 'Microsoft YaHei','微软雅黑',system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial; overflow-y: auto; }
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
.input-actions { position: absolute; right: 8px; bottom: 8px; display: flex; gap: 8px; align-items: center; }
.icon-btn { width: 32px; height: 32px; border: none; background: transparent; color: var(--text-2); display: flex; align-items: center; justify-content: center; cursor: pointer; transition: color 0.2s ease; }
.icon-btn:hover { color: var(--accent-1); }
.send-btn, .stop-btn { width: 36px; height: 32px; padding: 0; border: none; border-radius: 8px; background: var(--accent-1); color: #fff; display: flex; align-items: center; justify-content: center; }
.send-btn[disabled] { background: #9aa0a6; color: #fff; cursor: not-allowed; opacity: 0.7; }
.stop-btn { background: #ef4444; }
.file-list { position: absolute; left: 12px; bottom: 48px; display: flex; flex-wrap: wrap; gap: 6px; max-width: calc(100% - 180px); }
.file-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 8px; background: rgba(229,229,229,0.5); }
.file-name { font-size: 13px; color: #333; }
.del { border: none; background: transparent; color: #ef4444; }
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
</style>

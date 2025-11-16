<template>
  <div class="app">
    <!-- 左侧对话列表 -->
    <div class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="header-buttons">
          <button class="new-chat-btn" @click="createNewChat" v-show="!sidebarCollapsed">
          新建对话
        </button>
          <button class="collapse-btn" @click="toggleSidebar" :title="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'">
            <Icon type="menu-fold" :fill-color='"transparent"' :stroke-color='"currentColor"' :stroke-width="2"/>
          </button>
        </div>
      </div>
      
      <div class="conversation-list" v-show="!sidebarCollapsed">
        <!-- 加载骨架屏 -->
        <template v-if="loading">
          <div class="skeleton-item" v-for="i in 6" :key="'skl-'+i">
            <div class="skeleton-avatar shimmer"></div>
            <div class="skeleton-lines">
              <div class="skeleton-line shimmer" style="width: 70%"></div>
              <div class="skeleton-line shimmer" style="width: 40%"></div>
            </div>
          </div>
        </template>
        <!-- 对话列表 -->
        <template v-else>
          <div 
            v-for="conv in conversations" 
            :key="conv.id"
            class="conversation-item"
            :class="{ active: conv.id === currentConversation }"
          >
            <div class="conv-content" @click="selectConversation(conv.id)">
              <div class="conv-title">{{ conv.title }}</div>
              <div class="conv-time">{{ conv.time }}</div>
            </div>
            <button 
              class="delete-btn" 
              @click.stop="deleteConversation(conv.id)"
              title="删除对话"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 6h18"/>
                <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>
                <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
                <line x1="10" x2="10" y1="11" y2="17"/>
                <line x1="14" x2="14" y1="11" y2="17"/>
              </svg>
            </button>
          </div>
        </template>
      </div>
    </div>

    <!-- 右侧聊天区域 -->
    <div class="main-content">
      <!-- 侧边栏完全隐藏时的展开按钮 -->
      <button 
        v-show="sidebarCollapsed" 
        class="expand-sidebar-btn" 
        @click="toggleSidebar"
        title="展开侧边栏"
      >
        <Icon type="menu-fold" :fill-color='"transparent"' :stroke-color='"currentColor"' :stroke-width="2"/>
      </button>
      
      <!-- 顶部导航栏 -->
      <div class="header">
        <div class="chat-title">
          <span class="title-icon">
            <div :class="['logo', isDark ? 'logo-dark' : 'logo-light']">
              <img v-if="!isDark" height="50" src="../components/tuan7.svg" alt="logo" />
              <img v-else height="50" src="../components/tuan8.svg" alt="logo" />
            </div>
          </span>
        </div>
        <div class="header-right">
          <!-- 学校首页导航按钮 -->
          <button 
            class="header-btn" 
            @click="goToSchoolHomepage"
            title="学校首页"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="transparent" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>
              <path d="M2 12h20"/>
            </svg>
          </button>

          <!-- 西工程大APP下载按钮 -->
          <button 
            class="header-btn" 
            @click="showAppDownload"
            title="西工程大APP下载"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="transparent" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7,10 12,15 17,10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
          </button>

          <span class="theme-label">{{ isDark ? '深色' : '浅色' }}</span>
          <button type="button" class="TDesign-switch size-small" @click="toggleTheme">
            <span class="TDesign-switch__handle"></span>
          </button>
          
          <!-- 用户信息下拉菜单 - 使用TDesign组件 -->
          <t-dropdown 
            :options="userMenuOptions" 
            @click="handleUserMenuClick"
            placement="bottom-right"
            :popup-props="{ overlayClassName: 'user-dropdown-popup' }"
          >
            <div class="user-menu-trigger">
              <Icon 
                type="user-circle-icon" 
                :size="32" 
                :fill-color='"transparent"' 
                :stroke-color="isDark ? '#cccccc' : '#333'" 
                :stroke-width="2"
                class="user-avatar"
              />
              <span class="username">{{ getUserDisplayName() }}</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="dropdown-icon">
                <polyline points="6,9 12,15 18,9"></polyline>
              </svg>
            </div>
          </t-dropdown>
        </div>
      </div>

      <!-- 聊天消息区域 -->
      <div class="chat-area" ref="chatArea" :class="{ 'drag-over': isDragOver }" role="log" aria-live="polite">
        <!-- 聊天区加载骨架屏 -->
        <div v-if="loading" class="skeleton-chat">
          <div class="skeleton-bubble shimmer" style="width: 60%"></div>
          <div class="skeleton-bubble shimmer" style="width: 40%; align-self: flex-end"></div>
          <div class="skeleton-bubble shimmer" style="width: 75%"></div>
        </div>
        <!-- 拖拽上传提示层 -->
        <div v-if="isDragOver" class="drag-overlay">
          <div class="drag-content">
            <div class="drag-icon">
              <img src="../components/doc1.svg" alt="上传文档" width="64" height="64" />
            </div>
            <h3>拖拽文件到此处上传</h3>
            <p>支持 TXT、PDF、DOC、DOCX、JPG、PNG、GIF、MP3、MP4、WAV 格式</p>
            <p>文件大小限制：50MB</p>
          </div>
        </div>
        <!-- 空状态 -->
        <div v-if="!loading && messages && messages.length === 0" class="empty-state">
          <div class="welcome-message">
            <h2>织语，知你所需。</h2>
          </div>
          
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

        <!-- 消息列表 -->
        <div v-for="message in (messages || [])" :key="message.id" class="message" :class="message.type">
          <!-- 用户消息 - 保留气泡格式 -->
          <div v-if="message.type === 'user'" class="message-header">
          </div>
          <div v-if="message.type === 'user'" class="user-message-container">
            <div class="message-content">
              <!-- 如果是文件消息，显示文件图标和名称 -->
              <div v-if="message.fileInfo" class="file-message">
                <Icon :type="getFileIconType(message.fileInfo.name)" :size="24" />
                <div class="file-details">
                  <div class="file-name">{{ message.fileInfo.name }}</div>
                  <div class="file-size">{{ (message.fileInfo.size / 1024 / 1024).toFixed(2) }} MB</div>
                </div>
              </div>
              <!-- 普通文本消息 -->
              <div v-else>
                {{ message.content }}
              </div>
            </div>
            <!-- 消息操作按钮 - 位于气泡外部右下方 -->
            <div class="message-actions-external">
              <button 
                class="action-btn edit-btn" 
                @click="editMessage(message)"
                title="编辑消息"
              >
                <Icon type="edit" :fill-color="'transparent'" :stroke-color="'currentColor'" :stroke-width="2" :size="16"/>
              </button>
              <button 
                class="action-btn copy-btn" 
                @click="copyMessage(message.content)"
                title="复制消息"
              >
                <Icon type="copy" :fill-color="'transparent'" :stroke-color="'currentColor'" :stroke-width="2" :size="16"/>
              </button>
            </div>
          </div>
          
          <!-- 智能体消息 - 添加气泡格式 -->
          <div v-else class="assistant-message">
            <div class="message-header">
            </div>
            <div class="assistant-message-container">
              <div class="assistant-message-content">
                <div v-html="renderMarkdown(message.content)"></div>
              </div>
              <!-- 消息操作按钮 - 位于气泡外部左下方 -->
              <div class="message-actions-external">
                <!-- 流式输出指示器 -->
                <div v-if="message.streaming" class="streaming-indicator">
                  <span class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </span>
                  <span class="streaming-text">正在生成回答...</span>
                </div>
                <!-- 复制按钮 -->
                <button 
                  v-if="!message.streaming"
                  class="action-btn copy-btn" 
                  @click="copyMessage(message.content)"
                  title="复制消息"
                >
                  <Icon type="copy" :fill-color="'transparent'" :stroke-color="'currentColor'" :stroke-width="2" :size="16"/>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area" :class="{ 'drag-over': isDragOver }">
        <div class="input-container">
          <!-- 隐藏文件输入，支持点击上传 -->
          <input ref="fileInput" type="file" style="display: none;" @change="handleFilesSelected" multiple accept=".txt,.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif,.mp3,.mp4,.wav" aria-hidden="true" />
          <!-- 文件预览区域 -->
          <div v-if="uploadedFiles.length > 0" class="file-preview-area">
            <div v-for="(file, index) in uploadedFiles" :key="index" class="file-preview-item">
              <Icon :type="getFileIconType(file.name)" :size="20" :fill-color="'transparent'" :stroke-color="'currentColor'" :stroke-width="2" />
              <span class="file-name">{{ file.name }}</span>
              <span class="file-size">({{ (file.size / 1024 / 1024).toFixed(2) }} MB)</span>
              <button class="remove-file-btn" @click="removeFile(index)" title="移除文件">×</button>
            </div>
          </div>
          
          <div class="input-wrapper">
            <textarea
              v-model="inputMessage"
              class="message-input"
              placeholder="输入您的问题，让织语为您解答"
              @keydown="handleKeyDown"
              @input="adjustTextareaHeight"
              ref="messageInput"
              aria-label="消息输入框"
            ></textarea>
            <div class="shortcut-hint" aria-hidden="true"></div>
            
            <div class="input-actions">
              <button 
                class="attachment-btn" 
                @click="openFileDialog"
                title="上传文件"
                aria-label="上传文件"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.64 16.2a2 2 0 0 1-2.83-2.83l8.49-8.49"/>
                </svg>
              </button>
              
              <button 
                class="voice-btn" 
                :class="{ recording: isRecording }"
                @click="handleVoiceInput"
                :title="isRecording ? '点击停止录音' : '语音输入'"
                :disabled="false"
                aria-label="语音输入"
              >
                <svg v-if="!isRecording" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                  <path d="M12 19v4"/>
                  <path d="M8 23h8"/>
                </svg>
                <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="6" y="6" width="12" height="12" rx="2"/>
                </svg>
                <span v-if="isRecording" class="recording-indicator">●</span>
              </button>
              
              <button 
                class="call-btn" 
                :class="{ active: isPhoneCallActive }"
                @click="handleCallInput"
                :title="isPhoneCallActive ? '结束电话通话' : '开始电话通话'"
                aria-label="电话通话"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
                </svg>
                <span v-if="isPhoneCallActive" class="phone-indicator">●</span>
              </button>
              
              <button 
                class="send-btn" 
                @click="isStreaming ? stopStreaming() : sendMessage()"
                :disabled="!inputMessage.trim() && !isStreaming"
                :title="isStreaming ? '停止回答' : '发送消息'"
                aria-label="发送消息"
              >
                <Icon 
                  v-if="isStreaming"
                  type="stop"
                  :fill-color='"transparent"' 
                  :stroke-color='"currentColor"' 
                  :stroke-width="2"
                  :size="20"
                />
                <svg 
                  v-else
                  width="20" 
                  height="20" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  stroke-width="2" 
                  stroke-linecap="round" 
                  stroke-linejoin="round"
                >
                  <path d="M22 2L11 13"/>
                  <path d="M22 2l-7 20-4-9-9-4z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- APP下载模态框 -->
    <div v-if="showAppModal" class="modal-overlay" @click="closeAppModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>西工程大APP下载</h3>
          <button class="close-btn" @click="closeAppModal">×</button>
        </div>
        <div class="modal-body">
          <div class="app-clients">
            <div class="client-item">
              <img src="../components/ios.png" alt="iOS客户端二维码" class="app-qr-image" />
              <p>iOS客户端</p>
            </div>
            <div class="client-item">
              <img src="../components/android.png" alt="安卓客户端二维码" class="app-qr-image" />
              <p>安卓客户端</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 语音识别提示 -->
    <div class="voice-alerts-container">
      <t-message 
        v-if="showVoiceSuccess" 
        theme="success" 
        :content="voiceSuccessMessage"
        :close-btn="true"
        @close="closeVoiceSuccess"
        class="voice-message"
      />
      <t-message 
        v-if="showVoiceError" 
        theme="error" 
        :content="voiceErrorMessage"
        :close-btn="true"
        @close="closeVoiceError"
        class="voice-message"
      />
    </div>

    <!-- 电话通话模态框 -->
    <CallModal 
      v-if="showCallModal"
      :visible="showCallModal"
      :call-status="callStatus"
      :call-duration="callDuration"
      :is-muted="isMuted"
      :is-speaker-on="isSpeakerOn"
      @close="closeCallModal"
      @hang-up="hangUpCall"
      @mute-toggle="handleMuteToggle"
      @speaker-toggle="handleSpeakerToggle"
    />
  </div>
</template>

<script>
import { h } from 'vue'
import Icon from '../components/Icon.vue'
import CallModal from './CallModal.vue'
// 使用相对路径避免 alias 解析异常
import { renderMarkdown as mdRender } from '../utils/markdown.js'
import { authStore } from '../store/auth.js'

export default {
  name: 'ChatApp',
  components: { Icon, CallModal },
  data() {
    return {
      inputMessage: '',
      messages: [],
      conversations: [],
      currentConversation: null,
      isDark: false,
      isRecording: false,
      hoveredMessageId: null,
      sidebarCollapsed: false,
      loading: false,
      isStreaming: false,
      currentStreamController: null,
      apiBaseUrl: 'http://localhost:8000/api',
      showAppModal: false,
      // 语音识别相关
      mediaRecorder: null,
      audioChunks: [],
      recordingStartTime: null,
      voiceRecognitionError: null,
      showVoiceError: false,
      voiceErrorMessage: '',
      showVoiceSuccess: false,
      voiceSuccessMessage: '',
      // 拖拽上传相关
      isDragOver: false,
      dragCounter: 0,
      // 文件上传相关
      uploadedFiles: [],
      // 电话通话连续对话相关
      isPhoneCallActive: false,
      phoneCallStream: null,
      phoneCallSessionId: null,
      phoneCallRoundCount: 0,
      phoneCallTimeoutId: null,
      phoneCallAudioContext: null,
      // 电话模态框相关
      showCallModal: false,
      callStatus: 'connecting',
      callDuration: 0,
      callStartTime: null,
      callTimer: null,
      isMuted: false,
      isSpeakerOn: false,
      // TDesign下拉菜单选项
      userMenuOptions: [
        {
          content: '退出登录',
          value: 'logout',
          prefixIcon: () => h('svg', {
            width: 16,
            height: 16,
            viewBox: '0 0 24 24',
            fill: 'transparent',
            stroke: 'currentColor',
            'stroke-width': 2,
            'stroke-linecap': 'round',
            'stroke-linejoin': 'round'
          }, [
            h('path', { d: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4' }),
            h('polyline', { points: '16,17 21,12 16,7' }),
            h('line', { x1: '21', y1: '12', x2: '9', y2: '12' })
          ])
        }
      ]
    }
  },
  computed: {
    userInfo() {
      return authStore.user
    }
  },
  mounted() {
    // 初始化主题
    this.initTheme();
    // 调整输入框高度
    this.adjustTextareaHeight();
    // 加载对话列表
    this.loadConversations();
    // 添加拖拽事件监听器
    this.addDragListeners();
  },
  beforeUnmount() {
    // 组件销毁时移除拖拽监听器
    this.removeDragListeners();
  },
  methods: {
    // 打开文件选择对话框（用于附件按钮）
    openFileDialog() {
      const input = this.$refs.fileInput
      if (input) input.click()
    },

    // 处理文件选择
    handleFilesSelected(event) {
      const files = Array.from(event.target.files || [])
      if (files.length) {
        this.uploadedFiles = this.uploadedFiles.concat(files)
      }
      // 清空 input，便于重复选择同一文件
      event.target.value = ''
    },

    // 统一按键处理：Ctrl/Cmd+Enter 发送、Shift+Enter 换行、Esc 停止
    handleKeyDown(event) {
      const el = this.$refs.messageInput
      if (!el) return

      if (event.key === 'Enter') {
        if (event.shiftKey) {
          // 插入换行
          const start = el.selectionStart
          const end = el.selectionEnd
          const value = this.inputMessage || ''
          this.inputMessage = value.substring(0, start) + '\n' + value.substring(end)
          this.$nextTick(() => {
            el.selectionStart = el.selectionEnd = start + 1
          })
        } else if (event.ctrlKey || event.metaKey) {
          // Ctrl/Cmd + Enter 发送
          event.preventDefault()
          if (!this.isStreaming) {
            this.sendMessage()
          } else {
            this.stopStreaming()
          }
        }
      } else if (event.key === 'Escape') {
        // Esc 停止流式生成
        if (this.isStreaming) {
          this.stopStreaming()
        }
      }
    },
    // 获取用户显示名称
    getUserDisplayName() {
      if (!this.userInfo) {
        return '用户';
      }
      
      // 优先显示昵称，然后是用户名，最后是默认值
      const displayName = this.userInfo.nickname || this.userInfo.username || '用户';
      
      // 确保返回的是字符串，避免显示为问号
      return String(displayName).trim() || '用户';
    },
    
    // 用户登出
    logout() {
      console.log('开始执行logout...');
      try {
        authStore.logout();
        console.log('authStore.logout() 执行完成');
        console.log('准备跳转到登录页...');
        this.$router.push('/login');
        console.log('路由跳转命令已执行');
      } catch (error) {
        console.error('logout过程中出现错误:', error);
      }
    },
    
    // 处理TDesign下拉菜单点击事件
    handleUserMenuClick(data) {
      console.log('TDesign下拉菜单点击:', data);
      if (data.value === 'logout') {
        this.logout();
      }
    },
    
    // 切换侧边栏收起/展开状态
     toggleSidebar() {
       this.sidebarCollapsed = !this.sidebarCollapsed;
     },

     // 从数据库加载对话列表
     async loadConversations() {
       try {
         this.loading = true;
         const response = await fetch(`${this.apiBaseUrl}/conversations/`);
         if (response.ok) {
           const data = await response.json();
           this.conversations = data.map(conv => ({
             id: conv.conversation_id,
             title: conv.title,
             time: this.formatConversationTime(conv.created),
             created: conv.created,
             status: conv.status
           }));
           
           // 如果有对话，默认选择第一个
           if (this.conversations.length > 0 && !this.currentConversation) {
             this.selectConversation(this.conversations[0].id);
           }
         } else {
           console.error('加载对话列表失败:', response.status);
         }
       } catch (error) {
         console.error('加载对话列表出错:', error);
       } finally {
         this.loading = false;
       }
     },

     // 从数据库加载对话历史记录
     async loadConversationHistory(conversationId) {
       try {
         this.loading = true;
         const response = await fetch(`${this.apiBaseUrl}/conversations/${conversationId}/messages/`);
         if (response.ok) {
           const data = await response.json();
           
           // 根据API返回的数据结构处理消息
           const messages = Array.isArray(data) ? data : (data.value || []);
           if (messages.length > 0) {
             // 处理消息数组
             this.messages = [];
             messages.forEach(msg => {
               if (msg.question) {
                 this.messages.push({
                   id: msg.id + '_q',
                   type: 'user',
                   content: msg.question,
                   time: this.formatTime(new Date(msg.created_at))
                 });
               }
               if (msg.answer) {
                 this.messages.push({
                   id: msg.id + '_a',
                   type: 'assistant',
                   content: msg.answer,
                   time: this.formatTime(new Date(msg.created_at))
                 });
               }
             });
           } else {
             // 如果没有数据
             this.messages = [];
           }
           
           this.scrollToBottom();
         } else {
           console.error('加载对话历史失败:', response.status);
           this.messages = [];
         }
       } catch (error) {
         console.error('加载对话历史出错:', error);
         this.messages = [];
       } finally {
         this.loading = false;
       }
     },

     // 格式化对话时间
     formatConversationTime(dateString) {
       const date = new Date(dateString);
       const now = new Date();
       const diffTime = Math.abs(now - date);
       const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
       
       if (diffDays === 1) {
         return '今天';
       } else if (diffDays === 2) {
         return '昨天';
       } else if (diffDays <= 7) {
         return `${diffDays}天前`;
       } else {
         return date.toLocaleDateString('zh-CN');
       }
     },

     // 选择对话（更新为加载历史记录）
     async selectConversation(id) {
       this.currentConversation = id;
       await this.loadConversationHistory(id);
     },

     // 发送消息（更新为调用API）
     async sendMessage() {
       if (!this.inputMessage.trim()) return;
       
       // 如果没有当前对话，先创建一个
       if (!this.currentConversation) {
         await this.createNewChat();
       }
       
       const userMessage = {
         id: Date.now(),
         type: 'user',
         sender: 'USER',
         content: this.inputMessage,
         time: this.formatTime(new Date())
       };
       
       this.messages.push(userMessage);
       const messageContent = this.inputMessage;
       this.inputMessage = '';
       this.adjustTextareaHeight();
       this.scrollToBottom();
       
       // 创建助手消息占位符
       const assistantMessage = {
         id: Date.now() + 1,
         type: 'assistant',
         sender: 'assistant',
         content: '',
         time: this.formatTime(new Date()),
         streaming: true
       };
       this.messages.push(assistantMessage);
       this.scrollToBottom();

       // 设置流式传输状态
       this.isStreaming = true;

       try {
         // 使用EventSource接收SSE流式数据
         const eventSourceUrl = `${this.apiBaseUrl}/chat/stream/`;
         
         // 由于EventSource不支持POST请求，我们需要先发送POST请求启动流式响应
         const response = await fetch(eventSourceUrl, {
           method: 'POST',
           headers: {
             'Content-Type': 'application/json',
           },
           body: JSON.stringify({
             conversation_id: this.currentConversation,
             message: messageContent,
             user_id: 'test_user'
           })
         });
         
         if (response.ok) {
           // 使用ReadableStream处理SSE响应
           const reader = response.body.getReader();
           this.currentStreamController = reader;
           const decoder = new TextDecoder();
           
           while (true) {
             // 检查是否被停止
             if (!this.isStreaming) {
               reader.cancel();
               break;
             }
             
             const { done, value } = await reader.read();
             if (done) break;
             
             const chunk = decoder.decode(value);
             const lines = chunk.split('\n');
             
             for (const line of lines) {
               if (line.startsWith('data: ')) {
                 try {
                   const data = JSON.parse(line.slice(6));
                   
                   if (data.type === 'chunk' && data.chunk) {
                     // 追加内容到助手消息，实现流式展示
                     assistantMessage.content += data.chunk;
                     this.scrollToBottom();
                     // 强制Vue更新DOM
                     this.$forceUpdate();
                   } else if (data.type === 'done') {
                     // 流式传输完成
                     assistantMessage.streaming = false;
                     this.isStreaming = false;
                     this.currentStreamController = null;
                     console.log('流式传输完成');
                     break;
                   } else if (data.type === 'error') {
                     // 处理错误
                     assistantMessage.content = data.error || '抱歉，处理消息时出现错误。';
                     assistantMessage.streaming = false;
                     this.isStreaming = false;
                     this.currentStreamController = null;
                     break;
                   }
                 } catch (parseError) {
                   console.warn('解析流数据失败:', parseError);
                 }
               }
             }
           }
         } else {
           console.error('发送消息失败:', response.status);
           assistantMessage.content = '抱歉，发送消息时出现错误，请稍后重试。';
           assistantMessage.streaming = false;
           this.isStreaming = false;
           this.currentStreamController = null;
         }
       } catch (error) {
         console.error('发送消息出错:', error);
         assistantMessage.content = '网络连接错误，请检查网络后重试。';
         assistantMessage.streaming = false;
         this.isStreaming = false;
         this.currentStreamController = null;
       }
     },

     // 停止流式传输
     stopStreaming() {
       if (this.isStreaming && this.currentStreamController) {
         this.isStreaming = false;
         try {
           this.currentStreamController.cancel();
         } catch (error) {
           console.warn('停止流式传输时出现错误:', error);
         }
         this.currentStreamController = null;
         
         // 找到最后一个流式传输的消息并标记为完成
         const lastMessage = this.messages[this.messages.length - 1];
         if (lastMessage && lastMessage.streaming) {
           lastMessage.streaming = false;
           if (!lastMessage.content.trim()) {
             lastMessage.content = '回答已停止。';
           }
         }
       }
     },
    

    
    sendQuickMessage(content) {
      this.inputMessage = content;
      this.sendMessage();
    },
    
    handleEnterKey(event) {
      if (event.shiftKey) {
        return;
      }
      this.sendMessage();
    },
    
    adjustTextareaHeight() {
      this.$nextTick(() => {
        const textarea = this.$refs.messageInput;
        if (textarea) {
          textarea.style.height = 'auto';
          textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        }
      });
    },
    
    formatTime(date) {
      return date.toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    },

    renderMarkdown(text) {
      return mdRender(text)
    },

    // 获取文件类型图标
    getFileIconType(fileName) {
      const extension = fileName.split('.').pop().toLowerCase();
      
      const typeMap = {
        // 文档类型
        'pdf': 'file-pdf',
        'doc': 'file-word',
        'docx': 'file-word',
        'txt': 'file-text',
        
        // 图片类型
        'jpg': 'file-image',
        'jpeg': 'file-image',
        'png': 'file-image',
        'gif': 'file-image',
        'bmp': 'file-image',
        'svg': 'file-image',
        
        // 音频类型
        'mp3': 'file-audio',
        'wav': 'file-audio',
        'flac': 'file-audio',
        'aac': 'file-audio',
        
        // 其他类型
        'zip': 'file-default',
        'rar': 'file-default',
        '7z': 'file-default',
        'tar': 'file-default'
      };
      
      return typeMap[extension] || 'file-default';
    },

    // 获取文件类型（保留原有方法用于其他用途）
    getFileType(fileName) {
      const extension = fileName.split('.').pop().toLowerCase();
      
      const typeMap = {
        // 文档类型
        'pdf': 'pdf',
        'doc': 'word',
        'docx': 'word',
        'txt': 'text',
        
        // 图片类型
        'jpg': 'image',
        'jpeg': 'image',
        'png': 'image',
        'gif': 'image',
        'bmp': 'image',
        'svg': 'image',
        
        // 音频类型
        'mp3': 'audio',
        'wav': 'audio',
        'flac': 'audio',
        'aac': 'audio',
        
        // 其他类型
        'zip': 'archive',
        'rar': 'archive',
        '7z': 'archive',
        'tar': 'archive'
      };
      
      return typeMap[extension] || 'file';
    },
    
    createNewChat() {
      // 调用异步方法创建新对话
      this.createNewChatAsync();
    },
    
    async createNewChatAsync() {
      try {
        const response = await fetch(`${this.apiBaseUrl}/conversations/create/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            title: `新对话 ${new Date().toLocaleString()}`,
            user_id: 'test_user'
          })
        });
        
        if (response.ok) {
          const conversation = await response.json();
          
          const newConv = {
            id: conversation.conversation_id,
            title: conversation.title,
            time: '刚刚',
            created: conversation.created,
            status: conversation.status
          };
          
          this.conversations.unshift(newConv);
          this.currentConversation = newConv.id;
          this.messages = [];
          
          console.log('新对话创建成功:', newConv);
        } else {
          console.error('创建新对话失败:', response.status);
        }
      } catch (error) {
        console.error('创建新对话出错:', error);
      }
    },
    
    async deleteConversation(id) {
      if (this.conversations.length <= 1) {
        alert('至少需要保留一个对话');
        return;
      }
      
      // 确认删除
      if (!confirm('确定要删除这个对话吗？删除后无法恢复。')) {
        return;
      }
      
      try {
        // 调用后端API删除对话
        const response = await fetch(`${this.apiBaseUrl}/conversations/${id}/delete/`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json'
          }
        });
        
        if (response.ok) {
          // 后端删除成功，更新前端状态
          this.conversations = this.conversations.filter(c => c.id !== id);
          
          if (this.currentConversation === id) {
            // 如果删除的是当前对话，选择第一个剩余的对话并加载其历史
            if (this.conversations.length > 0) {
              await this.selectConversation(this.conversations[0].id);
            } else {
              // 如果没有剩余对话，清空消息并获取用户对话
           this.messages = [];
           this.currentConversation = null;
           await this.createNewChat();
            }
          }
          
          console.log('对话删除成功');
        } else {
          const errorData = await response.json();
          console.error('删除对话失败:', errorData);
          alert(`删除对话失败: ${errorData.detail || '未知错误'}`);
        }
      } catch (error) {
        console.error('删除对话出错:', error);
        alert('删除对话时发生网络错误，请稍后重试');
      }
    },
    
    toggleTheme() {
      this.isDark = !this.isDark;
      document.body.classList.toggle('dark', this.isDark);
      localStorage.setItem('theme', this.isDark ? 'dark' : 'light');
    },
    
    initTheme() {
      const savedTheme = localStorage.getItem('theme');
      this.isDark = savedTheme === 'dark';
      document.body.classList.toggle('dark', this.isDark);
    },
    
    editMessage(message) {
      // 找到要编辑的消息在数组中的索引
      const messageIndex = this.messages.findIndex(m => m.id === message.id);
      if (messageIndex === -1) return;
      
      // 删除该消息及其之后的所有消息（包括AI回复）
      this.messages = this.messages.slice(0, messageIndex);
      
      // 将消息内容填充到输入框
      this.inputMessage = message.content;
      
      // 调整输入框高度
      this.adjustTextareaHeight();
      
      // 聚焦到输入框
      this.$nextTick(() => {
        const textarea = this.$refs.messageInput;
        if (textarea) {
          textarea.focus();
          // 将光标移到文本末尾
          textarea.setSelectionRange(textarea.value.length, textarea.value.length);
        }
      });
    },
    
    scrollToBottom() {
      this.$nextTick(() => {
        const chatArea = this.$refs.chatArea;
        if (chatArea) {
          chatArea.scrollTop = chatArea.scrollHeight;
        }
      });
    },
    
    // 文件上传处理函数
    handleFileUpload() {
      const input = document.createElement('input');
      input.type = 'file';
      input.multiple = true;
      input.accept = '.txt,.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif,.mp3,.mp4,.wav';
      
      input.onchange = (event) => {
        const files = event.target.files;
        if (files && files.length > 0) {
          for (let i = 0; i < files.length; i++) {
            const file = files[i];
            console.log('上传文件:', file.name, '大小:', file.size, '类型:', file.type);
            
            // 检查文件大小
            if (file.size > 50 * 1024 * 1024) {
              console.warn(`文件过大: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`);
              continue;
            }
            
            // 将文件添加到uploadedFiles数组中
            this.uploadedFiles.push(file);
          }
          
          // 聚焦到输入框
          this.$nextTick(() => {
            if (this.$refs.messageInput) {
              this.$refs.messageInput.focus();
            }
          });
        }
      };
      
      input.click();
    },
    
    // 语音输入处理函数
    async handleVoiceInput() {
      if (!this.isRecording) {
        // 开始录音
        await this.startRecording();
      } else {
        // 停止录音
        await this.stopRecording();
      }
    },
    
    async startRecording() {
      try {
        this.voiceRecognitionError = null;
        
        // 检查浏览器是否支持语音录制
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error('您的浏览器不支持语音录制功能');
        }
        
        // 获取麦克风权限
        const stream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            sampleRate: 16000,
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true
          } 
        });
        
        // 创建MediaRecorder实例
        this.mediaRecorder = new MediaRecorder(stream, {
          mimeType: 'audio/webm;codecs=opus'
        });
        
        this.audioChunks = [];
        this.recordingStartTime = Date.now();
        
        // 监听数据可用事件
        this.mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            this.audioChunks.push(event.data);
          }
        };
        
        // 监听录制停止事件
        this.mediaRecorder.onstop = async () => {
          try {
            await this.processRecordedAudio();
          } catch (error) {
            console.error('处理录音失败:', error);
            this.showVoiceErrorMessage(error.message);
          } finally {
            // 停止所有音频轨道
            stream.getTracks().forEach(track => track.stop());
          }
        };
        
        // 开始录制
        this.mediaRecorder.start();
        this.isRecording = true;
        console.log('开始录音...');
        
        // 显示录音开始提示
        this.showVoiceSuccessMessage('开始录音，请说话...');
        
      } catch (error) {
        console.error('启动录音失败:', error);
        this.showVoiceErrorMessage(error.message);
        this.isRecording = false;
      }
    },
    
    async stopRecording() {
      if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.stop();
        this.isRecording = false;
        
        const recordingDuration = Date.now() - this.recordingStartTime;
        console.log(`录音结束，时长: ${recordingDuration}ms`);
        
        // 显示处理中提示
        this.showVoiceSuccessMessage('录音完成，正在识别中...');
      }
    },
    
    async processRecordedAudio() {
      if (this.audioChunks.length === 0) {
        throw new Error('没有录制到音频数据');
      }
      
      // 检查录制时长
      const recordingDuration = Date.now() - this.recordingStartTime;
      if (recordingDuration < 500) {
        throw new Error('录制时间太短，请重新录制');
      }
      
      // 创建音频Blob
      const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
      
      // 转换为WAV格式（如果需要）
      const wavBlob = await this.convertToWav(audioBlob);
      
      // 发送到后端进行语音识别
      await this.sendAudioForRecognition(wavBlob);
    },
    
    async convertToWav(audioBlob) {
      return new Promise((resolve, reject) => {
        try {
          // 创建AudioContext
          const audioContext = new (window.AudioContext || window.webkitAudioContext)();
          
          // 读取音频数据
          const reader = new FileReader();
          reader.onload = async (e) => {
            try {
              // 解码音频数据
              const arrayBuffer = e.target.result;
              const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
              
              // 转换为WAV格式
              const wavBuffer = this.audioBufferToWav(audioBuffer);
              const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' });
              
              resolve(wavBlob);
            } catch (error) {
              console.error('音频解码失败:', error);
              // 如果转换失败，直接返回原始blob
              resolve(audioBlob);
            }
          };
          
          reader.onerror = () => {
            console.error('读取音频文件失败');
            // 如果读取失败，直接返回原始blob
            resolve(audioBlob);
          };
          
          reader.readAsArrayBuffer(audioBlob);
        } catch (error) {
          console.error('音频转换失败:', error);
          // 如果转换失败，直接返回原始blob
          resolve(audioBlob);
        }
      });
    },

    // 将AudioBuffer转换为WAV格式
    audioBufferToWav(buffer) {
      const length = buffer.length;
      const numberOfChannels = buffer.numberOfChannels;
      const sampleRate = buffer.sampleRate;
      const bytesPerSample = 2; // 16-bit
      const blockAlign = numberOfChannels * bytesPerSample;
      const byteRate = sampleRate * blockAlign;
      const dataSize = length * blockAlign;
      const bufferSize = 44 + dataSize;
      
      const arrayBuffer = new ArrayBuffer(bufferSize);
      const view = new DataView(arrayBuffer);
      
      // WAV文件头
      const writeString = (offset, string) => {
        for (let i = 0; i < string.length; i++) {
          view.setUint8(offset + i, string.charCodeAt(i));
        }
      };
      
      writeString(0, 'RIFF');
      view.setUint32(4, bufferSize - 8, true);
      writeString(8, 'WAVE');
      writeString(12, 'fmt ');
      view.setUint32(16, 16, true); // PCM格式
      view.setUint16(20, 1, true); // 音频格式
      view.setUint16(22, numberOfChannels, true);
      view.setUint32(24, sampleRate, true);
      view.setUint32(28, byteRate, true);
      view.setUint16(32, blockAlign, true);
      view.setUint16(34, 16, true); // 位深度
      writeString(36, 'data');
      view.setUint32(40, dataSize, true);
      
      // 写入音频数据
      let offset = 44;
      for (let i = 0; i < length; i++) {
        for (let channel = 0; channel < numberOfChannels; channel++) {
          const sample = Math.max(-1, Math.min(1, buffer.getChannelData(channel)[i]));
          view.setInt16(offset, sample * 0x7FFF, true);
          offset += 2;
        }
      }
      
      return arrayBuffer;
    },
    
    async sendAudioForRecognition(audioBlob) {
      try {
        // 创建FormData
        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'recording.wav');
        
        // 发送到后端API
        const response = await fetch(`${this.apiBaseUrl}/voice/recognize/`, {
          method: 'POST',
          body: formData
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || '语音识别失败');
        }
        
        const result = await response.json();
        
        if (result.success && result.text) {
          // 将识别结果填入输入框
          this.inputMessage = result.text;
          this.adjustTextareaHeight();
          console.log('语音识别成功:', result.text);
          
          // 显示识别成功提示
          this.showVoiceSuccessMessage(`识别成功: ${result.text}`);
        } else {
          throw new Error(result.message || '语音识别失败');
        }
        
      } catch (error) {
         console.error('语音识别请求失败:', error);
         this.showVoiceErrorMessage(error.message);
       }
    },

    // 处理电话通话音频
    async processPhoneCallAudio(audioBlob) {
      try {
        // 检查是否还在电话通话模式，如果不在则直接返回
        if (!this.isPhoneCallActive) {
          console.log('电话通话已结束，取消音频处理');
          return;
        }
        
        console.log('开始处理电话通话音频...');
        this.showVoiceSuccessMessage('正在处理电话通话...');
        
        // 创建FormData
        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'phone_call.webm');
        formData.append('user_id', this.phoneCallSessionId || 'web_user_' + Date.now());
        
        // 发送到电话接口
        const response = await fetch(`${this.apiBaseUrl}/voice/phone_call/`, {
          method: 'POST',
          body: formData
        });
        
        // 再次检查是否还在电话通话模式
        if (!this.isPhoneCallActive) {
          console.log('电话通话已结束，取消后续处理');
          return;
        }
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`电话接口请求失败: ${response.status} - ${errorText}`);
        }
        
        // 获取响应头中的信息
        const recognizedText = response.headers.get('X-Recognized-Text') || '无法获取识别文本';
        const responseText = response.headers.get('X-Response-Text') || '无法获取回复文本';
        
        console.log('识别文本:', recognizedText);
        console.log('回复文本:', responseText);
        
        // 显示识别结果
        this.showVoiceSuccessMessage(`识别: ${recognizedText}`);
        
        // 获取音频响应并播放
        const audioArrayBuffer = await response.arrayBuffer();
        
        // 再次检查是否还在电话通话模式
        if (!this.isPhoneCallActive) {
          console.log('电话通话已结束，取消音频播放');
          return;
        }
        
        if (audioArrayBuffer.byteLength > 0) {
          // 创建音频上下文并播放
          const audioContext = new (window.AudioContext || window.webkitAudioContext)();
          this.phoneCallAudioContext = audioContext; // 保存引用以便清理
          
          const audioBuffer = await audioContext.decodeAudioData(audioArrayBuffer);
          const source = audioContext.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(audioContext.destination);
          
          // 监听音频播放完成事件
          source.onended = () => {
            console.log('电话通话音频播放完成');
            
            // 检查是否还在电话通话模式
            if (!this.isPhoneCallActive) {
              console.log('电话通话已结束，不继续下一轮');
              return;
            }
            
            this.showVoiceSuccessMessage(`AI回复: ${responseText}`);
            
            // 音频播放完成，持续监听机制会自动继续录音
            console.log('AI回复播放完成，等待持续监听机制继续录音');
          };
          
          source.start();
          
          // 语音对话时不创建气泡，保持界面简洁
          // 注释掉以下代码以避免在语音对话时创建聊天气泡
          /*
          if (recognizedText && responseText) {
            this.messages.push({
              id: Date.now(),
              text: recognizedText,
              isUser: true,
              timestamp: new Date().toLocaleTimeString()
            });
            
            this.messages.push({
              id: Date.now() + 1,
              text: responseText,
              isUser: false,
              timestamp: new Date().toLocaleTimeString(),
              isPhoneCall: true // 标记为电话通话消息
            });
            
            // 滚动到底部
            this.$nextTick(() => {
              this.scrollToBottom();
            });
          }
          */
        } else {
          throw new Error('未收到音频响应');
        }
        
      } catch (error) {
        console.error('电话通话处理失败:', error);
        
        // 检查是否还在电话通话模式
        if (!this.isPhoneCallActive) {
          console.log('电话通话已结束，不显示错误信息');
          return;
        }
        
        this.showVoiceErrorMessage('电话通话失败: ' + error.message);
        
        // 错误处理完成，持续监听机制会自动处理重试
        console.log('电话通话处理出错，持续监听机制会自动重试');
      }
    },

    // 电话通话处理函数
    async handleCallInput() {
      console.log('点击电话按钮...');
      
      // 如果已经在电话通话中，挂断电话
      if (this.isPhoneCallActive) {
        await this.hangUpCall();
        return;
      }
      
      // 开始电话通话
      await this.startPhoneCallMode();
    },

    // 关闭电话模态框
    async closeCallModal() {
      await this.hangUpCall();
      // hangUpCall方法内部已经处理了showCallModal的关闭，这里不需要重复设置
    },

    // 挂断电话（从模态框中调用）
    async hangUpCall() {
      console.log('挂断电话');
      
      // 立即设置通话状态为结束中，防止用户重复点击
      this.callStatus = 'ending';
      
      // 立即停止电话通话状态，防止异步操作继续执行
      this.isPhoneCallActive = false;
      
      try {
        // 停止电话通话
        await this.stopPhoneCall();
        
        // 确保在下一个事件循环中关闭模态框，给异步操作时间完成
        await this.$nextTick();
        
        // 立即关闭电话模态框
        this.showCallModal = false;
        
        // 显示通话结束提示
        this.showVoiceSuccessMessage(`通话已结束，共进行了${this.phoneCallRoundCount}轮对话`);
        
        // 重置通话相关状态
        this.callDuration = 0;
        this.callStartTime = null;
        this.phoneCallRoundCount = 0;
        
        console.log('电话界面已关闭');
        
      } catch (error) {
        console.error('挂断电话时出错:', error);
        // 即使出错也要关闭界面
        this.showCallModal = false;
        this.showVoiceErrorMessage('挂断电话时出现错误');
      }
    },
    
    // 处理静音切换
    handleMuteToggle(isMuted) {
      console.log('静音状态:', isMuted);
      this.isMuted = isMuted;
      
      // 如果正在录音，控制麦克风
      if (this.phoneCallStream) {
        this.phoneCallStream.getAudioTracks().forEach(track => {
          track.enabled = !isMuted;
        });
      }
    },

    // 处理扬声器切换
    handleSpeakerToggle(isSpeakerOn) {
      console.log('扬声器状态:', isSpeakerOn);
      this.isSpeakerOn = isSpeakerOn;
      
      // 控制音频输出设备
      if (this.currentAudio) {
        // 设置音频音量
        this.currentAudio.volume = isSpeakerOn ? 1.0 : 0.5;
        
        // 如果浏览器支持，尝试设置音频输出设备
        if (this.currentAudio.setSinkId && navigator.mediaDevices.enumerateDevices) {
          navigator.mediaDevices.enumerateDevices().then(devices => {
            const audioOutputs = devices.filter(device => device.kind === 'audiooutput');
            if (audioOutputs.length > 1) {
              // 如果有多个音频输出设备，可以在这里切换
              const deviceId = isSpeakerOn ? 'default' : audioOutputs[0].deviceId;
              this.currentAudio.setSinkId(deviceId).catch(err => {
                console.warn('无法切换音频输出设备:', err);
              });
            }
          }).catch(err => {
            console.warn('无法枚举音频设备:', err);
          });
        }
      }
    },

    // 启动通话时长计时器
    startCallTimer() {
      this.callTimer = setInterval(() => {
        if (this.isPhoneCallActive && this.callStartTime) {
          this.callDuration = Math.floor((Date.now() - this.callStartTime) / 1000);
        }
      }, 1000);
    },

    // 停止通话时长计时器
    stopCallTimer() {
      if (this.callTimer) {
        clearInterval(this.callTimer);
        this.callTimer = null;
      }
    },

    // 原来的电话通话处理函数（重命名）
    async startPhoneCallMode() {
      console.log('开始电话通话...');
      
      // 如果已经在电话通话中，停止当前通话
      if (this.isPhoneCallActive) {
        this.stopPhoneCall();
        return;
      }
      
      if (this.isRecording) {
        this.showVoiceErrorMessage('请先停止当前录音再开始电话通话');
        return;
      }
      
      try {
        // 检查浏览器是否支持录音
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          this.showVoiceErrorMessage('您的浏览器不支持录音功能');
          return;
        }
        
        // 显示电话模态框
        this.showCallModal = true;
        this.callStatus = 'connecting';
        
        // 开始电话通话模式
        this.isPhoneCallActive = true;
        this.phoneCallRoundCount = 0;
        this.phoneCallSessionId = 'phone_session_' + Date.now();
        this.callStartTime = Date.now();
        
        // 启动通话计时器
        this.startCallTimer();
        
        this.showVoiceSuccessMessage('电话通话已开始，点击电话按钮可结束通话');
        
        // 设置通话状态为监听
        this.callStatus = 'listening';
        
        // 开始第一轮录音
        await this.startPhoneCallRecording();
        
      } catch (error) {
        console.error('电话通话启动失败:', error);
        this.showVoiceErrorMessage('无法启动电话通话: ' + error.message);
        this.isPhoneCallActive = false;
      }
    },

    // 开始电话通话录音
    async startPhoneCallRecording() {
      try {
        // 防止重复录音
        if (this.isRecording) {
          console.log('已在录音中，跳过重复启动');
          return;
        }
        
        // 检查电话通话状态
        if (!this.isPhoneCallActive) {
          console.log('电话通话已结束，取消录音启动');
          return;
        }
        
        this.isRecording = true;
        this.phoneCallRoundCount++;
        this.showVoiceSuccessMessage(`第${this.phoneCallRoundCount}轮对话 - 开始录音...`);
        
        // 清理之前的音频流（如果存在）
        if (this.phoneCallStream) {
          this.phoneCallStream.getTracks().forEach(track => track.stop());
          this.phoneCallStream = null;
        }
        
        const stream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            sampleRate: 16000,
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          } 
        });
        
        this.phoneCallStream = stream;
        
        // 创建音频分析器用于持续监听音频级别
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        
        analyser.fftSize = 256;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        // 持续音频监听变量
        let silenceCount = 0;
        let hasSound = false;
        let lastSoundTime = Date.now();
        let isProcessingAudio = false;
        
        // 创建MediaRecorder用于录音
        this.mediaRecorder = new MediaRecorder(stream, {
          mimeType: 'audio/webm;codecs=opus'
        });
        
        this.audioChunks = [];
        
        this.mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            this.audioChunks.push(event.data);
            console.log(`音频数据块: ${event.data.size} bytes`);
          }
        };
        
        this.mediaRecorder.onstop = async () => {
          console.log('MediaRecorder停止，开始处理音频');
          isProcessingAudio = true;
          
          try {
            if (this.audioChunks.length === 0) {
              console.log('没有录制到音频数据，继续监听');
              isProcessingAudio = false;
              return;
            }
            
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            console.log(`录制完成，音频大小: ${(audioBlob.size / 1024).toFixed(2)} KB`);
            
            // 处理音频并等待回复完成
            await this.processPhoneCallAudio(audioBlob);
            
          } catch (error) {
            console.error('处理电话音频失败:', error);
            this.showVoiceErrorMessage('电话通话处理失败: ' + error.message);
          } finally {
            isProcessingAudio = false;
            this.isRecording = false;
            
            // 清理当前录音的音频数据
            this.audioChunks = [];
            
            // 如果还在通话中，立即重新开始录音
            if (this.isPhoneCallActive) {
              setTimeout(() => {
                if (this.isPhoneCallActive && !this.isRecording) {
                  this.startPhoneCallRecording();
                }
              }, 100); // 很短的延迟后重新开始录音
            }
          }
        };
        
        this.mediaRecorder.onerror = (event) => {
          console.error('MediaRecorder错误:', event.error);
          this.showVoiceErrorMessage('录音设备错误: ' + event.error.message);
          this.isRecording = false;
          isProcessingAudio = false;
        };
        
        // 持续音频级别监控和自动处理
        const checkAudioLevel = () => {
          if (!this.isPhoneCallActive) {
            audioContext.close();
            return;
          }
          
          // 如果正在处理音频，暂停监听
          if (isProcessingAudio) {
            setTimeout(checkAudioLevel, 50);
            return;
          }
          
          analyser.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((a, b) => a + b) / bufferLength;
          const currentTime = Date.now();
          
          // 检测是否有声音输入（阈值可调整）
          if (average > 15) { // 提高阈值以减少误触发
            if (!hasSound) {
              console.log('开始检测到声音，启动录音');
              hasSound = true;
              // 如果还没开始录音，现在开始
              if (this.mediaRecorder.state === 'inactive') {
                this.mediaRecorder.start();
              }
            }
            lastSoundTime = currentTime;
            silenceCount = 0;
            console.log(`音频级别: ${average.toFixed(2)}`);
          } else {
            silenceCount++;
          }
          
          // 如果检测到声音后静音超过1秒（20 * 50ms），自动处理音频
          if (hasSound && (currentTime - lastSoundTime) > 1000) {
            console.log('检测到1秒静音，自动处理音频');
            
            if (this.mediaRecorder.state === 'recording') {
              this.mediaRecorder.stop();
            }
            
            // 重置状态准备下一轮
            hasSound = false;
            silenceCount = 0;
            lastSoundTime = currentTime;
            
            return; // 停止当前监听循环，等待录音处理完成后重新开始
          }
          
          // 继续监听
          setTimeout(checkAudioLevel, 50); // 每50ms检查一次
        };
        
        // 开始音频级别监控
        console.log('开始持续音频监听');
        checkAudioLevel();
        
        // 不立即开始录音，等待检测到声音时再开始
        console.log('等待检测到声音输入...');
        
      } catch (error) {
        console.error('电话录音启动失败:', error);
        this.showVoiceErrorMessage('无法启动录音: ' + error.message);
        this.isRecording = false;
        
        // 清理资源
        if (this.phoneCallStream) {
          this.phoneCallStream.getTracks().forEach(track => track.stop());
          this.phoneCallStream = null;
        }
        
        // 如果还在通话中，尝试重新开始录音
        if (this.isPhoneCallActive) {
          setTimeout(() => {
            if (this.isPhoneCallActive && !this.isRecording) {
              this.startPhoneCallRecording();
            }
          }, 2000);
        }
      }
    },

    // 停止电话通话
    stopPhoneCall() {
      console.log('停止电话通话');
      
      // 立即设置状态为非活跃，防止其他异步操作继续执行
      this.isPhoneCallActive = false;
      this.isRecording = false;
      
      // 停止录音
      if (this.mediaRecorder) {
        try {
          if (this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
          }
          // 清除mediaRecorder引用
          this.mediaRecorder = null;
        } catch (error) {
          console.warn('停止录音时出错:', error);
        }
      }
      
      // 停止音频流
      if (this.phoneCallStream) {
        try {
          this.phoneCallStream.getTracks().forEach(track => track.stop());
          this.phoneCallStream = null;
        } catch (error) {
          console.warn('停止音频流时出错:', error);
        }
      }
      
      // 清除所有相关的定时器（如果有的话）
      if (this.phoneCallTimeoutId) {
        clearTimeout(this.phoneCallTimeoutId);
        this.phoneCallTimeoutId = null;
      }
      
      // 停止通话时长计时器
      this.stopCallTimer();
      
      // 清除音频上下文（如果有的话）
      if (this.phoneCallAudioContext) {
        try {
          this.phoneCallAudioContext.close();
          this.phoneCallAudioContext = null;
        } catch (error) {
          console.warn('关闭音频上下文时出错:', error);
        }
      }
      
      // 重置电话模态框相关状态（但保留通话时间用于显示）
      this.callStatus = 'connecting';
      // 不在这里重置 callDuration 和 callStartTime，让它们在界面关闭时再重置
      this.isMuted = false;
      this.isSpeakerOn = false;
      
      this.showVoiceSuccessMessage(`电话通话已结束，共进行了${this.phoneCallRoundCount}轮对话`);
      this.phoneCallRoundCount = 0;
      this.phoneCallSessionId = null;
    },

    goToSchoolHomepage() {
       console.log('导航到学校首页');
       // 导航到西安工程大学官网
       window.open('https://www.xpu.edu.cn/', '_blank');
     },

    // APP下载模态框相关方法
    showAppDownload() {
      this.showAppModal = true;
    },

    closeAppModal() {
      this.showAppModal = false;
    },

    // 语音错误提示相关方法
    showVoiceErrorMessage(message) {
      this.voiceErrorMessage = message;
      this.showVoiceError = true;
      // 3秒后自动关闭错误提示
      setTimeout(() => {
        this.closeVoiceError();
      }, 3000);
    },

    showVoiceSuccessMessage(message) {
        this.voiceSuccessMessage = message;
        this.showVoiceSuccess = true;
        
        // 3秒后自动关闭
        setTimeout(() => {
          this.showVoiceSuccess = false;
        }, 3000);
      },
      
      closeVoiceSuccess() {
        this.showVoiceSuccess = false;
      },
      
      closeVoiceError() {
        this.showVoiceError = false;
        this.voiceErrorMessage = '';
      },

    goToLogin() {
      this.$router.push('/login');
    },

    // 复制功能相关方法
    showCopyButton(messageId) {
      this.hoveredMessageId = messageId;
    },

    hideCopyButton() {
      this.hoveredMessageId = null;
    },

    async copyMessage(content) {
      try {
        // 移除HTML标签，只复制纯文本
        const textContent = content.replace(/<[^>]*>/g, '');
        await navigator.clipboard.writeText(textContent);
        
        // 可以添加复制成功的提示
        console.log('消息已复制到剪贴板');
        
        // 这里可以添加一个临时的成功提示
        // 例如显示一个toast消息
      } catch (err) {
        console.error('复制失败:', err);
        // 降级方案：使用传统的复制方法
        this.fallbackCopyTextToClipboard(content.replace(/<[^>]*>/g, ''));
      }
    },

    fallbackCopyTextToClipboard(text) {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      
      // 避免滚动到底部
      textArea.style.top = "0";
      textArea.style.left = "0";
      textArea.style.position = "fixed";

      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();

      try {
        const successful = document.execCommand('copy');
        if (successful) {
          console.log('消息已复制到剪贴板（降级方案）');
        } else {
          console.error('复制失败');
        }
      } catch (err) {
        console.error('复制失败:', err);
      }

      document.body.removeChild(textArea);
    },

    // 添加拖拽事件监听器
    addDragListeners() {
      const chatArea = this.$refs.chatArea || document.querySelector('.chat-area');
      const inputArea = document.querySelector('.input-area');
      
      if (chatArea) {
        chatArea.addEventListener('dragenter', this.handleDragEnter);
        chatArea.addEventListener('dragover', this.handleDragOver);
        chatArea.addEventListener('dragleave', this.handleDragLeave);
        chatArea.addEventListener('drop', this.handleDrop);
      }
      
      if (inputArea) {
        inputArea.addEventListener('dragenter', this.handleDragEnter);
        inputArea.addEventListener('dragover', this.handleDragOver);
        inputArea.addEventListener('dragleave', this.handleDragLeave);
        inputArea.addEventListener('drop', this.handleDrop);
      }
    },

    // 移除拖拽事件监听器
    removeDragListeners() {
      const chatArea = this.$refs.chatArea || document.querySelector('.chat-area');
      const inputArea = document.querySelector('.input-area');
      
      if (chatArea) {
        chatArea.removeEventListener('dragenter', this.handleDragEnter);
        chatArea.removeEventListener('dragover', this.handleDragOver);
        chatArea.removeEventListener('dragleave', this.handleDragLeave);
        chatArea.removeEventListener('drop', this.handleDrop);
      }
      
      if (inputArea) {
        inputArea.removeEventListener('dragenter', this.handleDragEnter);
        inputArea.removeEventListener('dragover', this.handleDragOver);
        inputArea.removeEventListener('dragleave', this.handleDragLeave);
        inputArea.removeEventListener('drop', this.handleDrop);
      }
    },

    // 处理拖拽进入事件
    handleDragEnter(e) {
      e.preventDefault();
      e.stopPropagation();
      this.dragCounter++;
      if (this.dragCounter === 1) {
        this.isDragOver = true;
      }
    },

    // 处理拖拽悬停事件
    handleDragOver(e) {
      e.preventDefault();
      e.stopPropagation();
      e.dataTransfer.dropEffect = 'copy';
    },

    // 处理拖拽离开事件
    handleDragLeave(e) {
      e.preventDefault();
      e.stopPropagation();
      this.dragCounter--;
      if (this.dragCounter === 0) {
        this.isDragOver = false;
      }
    },

    // 处理文件拖拽放置事件
    handleDrop(e) {
      e.preventDefault();
      e.stopPropagation();
      this.dragCounter = 0;
      this.isDragOver = false;
      
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        this.processDroppedFiles(files);
      }
    },

    // 处理拖拽放置的文件
    processDroppedFiles(files) {
      const allowedTypes = [
        'text/plain',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'audio/mpeg',
        'audio/mp3',
        'audio/wav',
        'video/mp4'
      ];

      let fileTexts = [];
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // 检查文件类型
        if (!allowedTypes.includes(file.type) && !this.isAllowedFileExtension(file.name)) {
          console.warn(`不支持的文件类型: ${file.name}`);
          continue;
        }
        
        // 检查文件大小 (限制为50MB)
        if (file.size > 50 * 1024 * 1024) {
          console.warn(`文件过大: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`);
          continue;
        }
        
        console.log('拖拽上传文件:', file.name, '大小:', file.size, '类型:', file.type);
        
        // 将文件添加到uploadedFiles数组中
        this.uploadedFiles.push(file);
      }
      
      if (this.uploadedFiles.length > 0) {
        // 聚焦到输入框
        this.$nextTick(() => {
          if (this.$refs.messageInput) {
            this.$refs.messageInput.focus();
          }
        });
      }
    },

    // 检查文件扩展名
    isAllowedFileExtension(filename) {
      const allowedExtensions = ['.txt', '.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4', '.wav'];
      const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));
      return allowedExtensions.includes(extension);
    },

    // 移除文件
    removeFile(index) {
      this.uploadedFiles.splice(index, 1);
    },

    // 获取文件图标类型
    getFileIconType(filename) {
      const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));
      
      switch (extension) {
        case '.pdf':
          return 'file-pdf';
        case '.doc':
        case '.docx':
          return 'file-word';
        case '.txt':
          return 'file-text';
        case '.jpg':
        case '.jpeg':
        case '.png':
        case '.gif':
          return 'file-image';
        case '.mp3':
        case '.wav':
          return 'file-audio';
        default:
          return 'file-default';
      }
    }
  }
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
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 侧边栏收起状态 */
.sidebar.collapsed {
  width: 0;
  min-width: 0;
  overflow: hidden;
}

.sidebar-header {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(229, 229, 229, 0.3);
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: 70px; /* 设置实际高度为70px */
  box-sizing: border-box; /* 确保padding包含在高度内 */
}

.header-buttons {
  display: flex;
  align-items: center;
  justify-content: center; /* 水平居中 */
  gap: 8px;
  width: 100%;
  height: 100%; /* 占满父容器高度 */
  padding-top: 5px; /* 稍微向下一点点 */
}

/* 收起按钮样式 */
.collapse-btn {
  width: 36px;
  height: 36px;
  background: transparent;
  border: none;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: #4A90E2;
  /* 移除 align-self: flex-end，让按钮跟随父容器居中 */
}

.collapse-btn:hover {
  background: rgba(74, 144, 226, 0.2);
  transform: translateY(-1px);
}

/* 收起状态下的按钮居中 */
.sidebar.collapsed .sidebar-header {
  align-items: center;
}

.sidebar.collapsed .collapse-btn {
  align-self: center;
}

.new-chat-btn {
  flex: 1;
  padding: 8px 12px;
  background: linear-gradient(135deg, #4A90E2 0%, #5BA7F7 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(74, 144, 226, 0.3);
  white-space: nowrap;
}

.new-chat-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(74, 144, 226, 0.4);
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

/* 对话列表骨架屏 */
.skeleton-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 12px;
}
.skeleton-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--skeleton-base);
}
.skeleton-lines { flex: 1; }
.skeleton-line {
  height: 10px;
  border-radius: 6px;
  background: var(--skeleton-base);
  margin-bottom: 8px;
}
.skeleton-line:last-child { margin-bottom: 0; }

/* 闪烁渐变动画 */
.shimmer {
  background-image: linear-gradient(90deg,
    var(--skeleton-base) 0%,
    var(--skeleton-base) 35%,
    var(--skeleton-highlight) 50%,
    var(--skeleton-base) 65%,
    var(--skeleton-base) 100%
  );
  background-size: 200% 100%;
  animation: shimmerMove 1.4s ease-in-out infinite;
}
@keyframes shimmerMove {
  0% { background-position: -100% 0; }
  100% { background-position: 100% 0; }
}

/* 颜色变量（亮/暗） */
:root {
  --skeleton-base: rgba(0,0,0,0.06);
  --skeleton-highlight: rgba(255,255,255,0.6);
}
body.dark {
  --skeleton-base: rgba(255,255,255,0.12);
  --skeleton-highlight: rgba(255,255,255,0.24);
}

/* 对话列表滚动条样式 */
.conversation-list::-webkit-scrollbar {
  width: 6px;
}

.conversation-list::-webkit-scrollbar-track {
  background: transparent;
  border-radius: 3px;
}

.conversation-list::-webkit-scrollbar-thumb {
  background: rgba(74, 144, 226, 0.3);
  border-radius: 3px;
  transition: background 0.3s ease;
}

.conversation-list::-webkit-scrollbar-thumb:hover {
  background: rgba(74, 144, 226, 0.5);
}

.conversation-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  border-left: 3px solid transparent;
  position: relative;
}

.conversation-item:hover {
  background: rgba(248, 249, 250, 0.8);
  transform: translateX(4px);
}

.conversation-item.active {
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.15), rgba(91, 167, 247, 0.15));
  border-left-color: #4A90E2;
  box-shadow: 0 4px 12px rgba(74, 144, 226, 0.2);
}

.conv-content {
  flex: 1;
  min-width: 0;
}

.conv-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-time {
  font-size: 12px;
  color: #999;
}

.delete-btn {
  opacity: 0;
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.3s ease;
}

.conversation-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: #ff4757;
  background: rgba(255, 71, 87, 0.1);
}

/* 主内容区域 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  position: relative;
}

/* 展开侧边栏按钮 */
.expand-sidebar-btn {
  position: absolute;
  top: 15px;
  left: 20px;
  z-index: 1000;
  width: 36px;
  height: 36px;
  background: transparent;
  border: none;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: #4A90E2;
}

.expand-sidebar-btn:hover {
  background: rgba(74, 144, 226, 0.2);
  transform: translateY(-1px);
}

/* 顶部导航栏 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(229, 229, 229, 0.3);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  height: 70px; /* 设置实际高度为70px */
  box-sizing: border-box; /* 确保padding包含在高度内 */
}

.chat-title {
  display: flex;
  align-items: center;
  transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  height: 50px; /* 与logo高度一致 */
}

/* 侧边栏收起时logo向右移动 */
.sidebar.collapsed ~ .main-content .chat-title {
  margin-left: 60px;
}

.title-icon {
  font-size: 20px;
  font-weight: 600;
  background: linear-gradient(135deg, #4A90E2 0%, #5BA7F7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Logo 容器：亮色渐变 / 暗色发光 */
.logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 50px;
  padding: 6px 10px;
  border-radius: 12px;
}
.logo img { display: block; }
.logo-light {
  background: linear-gradient(135deg, #ffffff 0%, #f3f7ff 100%);
  box-shadow: 0 4px 14px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.6);
}
.logo-dark {
  background: transparent;
  filter: drop-shadow(0 0 10px rgba(91,167,247,0.6)) drop-shadow(0 4px 12px rgba(0,0,0,0.4));
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 50px; /* 与左侧chat-title高度一致 */
}

/* 主题标签样式 */
.theme-label {
  font-size: 14px;
  color: #333;
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

/* 用户菜单样式 - 更新为TDesign触发器样式 */
.user-menu-trigger {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.user-menu-trigger:hover {
  background: rgba(74, 144, 226, 0.1);
}

/* 用户头像样式 */
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid rgba(255, 255, 255, 0.2);
}

.user-avatar:hover {
  transform: scale(1.05);
  border-color: rgba(74, 144, 226, 0.5);
  box-shadow: 0 4px 12px rgba(74, 144, 226, 0.2);
}

/* 用户名样式 - 与主题标签样式保持一致 */
.username {
  font-size: 14px;
  color: #333;
  font-weight: 500;
  transition: color 0.3s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

/* 下拉箭头样式 */
.dropdown-icon {
  transition: transform 0.3s ease;
  color: #666;
}

.user-menu-trigger:hover .dropdown-icon {
  transform: rotate(180deg);
}

/* TDesign下拉菜单自定义样式 */
:deep(.user-dropdown-popup) {
  z-index: 999999 !important;
}

:deep(.user-dropdown-popup .t-dropdown__menu) {
  background: rgba(255, 255, 255, 0.98) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(229, 229, 229, 0.3) !important;
  border-radius: 12px !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15) !important;
  min-width: 140px !important;
  padding: 4px !important;
}

:deep(.user-dropdown-popup .t-dropdown__item) {
  border-radius: 8px !important;
  margin: 2px !important;
  padding: 12px 16px !important;
  transition: all 0.3s ease !important;
}

:deep(.user-dropdown-popup .t-dropdown__item:hover) {
  background: rgba(74, 144, 226, 0.1) !important;
  color: #4A90E2 !important;
}

@keyframes dropdownFadeIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 用户信息区域 */
.user-info {
  padding: 16px;
  text-align: center;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
  text-align: center;
}

.user-email {
  font-size: 12px;
  color: #999;
  text-align: center;
}

/* 菜单分割线 */
.menu-divider {
  height: 1px;
  background: rgba(229, 229, 229, 0.5);
  margin: 0 12px;
}

/* 菜单项样式 */
.menu-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px 16px;
  background: none;
  border: none;
  color: #666;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  border-radius: 0 0 12px 12px;
}

.menu-item:hover {
  background: rgba(74, 144, 226, 0.1);
  color: #4A90E2;
}

.menu-item svg {
  transition: color 0.3s ease;
}

/* 聊天区域 */
.chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.02) 0%, rgba(91, 167, 247, 0.02) 100%);
}

/* 聊天区骨架屏 */
.skeleton-chat {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}
.skeleton-bubble {
  height: 18px;
  border-radius: 16px;
  background: var(--skeleton-base);
}

/* 聊天区域滚动条样式 */
.chat-area::-webkit-scrollbar {
  width: 6px;
}

.chat-area::-webkit-scrollbar-track {
  background: transparent;
  border-radius: 3px;
}

.chat-area::-webkit-scrollbar-thumb {
  background: rgba(74, 144, 226, 0.3);
  border-radius: 3px;
  transition: background 0.3s ease;
}

.chat-area::-webkit-scrollbar-thumb:hover {
  background: rgba(74, 144, 226, 0.5);
}

/* 消息样式 */
.message {
  margin-bottom: 24px;
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
  align-items: center;
  margin-bottom: 8px;
  gap: 8px;
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

/* 用户消息容器 */
.user-message-container {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  margin-left: auto;
  max-width: 70%;
}

.message-content {
  background: linear-gradient(135deg, #4A90E2 0%, #357ABD 100%);
  color: white;
  padding: 12px 16px;
  border-radius: 18px 18px 4px 18px;
  max-width: 100%;
  word-wrap: break-word;
  box-shadow: 0 2px 8px rgba(74, 144, 226, 0.3);
  position: relative;
  line-height: 1.5;
  font-size: 14px;
  margin: 0;
}

/* 消息操作按钮容器 - 外部显示在气泡右下方 */
.message-actions-external {
  display: flex;
  gap: 4px;
  margin-top: 6px;
  justify-content: flex-end;
  align-items: center;
}

/* 消息操作按钮容器 - 内联显示在气泡右下方 */
.message-actions-inline {
  position: absolute;
  bottom: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
  z-index: 10;
  opacity: 0.8;
}

.message-actions-inline .action-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  padding: 2px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  color: white;
}

.message-actions-inline .action-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  opacity: 1;
}

/* 消息操作按钮容器 */
.message-actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  justify-content: flex-end;
}

/* 操作按钮样式 */
.action-btn {
  background: transparent;
  border: none;
  border-radius: 4px;
  padding: 4px;
  cursor: pointer;
  transition: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  color: #666;
}

.action-btn:hover {
  background: rgba(0,0,0,0.05);
  color: #333;
  transition: var(--transition-fast);
}



/* 用户消息内容包装器 */
.message-content-wrapper {
  position: relative;
  display: flex;
  align-items: flex-end;
  margin-left: auto;
  max-width: 70%;
}

.message.user .message-content {
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.15), rgba(91, 167, 247, 0.15));
  color: #333;
  border: 1px solid rgba(74, 144, 226, 0.2);
  flex: 1;
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

/* 智能体消息样式 - 气泡格式 */
.assistant-message {
  margin-bottom: 24px;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  max-width: 85%;
}

.assistant-message-container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
}

.assistant-message-content {
  background: rgba(248, 248, 248, 0.95);
  border: 1px solid rgba(229, 229, 229, 0.3);
  border-radius: 18px;
  padding: 12px 16px;
  line-height: 1.6;
  font-size: 14px;
  color: #333;
  position: relative;
  max-width: 100%;
  word-wrap: break-word;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.2s ease;
}

.assistant-message-content:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.12);
}

/* 消息操作按钮 - 位于气泡外部左下方 */
.message-actions-external {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  margin-top: 6px;
  margin-left: 8px;
  gap: 8px;
}

/* 深色模式下的智能体消息气泡 */
body.dark .assistant-message-content {
  background: rgba(55, 55, 55, 0.95);
  border-color: rgba(70, 70, 70, 0.3);
  color: #ffffff;
}

.copy-btn, .action-btn {
  background: transparent;
  border: none;
  border-radius: 4px;
  padding: 4px;
  cursor: pointer;
  transition: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  color: #666;
}

.copy-btn:hover, .action-btn:hover {
  background: rgba(0,0,0,0.06);
}

/* 深色模式下的按钮样式 */
body.dark .copy-btn, body.dark .action-btn {
  background: transparent;
  border: none;
  color: #cccccc;
}

body.dark .copy-btn:hover, body.dark .action-btn:hover {
  background: rgba(255,255,255,0.12);
  color: #fff;
}

/* 智能体消息复制按钮 - 现在在底部操作区域中 */
.assistant-copy-btn {
  position: static;
  z-index: auto;
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
  text-align: center;
  padding: 40px 20px;
}

.welcome-message {
  margin-bottom: 40px;
}

.welcome-message h2 {
  font-size: 24px;
color: #333;
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

/* 文件预览区域 */
.file-preview-area {
  margin-bottom: 12px;
  padding: 12px;
  background: rgba(248, 249, 250, 0.8);
  border: 1px solid rgba(229, 229, 229, 0.5);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  max-width: fit-content; /* 让宽度适应内容 */
  min-width: 300px; /* 设置最小宽度 */
}

.file-preview-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(229, 229, 229, 0.3);
  border-radius: 8px;
  margin-bottom: 8px;
  transition: all 0.2s ease;
}

.file-preview-item:last-child {
  margin-bottom: 0;
}

.file-preview-item:hover {
  background: rgba(255, 255, 255, 1);
  border-color: #4A90E2;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(74, 144, 226, 0.1);
}

.file-name {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  font-size: 12px;
  color: #666;
  margin-left: auto;
}

.remove-file-btn {
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.1);
  color: #333;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  transition: all 0.2s ease;
  margin-left: 8px;
}

.remove-file-btn:hover {
  background: rgba(0, 0, 0, 0.2);
  transform: scale(1.1);
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
  /* 保持内层边框为中性颜色，避免出现有色内框 */
  border-color: rgba(229, 229, 229, 0.3);
  /* 可保留轻微外层提升感，如需完全无色可将 box-shadow 置为 none */
  box-shadow: none;
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

/* 移除 textarea 自身的聚焦描边与发光，避免出现内层有色框 */
.message-input:focus,
.message-input:focus-visible {
  outline: none;
  box-shadow: none;
  border: none;
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
  gap: 6px;
  flex-direction: row;
  flex-wrap: nowrap;
}

.attachment-btn,
.voice-btn,
.call-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #666;
}

.attachment-btn:hover,
.voice-btn:hover,
.call-btn:hover {
  background: rgba(74, 144, 226, 0.1);
  color: #4A90E2;
  transform: scale(1.05);
}

.voice-btn.recording {
  background: rgba(255, 71, 87, 0.1);
  color: #ff4757;
  animation: pulse 1.5s ease-in-out infinite;
  position: relative;
}

.call-btn.active {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  animation: pulse 1.5s ease-in-out infinite;
  position: relative;
}

.voice-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.recording-indicator,
.phone-indicator {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 8px;
  height: 8px;
  background: #ff4757;
  border-radius: 50%;
  animation: blink 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.3; }
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #4A90E2 0%, #5BA7F7 100%);
  color: white;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(74, 144, 226, 0.3);
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 4px 15px rgba(74, 144, 226, 0.4);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* 顶部导航栏按钮样式 */
.header-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #4A90E2;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 8px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.header-btn:hover {
  background: rgba(74, 144, 226, 0.1);
  transform: translateY(-1px);
}

/* 深色模式样式 */
body.dark {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

body.dark .header-btn {
  background: transparent;
  color: #ffffff;
}

body.dark .header-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

body.dark .collapse-btn {
  background: transparent;
  color: #ffffff;
}

body.dark .collapse-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

body.dark .expand-sidebar-btn {
  background: transparent;
  color: #ffffff;
}

body.dark .expand-sidebar-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

body.dark .app {
  background: linear-gradient(135deg, rgba(26, 26, 46, 0.9) 0%, rgba(22, 33, 62, 0.9) 100%);
}

body.dark .sidebar {
  background: rgba(26, 26, 46, 0.95);
  border-right-color: rgba(96, 96, 96, 0.3);
}

body.dark .main-content {
  background: rgba(26, 26, 46, 0.8);
}

body.dark .header {
  background: rgba(22, 33, 62, 0.95);
  border-bottom-color: rgba(96, 96, 96, 0.3);
}

body.dark .chat-area {
  background: linear-gradient(135deg, rgba(26, 26, 46, 0.2) 0%, rgba(15, 52, 96, 0.2) 100%);
}

/* 深色模式下的滚动条样式 */
body.dark .conversation-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
}

body.dark .conversation-list::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

body.dark .chat-area::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
}

body.dark .chat-area::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

body.dark .conv-title {
  color: #ffffff;
}

body.dark .theme-label {
  color: #cccccc;
}

body.dark .TDesign-switch {
  background: #4A90E2;
}

body.dark .TDesign-switch__handle {
  transform: translateX(20px);
}

/* 深色模式下的用户菜单样式 */
body.dark .user-menu-trigger:hover {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 8px;
}

body.dark .username {
  color: #f0f0f0;
}

body.dark .dropdown-icon {
  color: #d0d0d0;
}

body.dark .user-dropdown {
  background: rgba(45, 45, 45, 0.95);
  border-color: rgba(96, 96, 96, 0.3);
}

body.dark .user-name {
  color: #ffffff;
}

body.dark .user-email {
  color: #cccccc;
}

body.dark .menu-divider {
  background: rgba(96, 96, 96, 0.3);
}

body.dark .menu-item {
  color: #cccccc;
}

body.dark .menu-item:hover {
  background: rgba(74, 144, 226, 0.2);
  color: #5BA7F7;
}

/* 深色模式下的TDesign下拉菜单样式 - 增强优先级 */
body.dark :deep(.t-dropdown__popup .t-dropdown__menu),
body.dark :deep(.user-dropdown-popup .t-dropdown__menu) {
  background: rgba(28, 32, 40, 0.98) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6) !important;
}

body.dark :deep(.t-dropdown__popup .t-dropdown__item),
body.dark :deep(.user-dropdown-popup .t-dropdown__item) {
  color: #f0f0f0 !important;
  transition: all 0.3s ease !important;
  border-radius: 6px !important;
}

body.dark :deep(.t-dropdown__popup .t-dropdown__item:hover),
body.dark :deep(.user-dropdown-popup .t-dropdown__item:hover) {
  background: rgba(74, 144, 226, 0.25) !important;
  color: #ffffff !important;
  transform: translateY(-1px);
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

/* 深色模式下的操作按钮样式 */
body.dark .action-btn {
  background: transparent;
  border: none;
  color: #cccccc;
}

/* 深色模式下的复制按钮样式 - 与用户按钮保持一致 */
body.dark .copy-btn {
  background: transparent;
  border: none;
  color: #cccccc;
}

/* 深色模式下的编辑图标颜色 */
body.dark .edit-icon {
  stroke: #cccccc !important;
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

body.dark .attachment-btn,
body.dark .voice-btn,
body.dark .call-btn {
  background: transparent;
  color: #cccccc;
}

body.dark .attachment-btn:hover,
body.dark .voice-btn:hover,
body.dark .call-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

body.dark .conversation-item:hover {
  background: rgba(64, 64, 64, 0.6);
}

body.dark .conversation-item.active {
  background: linear-gradient(135deg, rgba(74, 144, 226, 0.25), rgba(91, 167, 247, 0.25));
  border-left-color: #4A90E2;
}

/* 流式输出指示器样式 */
.streaming-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.typing-dots {
  display: inline-flex;
  gap: 4px;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  background: #4A90E2;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) {
  animation-delay: 0s;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

.streaming-text {
  font-size: 12px;
  color: #666;
  font-style: italic;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: scale(1);
    opacity: 0.5;
  }
  30% {
    transform: scale(1.2);
    opacity: 1;
  }
}

/* 深色模式下的流式指示器 */
body.dark .typing-dots span {
  background: #5BA7F7;
}

body.dark .streaming-text {
  color: #999;
}

/* APP下载模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 0;
  max-width: 400px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  animation: modalSlideIn 0.3s ease-out;
}

.modal-header {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #eee;
  background: white;
  color: #333;
  position: relative;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #333;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  position: absolute;
  right: 24px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.1);
}

.modal-body {
  padding: 30px 24px;
  text-align: center;
}

.app-clients {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-bottom: 0;
  flex-wrap: nowrap;
}

.client-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.app-qr-image {
  width: 150px;
  height: 150px;
  object-fit: contain;
  margin-bottom: 12px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.client-item p {
  margin: 0;
  color: #333;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.5;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* 深色模式下的模态框样式 */
body.dark .modal-content {
  background: #2d2d2d;
  color: #ffffff;
}

body.dark .modal-header {
  background: #2d2d2d;
  border-bottom-color: #444;
  color: #ffffff;
}

body.dark .close-btn {
  color: #ffffff;
}

body.dark .close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

body.dark .client-item p {
  color: #ffffff;
}

/* 语音提示容器样式 */
.voice-alerts-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10000;
  max-width: 400px;
}

.voice-message {
  margin-bottom: 8px;
  animation: slideInRight 0.3s ease-out;
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 深色模式下的 t-message 组件样式 */
body.dark .voice-alerts-container .t-message {
  background: rgba(45, 45, 45, 0.95) !important;
  border: 1px solid rgba(96, 96, 96, 0.4) !important;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
  color: #ffffff !important;
}

/* 深色模式下成功消息样式 */
body.dark .voice-alerts-container .t-message--success {
  background: rgba(45, 45, 45, 0.95) !important;
  border-color: rgba(82, 196, 26, 0.4) !important;
  color: #ffffff !important;
}

body.dark .voice-alerts-container .t-message--success .t-message__content {
  color: #ffffff !important;
}

body.dark .voice-alerts-container .t-message--success .t-icon {
  color: #52c41a !important;
}

/* 深色模式下错误消息样式 */
body.dark .voice-alerts-container .t-message--error {
  background: rgba(45, 45, 45, 0.95) !important;
  border-color: rgba(255, 77, 79, 0.4) !important;
  color: #ffffff !important;
}

body.dark .voice-alerts-container .t-message--error .t-message__content {
  color: #ffffff !important;
}

body.dark .voice-alerts-container .t-message--error .t-icon {
  color: #ff4d4f !important;
}

/* 深色模式下警告消息样式 */
body.dark .voice-alerts-container .t-message--warning {
  background: rgba(45, 45, 45, 0.95) !important;
  border-color: rgba(250, 173, 20, 0.4) !important;
  color: #ffffff !important;
}

body.dark .voice-alerts-container .t-message--warning .t-message__content {
  color: #ffffff !important;
}

body.dark .voice-alerts-container .t-message--warning .t-icon {
  color: #faad14 !important;
}

/* 深色模式下信息消息样式 */
body.dark .voice-alerts-container .t-message--info {
  background: rgba(45, 45, 45, 0.95) !important;
  border-color: rgba(24, 144, 255, 0.4) !important;
  color: #ffffff !important;
}

body.dark .voice-alerts-container .t-message--info .t-message__content {
  color: #ffffff !important;
}

body.dark .voice-alerts-container .t-message--info .t-icon {
  color: #1890ff !important;
}

/* 拖拽上传样式 */
.chat-area {
  position: relative;
}

.chat-area.drag-over {
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  background: rgba(255, 255, 255, 0.2);
  transition: backdrop-filter 0.3s ease;
}


.drag-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(74, 144, 226, 0.1);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  border: 2px dashed #4A90E2;
  border-radius: 12px;
  animation: dragOverlayFadeIn 0.2s ease-out;
}

.drag-content {
  text-align: center;
  color: #4A90E2;
  padding: 40px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(74, 144, 226, 0.2);
  max-width: 400px;
}

.drag-icon {
  margin-bottom: 16px;
  opacity: 0.8;
}

.drag-content h3 {
  margin: 0 0 12px 0;
  font-size: 18px;
  font-weight: 600;
  color: #4A90E2;
}

.drag-content p {
  margin: 8px 0;
  font-size: 14px;
  color: #666;
  line-height: 1.5;
}

@keyframes dragOverlayFadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* 深色模式下的拖拽样式 */
body.dark .chat-area.drag-over {
  background: rgba(74, 144, 226, 0.1);
}

body.dark .drag-overlay {
  background: rgba(74, 144, 226, 0.15);
  border-color: #5BA7F7;
}

body.dark .drag-content {
  background: rgba(45, 45, 45, 0.95);
  color: #5BA7F7;
}

body.dark .drag-content h3 {
  color: #5BA7F7;
}

body.dark .drag-content p {
  color: #ccc;
}

/* 输入区域拖拽样式 */
.input-area.drag-over {
  background: rgba(74, 144, 226, 0.1);
  border-color: #4A90E2;
}

body.dark .input-area.drag-over {
  background: rgba(74, 144, 226, 0.15);
  border-color: #5BA7F7;
}

/* 深色模式下关闭按钮样式 */
body.dark .voice-alerts-container .t-message .t-message__close {
  color: #ffffff !important;
  background: transparent !important;
  border: none !important;
  opacity: 0.8;
}

body.dark .voice-alerts-container .t-message .t-message__close:hover {
  color: #ffffff !important;
  background: rgba(255, 255, 255, 0.1) !important;
  opacity: 1;
}
/* 拖入文件时模糊整个聊天区背景 */
.chat-area.drag-over {
  position: relative;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.15);
  transition: backdrop-filter 0.3s ease, background 0.3s ease;
  border-radius: 16px;
  overflow: hidden;
}

/* 文件消息样式 */
.file-message {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-name {
  font-weight: 500;
  color: #333;
  font-size: 14px;
  word-break: break-all;
}

.file-size {
  font-size: 12px;
  color: #666;
}

/* 深色模式下的文件消息样式 */
body.dark .file-preview-area {
  background: rgba(45, 55, 72, 0.8);
  border: 1px solid rgba(74, 85, 104, 0.5);
}

body.dark .file-preview-item {
  background: rgba(26, 32, 44, 0.9);
  border: 1px solid rgba(74, 85, 104, 0.3);
}

body.dark .file-preview-item:hover {
  background: rgba(26, 32, 44, 1);
  border-color: #4A90E2;
  box-shadow: 0 2px 8px rgba(74, 144, 226, 0.2);
}

body.dark .file-preview-item svg {
  color: #ffffff !important;
  stroke: #ffffff !important;
}

body.dark .file-name {
  color: #ffffff;
}

body.dark .file-size {
  color: #ccc;
}

body.dark .remove-file-btn {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

body.dark .remove-file-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 全局深色模式下拉菜单样式覆盖 */
body.dark :deep(.t-popup),
body.dark :deep(.t-dropdown),
body.dark :deep(.t-dropdown__popup) {
  --td-bg-color-container: rgba(28, 32, 40, 0.98) !important;
  --td-text-color-primary: #f0f0f0 !important;
  --td-bg-color-container-hover: rgba(74, 144, 226, 0.25) !important;
}

body.dark :deep(.t-dropdown__menu) {
  background: rgba(28, 32, 40, 0.98) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6) !important;
}

body.dark :deep(.t-dropdown__item) {
  color: #f0f0f0 !important;
  background: transparent !important;
}

body.dark :deep(.t-dropdown__item:hover) {
  background: rgba(74, 144, 226, 0.25) !important;
  color: #ffffff !important;
}


</style>
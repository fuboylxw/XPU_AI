<template>
  <div class="call-modal-overlay" @click="handleOverlayClick">
    <div class="call-modal" :class="{ 'dark-mode': isDarkMode }" role="dialog" aria-modal="true" aria-label="语音通话对话框" tabindex="-1">
      <!-- 智能体头像/Logo区域 -->
      <div class="avatar-section">
        <div class="avatar-container">
          <!-- 这里将放置智能体的SVG Logo -->
          <div class="avatar-placeholder">
            <img src="../components/logo4.svg" alt="智能体Logo" />
          </div>
          <!-- 通话状态指示器 -->
          <div class="call-status-indicator" :class="callStatus">
            <div class="pulse-ring"></div>
            <div class="pulse-ring delay-1"></div>
            <div class="pulse-ring delay-2"></div>
          </div>
        </div>
        
        <!-- 通话状态文本 -->
        <p class="call-status-text">
          <span v-if="callStatus === 'connecting'">正在连接...</span>
          <span v-else-if="callStatus === 'listening'">请说话...</span>
          <span v-else-if="callStatus === 'speaking'">织语正在回复...</span>
          <span v-else-if="callStatus === 'ending'">正在结束通话...</span>
          <span v-else>通话中</span>
        </p>
        
        <!-- 通话时长 - 只要不是连接状态就显示 -->
        <p class="call-duration" v-if="callStatus !== 'connecting' && callDuration >= 0">{{ formatDuration(callDuration) }}</p>
      </div>
      
      <!-- 语音交互提示：改为三个动态小圆点 -->
      <div class="voice-hint" v-if="callStatus === 'listening'">
        <div class="dots-indicator" aria-label="正在聆听">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>
      </div>
      
      <!-- AI回复提示 -->
      <div class="ai-speaking-hint" v-if="callStatus === 'speaking'">
        <div class="speaking-indicator">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>
      </div>
      
      <!-- 控制按钮区域 -->
      <div class="controls-section">
        <!-- 静音按钮 -->
        <button 
          ref="muteBtn"
          class="control-btn mute-btn" 
          @click="toggleMute" 
          :class="{ active: isMuted, disabled: callStatus === 'ending' }" 
          :disabled="callStatus === 'ending'"
          :title="callStatus === 'ending' ? '通话结束中...' : (isMuted ? '取消静音' : '静音')"
          :aria-pressed="isMuted"
          aria-label="静音切换"
        >
          <Icon 
            :type="isMuted ? 'mute-on-icon' : 'mute-off-icon'"
            :fill-color="'transparent'" 
            :stroke-color="'currentColor'" 
            :stroke-width="2"
            :size="24"
          />
        </button>
        
        <!-- 挂断按钮 -->
        <button 
          ref="hangupBtn"
          class="hang-up-btn" 
          @click="handleHangUp" 
          :class="{ disabled: callStatus === 'ending' }"
          :disabled="callStatus === 'ending'"
          :title="callStatus === 'ending' ? '通话结束中...' : '结束通话'"
          aria-label="结束通话"
        >
          <Icon 
            type="call-cancel"
            :fill-color="'transparent'" 
            :stroke-color="'currentColor'" 
            :stroke-width="2"
            :size="28"
          />
        </button>
        
        <!-- 扬声器按钮 -->
        <button 
          ref="speakerBtn"
          class="control-btn speaker-btn" 
          @click="toggleSpeaker" 
          :class="{ active: isSpeakerOn, disabled: callStatus === 'ending' }" 
          :disabled="callStatus === 'ending'"
          :title="callStatus === 'ending' ? '通话结束中...' : (isSpeakerOn ? '关闭扬声器' : '开启扬声器')"
          :aria-pressed="isSpeakerOn"
          aria-label="扬声器切换"
        >
          <Icon 
            :type="isSpeakerOn ? 'speaker-on-icon' : 'speaker-off-icon'"
            :fill-color="'transparent'" 
            :stroke-color="'currentColor'" 
            :stroke-width="2"
            :size="24"
          />
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import Icon from '../components/Icon.vue'

export default {
  name: 'CallModal',
  components: {
    Icon
  },
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    callStatus: {
      type: String,
      default: 'connecting', // connecting, connected, speaking, listening, ending
      validator: value => ['connecting', 'connected', 'speaking', 'listening', 'ending'].includes(value)
    },
    callDuration: {
      type: Number,
      default: 0
    },
    isMuted: {
      type: Boolean,
      default: false
    },
    isSpeakerOn: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      isDarkMode: false
    }
  },
  computed: {
    callStatusText() {
      const statusMap = {
        connecting: '正在连接...',
        connected: '通话中',
        speaking: '正在说话...',
        listening: '正在聆听...',
        ending: '正在结束通话...'
      }
      return statusMap[this.callStatus] || '通话中'
    }
  },
  mounted() {
    this.checkDarkMode()
    // 监听主题变化
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaQuery.addListener(this.checkDarkMode)
    }
    // 监听body类变化
    this.observeBodyClass()
    
    // 添加ESC键监听
    document.addEventListener('keydown', this.handleKeyDown)
  },
  
  beforeUnmount() {
    // 移除ESC键监听
    document.removeEventListener('keydown', this.handleKeyDown)
  },
  
  watch: {
    // 监听通话状态变化，确保在结束状态时能够正确处理
    callStatus(newStatus) {
      if (newStatus === 'ending') {
        console.log('通话状态变为结束中，准备关闭界面')
        // 可以在这里添加额外的清理逻辑
      }
    },
    
    // 监听visible属性变化
    visible(newVisible) {
      if (!newVisible) {
        console.log('通话界面即将关闭')
        // 确保界面关闭时的清理工作
        this.$nextTick(() => {
          // 强制触发DOM更新，确保界面完全关闭
          this.$forceUpdate();
        });
      } else {
        // 当模态打开时，设置初始焦点并启用键盘聚焦控制
        this.$nextTick(() => {
          this.focusFirstControl();
        });
      }
    }
  },
  methods: {
    checkDarkMode() {
      // 检查body是否有dark类
      this.isDarkMode = document.body.classList.contains('dark') || 
                       window.matchMedia('(prefers-color-scheme: dark)').matches
    },
    
    observeBodyClass() {
      // 使用MutationObserver监听body类的变化
      const observer = new MutationObserver(() => {
        this.checkDarkMode()
      })
      observer.observe(document.body, {
        attributes: true,
        attributeFilter: ['class']
      })
    },
    
    handleOverlayClick(event) {
      // 点击遮罩层关闭模态框并挂断电话
      if (event.target === event.currentTarget) {
        this.handleHangUp()
      }
    },
    
    handleKeyDown(event) {
      // 如果按下Tab键，在模态内部循环焦点
      if (event.key === 'Tab') {
        // 仅在模态可见时处理
        if (!this.visible) return
        event.preventDefault()
        const focusOrder = [this.$refs.muteBtn, this.$refs.hangupBtn, this.$refs.speakerBtn].filter(Boolean)
        if (focusOrder.length === 0) return
        const active = document.activeElement
        const idx = focusOrder.findIndex(el => el === active)
        let nextIndex = 0
        if (idx === -1) {
          nextIndex = 0
        } else if (event.shiftKey) {
          nextIndex = (idx - 1 + focusOrder.length) % focusOrder.length
        } else {
          nextIndex = (idx + 1) % focusOrder.length
        }
        const nextEl = focusOrder[nextIndex]
        if (nextEl && typeof nextEl.focus === 'function') {
          nextEl.focus()
        }
        return
      }

      // ESC键关闭模态框并挂断电话
      if (event.key === 'Escape') {
        this.handleHangUp()
      }
    },

    focusFirstControl() {
      // 设置初始聚焦到挂断按钮（最显著的控制）
      this.$nextTick(() => {
        try {
          const el = this.$refs.hangupBtn || this.$refs.muteBtn || this.$refs.speakerBtn
          if (el && typeof el.focus === 'function') {
            el.focus()
          }
        } catch (e) {
          // ignore
        }
      })
    },
    
    handleHangUp() {
      this.$emit('hang-up')
    },
    
    toggleMute() {
      this.$emit('mute-toggle', !this.isMuted)
    },
    
    toggleSpeaker() {
      this.$emit('speaker-toggle', !this.isSpeakerOn)
    },
    
    formatDuration(seconds) {
      const mins = Math.floor(seconds / 60)
      const secs = seconds % 60
      return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
  }
}
</script>

<style scoped>
.call-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 80px;
  z-index: 9999;
  animation: fadeIn 0.3s ease-out;
}

.call-modal {
  background: linear-gradient(135deg, rgba(26, 26, 46, 0.95) 0%, rgba(22, 33, 62, 0.95) 100%);
  border-radius: 24px;
  padding: 60px 32px 48px;
  min-width: 320px;
  max-width: 400px;
  min-height: 600px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease-out;
  color: white;
  position: relative;
  overflow: hidden;
}

/* 浅色模式 */
.call-modal:not(.dark-mode) {
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  color: #333;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

/* 头像区域 */
.avatar-section {
  margin-bottom: 40px;
  margin-top: 30px;
}

.avatar-container {
  position: relative;
  display: inline-block;
  margin-bottom: 24px;
}

.avatar-placeholder {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: white; /* 修改为白色背景 */
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  position: relative;
  z-index: 2;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1); /* 调整阴影颜色 */
}

.avatar-placeholder img {
  width: 80px;
  height: 80px;
  object-fit: contain;
}

/* 通话状态指示器 */
.call-status-indicator {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 140px;
  height: 140px;
  pointer-events: none;
}

.pulse-ring {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: 2px solid rgba(74, 144, 226, 0.6);
  border-radius: 50%;
  animation: pulse 2s cubic-bezier(0.455, 0.03, 0.515, 0.955) infinite;
}

.pulse-ring.delay-1 {
  animation-delay: 0.5s;
}

.pulse-ring.delay-2 {
  animation-delay: 1s;
}

/* 不同状态的指示器颜色 */
.call-status-indicator.connected .pulse-ring {
  border-color: rgba(34, 197, 94, 0.6);
}

.call-status-indicator.speaking .pulse-ring {
  border-color: rgba(249, 115, 22, 0.6);
  animation-duration: 1s;
}

.call-status-indicator.listening .pulse-ring {
  border-color: rgba(168, 85, 247, 0.6);
  animation-duration: 1.5s;
}

/* 智能体名称 */
.agent-name {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: inherit;
}

/* 通话状态文本 */
.call-status-text {
  font-size: 16px;
  margin: 0 0 8px 0;
  opacity: 0.8;
  color: inherit;
}

/* 通话时长 */
.call-duration {
  font-size: 14px;
  margin: 0;
  opacity: 0.6;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
  color: inherit;
}

/* 控制按钮区域 */
.controls-section {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 40px;
  padding: 0 20px;
  margin-top: 200px; 
}

/* 通用控制按钮样式 */
.control-btn {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.control-btn svg {
  width: 28px;
  height: 28px;
  stroke-width: 2.5;
}

.control-btn:hover {
  transform: scale(1.05);
  background: rgba(255, 255, 255, 0.25);
}

.control-btn:hover svg {
  stroke-width: 3;
}

.control-btn.active {
  background: rgba(74, 144, 226, 0.9);
}

.control-btn.active svg {
  stroke-width: 3;
}

/* 禁用状态样式 */
.control-btn.disabled,
.hang-up-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.control-btn.disabled:hover,
.hang-up-btn.disabled:hover {
  transform: none;
  background: rgba(255, 255, 255, 0.15);
}

/* 浅色模式下的按钮样式 */
.call-modal:not(.dark-mode) .control-btn {
  background: rgba(0, 0, 0, 0.08);
  color: #333;
}

.call-modal:not(.dark-mode) .control-btn:hover {
  background: rgba(0, 0, 0, 0.12);
}

.call-modal:not(.dark-mode) .control-btn svg {
}

/* 挂断按钮 */
.hang-up-btn {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.hang-up-btn:hover {
  transform: scale(1.05);
}

.hang-up-btn:active {
  transform: scale(0.95);
}

/* 按钮波纹效果 */
.hang-up-btn::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: translate(-50%, -50%);
  transition: width 0.3s, height 0.3s;
}

.hang-up-btn:active::before {
  width: 100%;
  height: 100%;
}

/* 动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  100% {
    transform: scale(1.2);
    opacity: 0;
  }
}

@keyframes wave {
  0%, 100% {
    transform: scaleY(1);
  }
  50% {
    transform: scaleY(1.5);
  }
}

/* AI回复提示样式 */
.ai-speaking-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 16px 0;
  opacity: 0.8;
}

.speaking-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
}

.speaking-indicator .dot {
  width: 8px;
  height: 8px;
  background: currentColor;
  border-radius: 50%;
  animation: speaking 1.4s ease-in-out infinite;
}

.speaking-indicator .dot:nth-child(1) { animation-delay: 0s; }
.speaking-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.speaking-indicator .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes speaking {
  0%, 60%, 100% {
    transform: scale(1);
    opacity: 0.5;
  }
  30% {
    transform: scale(1.2);
    opacity: 1;
  }
}

/* 语音交互提示样式 */
.voice-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 16px 0;
  opacity: 0.8;
}

.voice-hint-text {
  font-size: 14px;
  color: inherit;
}

.wave-animation {
  display: flex;
  align-items: center;
  gap: 2px;
}

.wave-bar {
  width: 3px;
  height: 16px;
  background: currentColor;
  border-radius: 2px;
  animation: wave 1.2s ease-in-out infinite;
}

.wave-bar:nth-child(1) { animation-delay: 0s; }
.wave-bar:nth-child(2) { animation-delay: 0.1s; }
.wave-bar:nth-child(3) { animation-delay: 0.2s; }
.wave-bar:nth-child(4) { animation-delay: 0.3s; }
.wave-bar:nth-child(5) { animation-delay: 0.4s; }

/* 三个点指示器（用于监听状态） */
.dots-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
}
.dots-indicator .dot {
  width: 8px;
  height: 8px;
  background: currentColor;
  border-radius: 50%;
  animation: speaking 1.4s ease-in-out infinite;
}
.dots-indicator .dot:nth-child(1) { animation-delay: 0s; }
.dots-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.dots-indicator .dot:nth-child(3) { animation-delay: 0.4s; }

/* 响应式设计 */
@media (max-width: 480px) {
  .call-modal {
    margin: 20px;
    min-width: auto;
    width: calc(100vw - 40px);
    padding: 32px 24px 24px;
  }
  
  .avatar-placeholder {
    width: 100px;
    height: 100px;
  }
  
  .call-status-indicator {
    width: 120px;
    height: 120px;
  }
  
  .agent-name {
    font-size: 20px;
  }
  
  .hang-up-btn {
    width: 56px;
    height: 56px;
  }
}

/* 深色模式特定样式 */
.call-modal.dark-mode .avatar-placeholder {
  box-shadow: 0 8px 32px rgba(74, 144, 226, 0.4);
}

/* 移除空规则，避免样式校验报错 */
</style>
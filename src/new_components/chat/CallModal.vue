<template>
  <div class="call-modal-overlay" @click="handleOverlayClick">
    <div class="call-modal" :class="{ 'dark-mode': isDarkMode }">
      <div class="avatar-section">
        <div class="avatar-container">
          <div class="avatar-placeholder">
            <img src="/src/components/logo4.svg" alt="智能体Logo" />
          </div>
          <div class="call-status-indicator" :class="callStatus">
            <div class="pulse-ring"></div>
            <div class="pulse-ring delay-1"></div>
            <div class="pulse-ring delay-2"></div>
          </div>
        </div>
        <p class="call-status-text">
          <span v-if="callStatus === 'connecting'">正在连接...</span>
          <span v-else-if="callStatus === 'listening'">请说话...</span>
          <span v-else-if="callStatus === 'speaking'">织语正在回复...</span>
          <span v-else-if="callStatus === 'ending'">正在结束通话...</span>
          <span v-else>通话中</span>
        </p>
        <p class="call-duration" v-if="callStatus !== 'connecting' && displayDuration >= 0">{{ formatDuration(displayDuration) }}</p>
      </div>
      <div class="ai-speaking-hint" v-if="callStatus === 'speaking'">
        <div class="speaking-indicator">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>
      </div>
      <div class="controls-section">
        <button 
          class="control-btn mute-btn" 
          @click="toggleMute" 
          :class="{ active: isMuted, disabled: callStatus === 'ending' }" 
          :disabled="callStatus === 'ending'"
          :title="callStatus === 'ending' ? '通话结束中...' : (isMuted ? '取消静音' : '静音')"
        >
          <Icon 
            :type="isMuted ? 'mute-on-icon' : 'mute-off-icon'"
            :fill-color="'transparent'" 
            :stroke-color="'currentColor'" 
            :stroke-width="2"
            :size="24"
          />
        </button>
        <button 
          class="hang-up-btn" 
          @click="handleHangUp" 
          :class="{ disabled: callStatus === 'ending' }"
          :disabled="callStatus === 'ending'"
          :title="callStatus === 'ending' ? '通话结束中...' : '结束通话'"
        >
          <Icon 
            type="call-cancel"
            :fill-color="'transparent'" 
            :stroke-color="'currentColor'" 
            :stroke-width="2"
            :size="28"
          />
        </button>
        <button 
          class="control-btn speaker-btn" 
          @click="toggleSpeaker" 
          :class="{ active: isSpeakerOn, disabled: callStatus === 'ending' }" 
          :disabled="callStatus === 'ending'"
          :title="callStatus === 'ending' ? '通话结束中...' : (isSpeakerOn ? '关闭扬声器' : '开启扬声器')"
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
import Icon from '../common/Icon.vue'

export default {
  name: 'CallModal',
  components: { Icon },
  props: {
    visible: { type: Boolean, default: false },
    callStatus: { type: String, default: 'connecting' },
    callDuration: { type: Number, default: 0 },
    isMuted: { type: Boolean, default: false },
    isSpeakerOn: { type: Boolean, default: false }
  },
  data() { return { isDarkMode: false, timerId: null, elapsedSeconds: 0, durationOffset: 0 } },
  computed: { displayDuration() { return (this.durationOffset || 0) + (this.elapsedSeconds || 0) } },
  mounted() { this.checkDarkMode(); if (window.matchMedia) { const mq = window.matchMedia('(prefers-color-scheme: dark)'); mq.addListener(this.checkDarkMode) } document.addEventListener('keydown', this.handleKeyDown); this.syncTimerWithStatus() },
  beforeUnmount() { document.removeEventListener('keydown', this.handleKeyDown); this.stopTimer() },
  watch: { callStatus() { this.syncTimerWithStatus() }, visible(v) { if (!v) { this.$nextTick(() => { this.$forceUpdate() }); this.stopTimer() } else { this.syncTimerWithStatus() } } },
  methods: {
    checkDarkMode() { this.isDarkMode = document.body.classList.contains('dark') || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) },
    handleOverlayClick(e) { if (e.target === e.currentTarget) { this.handleHangUp() } },
    handleKeyDown(e) { if (e.key === 'Escape') { this.handleHangUp() } },
    handleHangUp() { this.$emit('hang-up') },
    toggleMute() { this.$emit('mute-toggle', !this.isMuted) },
    toggleSpeaker() { this.$emit('speaker-toggle', !this.isSpeakerOn) },
    formatDuration(s) { const m = Math.floor(s/60); const ss = s%60; return `${m.toString().padStart(2,'0')}:${ss.toString().padStart(2,'0')}` },
    startTimer() { if (this.timerId) return; this.durationOffset = this.callDuration || 0; this.elapsedSeconds = 0; this.timerId = setInterval(() => { this.elapsedSeconds += 1 }, 1000) },
    stopTimer() { if (this.timerId) { clearInterval(this.timerId); this.timerId = null } },
    syncTimerWithStatus() { const run = this.visible !== false && ['connected','speaking','listening'].includes(this.callStatus); if (run) { this.startTimer() } else { this.stopTimer() } }
  }
}
</script>

<style scoped>
.call-modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); backdrop-filter: blur(10px); display: flex; align-items: center; justify-content: center; z-index: 9999; }
.call-modal { background: linear-gradient(135deg, rgba(26,26,46,0.95) 0%, rgba(22,33,62,0.95) 100%); border-radius: 24px; padding: 60px 32px 48px; min-width: 320px; max-width: 400px; min-height: 600px; text-align: center; color: white; position: relative; overflow: hidden; }
.call-modal:not(.dark-mode) { background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); color: #333; }
.avatar-section { margin-bottom: 40px; margin-top: 30px; }
.avatar-container { position: relative; display: inline-block; margin-bottom: 24px; }
.avatar-placeholder { width: 120px; height: 120px; border-radius: 50%; background: white; display: flex; align-items: center; justify-content: center; margin: 0 auto; position: relative; z-index: 2; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
.avatar-placeholder img { width: 80px; height: 80px; object-fit: contain; }
.call-status-indicator { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 140px; height: 140px; pointer-events: none; }
.pulse-ring { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 2px solid rgba(74,144,226,0.6); border-radius: 50%; animation: pulse 2s cubic-bezier(0.455, 0.03, 0.515, 0.955) infinite; }
.pulse-ring.delay-1 { animation-delay: 0.5s; }
.pulse-ring.delay-2 { animation-delay: 1s; }
.call-status-indicator.connected .pulse-ring { border-color: rgba(34,197,94,0.6); }
.call-status-indicator.speaking .pulse-ring { border-color: rgba(249,115,22,0.6); animation-duration: 1s; }
.call-status-indicator.listening .pulse-ring { border-color: rgba(168,85,247,0.6); animation-duration: 1.5s; }
.call-status-text { font-size: 16px; margin: 0 0 8px 0; opacity: 0.8; }
.call-duration { font-size: 14px; margin: 0; opacity: 0.6; font-family: monospace; }
.controls-section { display: flex; justify-content: center; align-items: center; gap: 40px; padding: 0 20px; margin-top: 200px; }
.control-btn { width: 56px; height: 56px; border-radius: 50%; border: none; background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s ease; }
.control-btn:hover { transform: scale(1.05); background: rgba(255,255,255,0.25); }
.control-btn.active { background: rgba(74,144,226,0.9); }
.control-btn.disabled { opacity: 0.5; cursor: not-allowed; pointer-events: none; }
.hang-up-btn { width: 64px; height: 64px; border-radius: 50%; border: none; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s ease; position: relative; overflow: hidden; }
.hang-up-btn:hover { transform: scale(1.05); }
.hang-up-btn:active { transform: scale(0.95); }
@keyframes pulse { 0% { transform: scale(1); opacity: 1; } 100% { transform: scale(1.2); opacity: 0; } }
@keyframes speaking { 0%, 60%, 100% { transform: scale(1); opacity: 0.5; } 30% { transform: scale(1.2); opacity: 1; } }
.call-modal:not(.dark-mode) .control-btn { background: rgba(0,0,0,0.08); color: #333; }
.call-modal:not(.dark-mode) .control-btn:hover { background: rgba(0,0,0,0.12); }
</style>
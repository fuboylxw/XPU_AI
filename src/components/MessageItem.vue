<template>
  <div class="message-item" :class="message.type">
    <!-- User message -->
    <div v-if="isUser" class="user-message-container">
      <div class="message-content" v-if="message.fileInfo">
        <Icon :type="fileIcon" :size="20" :fill-color="'transparent'" :stroke-color="'currentColor'" :stroke-width="2" />
        <div class="file-details">
          <div class="file-name">{{ message.fileInfo.name }}</div>
          <div class="file-size">{{ (message.fileInfo.size / 1024 / 1024).toFixed(2) }} MB</div>
        </div>
      </div>
      <div class="message-content" v-else>
        {{ message.content }}
      </div>
      <div class="message-actions-external">
        <button class="action-btn edit-btn" @click="$emit('edit', message)" title="编辑消息">
          <Icon type="edit" :fill-color="'transparent'" :stroke-color="'currentColor'" :stroke-width="2" :size="16" />
        </button>
        <button class="action-btn copy-btn" @click="$emit('copy', message.content)" title="复制消息">
          <Icon type="copy" :fill-color="'transparent'" :stroke-color="'currentColor'" :stroke-width="2" :size="16" />
        </button>
      </div>
    </div>
    <!-- Assistant message -->
    <div v-else class="assistant-message-container">
      <div class="assistant-message-content" v-html="rendered"></div>
      <div class="message-actions-external">
        <div v-if="message.streaming" class="streaming-indicator">
          <span class="typing-dots"><span></span><span></span><span></span></span>
          <span class="streaming-text">正在生成回答...</span>
        </div>
        <button v-else class="action-btn copy-btn" @click="$emit('copy', message.content)" title="复制消息">
          <Icon type="copy" :fill-color="'transparent'" :stroke-color="'currentColor'" :stroke-width="2" :size="16" />
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import Icon from './Icon.vue'
import { renderMarkdown } from '@/utils/markdown.js'

export default {
  name: 'MessageItem',
  components: { Icon },
  props: {
    message: { type: Object, required: true }
  },
  computed: {
    isUser() { return this.message.type === 'user' },
    rendered() { return this.isUser ? '' : renderMarkdown(this.message.content || '') },
    fileIcon() {
      if (!this.message.fileInfo) return 'file-default'
      const name = this.message.fileInfo.name || ''
      const ext = name.split('.').pop().toLowerCase()
      const map = { pdf: 'file-pdf', doc: 'file-word', docx: 'file-word', txt: 'file-text', jpg: 'file-image', jpeg: 'file-image', png: 'file-image', gif: 'file-image', mp3: 'file-audio', wav: 'file-audio' }
      return map[ext] || 'file-default'
    }
  }
}
</script>

<style scoped>
.message-item { margin-bottom: var(--space-4); }
.user-message-container, .assistant-message-container { position: relative; }
.assistant-message-content :deep(pre.md-code) { background: #0f172a; color: #f1f5f9; padding: var(--space-3); border-radius: var(--radius-md); overflow-x: auto; }
.typing-dots { display: inline-flex; gap: 4px; }
.typing-dots span { width: 6px; height: 6px; background: var(--color-primary); border-radius: 50%; animation: bounce 1s infinite ease-in-out; }
.typing-dots span:nth-child(2){ animation-delay:.2s } .typing-dots span:nth-child(3){ animation-delay:.4s }
@keyframes bounce { 0%,80%,100% { transform: scale(.4); opacity:.6 } 40% { transform: scale(1); opacity:1 } }
</style>

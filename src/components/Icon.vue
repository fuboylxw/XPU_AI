<template>
  <svg 
    :width="size" 
    :height="size" 
    viewBox="0 0 24 24" 
    :fill="fillColor" 
    :stroke="strokeColor" 
    :stroke-width="strokeWidth" 
    stroke-linecap="round" 
    stroke-linejoin="round"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- Copy Icon -->
    <template v-if="type === 'copy'">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
    </template>

    <!-- Download Icon -->
    <template v-else-if="type === 'download'">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7,10 12,15 17,10"/>
      <line x1="12" y1="15" x2="12" y2="3"/>
    </template>

    <!-- Edit Icon -->
    <template v-else-if="type === 'edit'">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
      <path d="m18.5 2.5 a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
    </template>

    <!-- Stop Circle Icon -->
    <template v-else-if="type === 'stop'">
      <circle cx="12" cy="12" r="10"/>
      <rect x="9" y="9" width="6" height="6"/>
    </template>

    <!-- Send Icon (新增) -->
    <template v-else-if="type === 'send'">
      <line x1="22" y1="2" x2="11" y2="13"></line>
      <polygon points="22,2 15,22 11,13 2,9 22,2"></polygon>
    </template>

    <!-- Plus Icon (新增) -->
    <template v-else-if="type === 'plus'">
      <line x1="12" y1="5" x2="12" y2="19"></line>
      <line x1="5" y1="12" x2="19" y2="12"></line>
    </template>

    <!-- Menu Icon (新增) -->
    <template v-else-if="type === 'menu'">
      <line x1="3" y1="6" x2="21" y2="6"></line>
      <line x1="3" y1="12" x2="21" y2="12"></line>
      <line x1="3" y1="18" x2="21" y2="18"></line>
    </template>

    <!-- Menu Fold Icon (从MenuFoldIcon.vue合并) -->
    <template v-else-if="type === 'menu-fold'">
      <line x1="3" y1="6" x2="21" y2="6"></line>
      <line x1="3" y1="12" x2="21" y2="12"></line>
      <line x1="3" y1="18" x2="21" y2="18"></line>
    </template>

    <!-- Trash Icon (新增) -->
    <template v-else-if="type === 'trash'">
      <polyline points="3,6 5,6 21,6"></polyline>
      <path d="m19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"></path>
    </template>

    <!-- Call Icon (从Call1Icon.vue合并) -->
    <template v-else-if="type === 'call'">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
    </template>

    <!-- Call Cancel Icon (从CallCancelIcon.vue合并) -->
    <template v-else-if="type === 'call-cancel'">
      <!-- 电话听筒形状 -->
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
      <!-- 挂断的斜线 -->
      <line x1="18" y1="6" x2="6" y2="18" :stroke="strokeColor" :stroke-width="strokeWidth + 0.5"/>
    </template>

    <!-- File Icons (从FileIcon.vue合并，去掉视频图标) -->
    <!-- PDF 图标 -->
    <template v-else-if="type === 'file-pdf'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="14,2 14,8 20,8" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="16" y1="13" x2="8" y2="13" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="16" y1="17" x2="8" y2="17" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="10" y1="9" x2="8" y2="9" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>

    <!-- Word 文档图标 -->
    <template v-else-if="type === 'file-word'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="14,2 14,8 20,8" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="16" y1="13" x2="8" y2="13" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="16" y1="17" x2="8" y2="17" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="10,9 9,9 8,9 8,10 8,11 8,12 8,13" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>

    <!-- 文本文件图标 -->
    <template v-else-if="type === 'file-text'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="#38A169" stroke="#38A169" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <polyline points="14,2 14,8 20,8" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <text x="12" y="16" text-anchor="middle" fill="white" font-size="5" font-weight="bold">TXT</text>
    </template>

    <!-- 图片文件图标 -->
    <template v-else-if="type === 'file-image'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="14,2 14,8 20,8" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <rect x="8" y="10" width="8" height="6" rx="1" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <circle cx="10" cy="12" r="1" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="14,14 12,12 10,14" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>

    <!-- 音频文件图标 -->
    <template v-else-if="type === 'file-audio'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="14,2 14,8 20,8" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <circle cx="12" cy="13" r="2" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <path d="M12 11v6" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <path d="M16 13v2a4 4 0 0 1-8 0v-2" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>

    <!-- 默认文件图标 -->
    <template v-else-if="type === 'file-default'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="14,2 14,8 20,8" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="16" y1="13" x2="8" y2="13" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="16" y1="17" x2="8" y2="17" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>

 <!-- 微信语音通话风：打开静音 icon -->
<template v-else-if="type === 'mute-on-icon'">
  <!-- 麦克风禁用（带斜杠） -->
  <circle cx="12" cy="12" r="10" stroke="currentColor" fill="none" stroke-width="2" />
  <path d="M9 9v2a3 3 0 0 0 5.24 2.12M15 11V9a3 3 0 0 0-5.68-1.33" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
  <line x1="8" y1="8" x2="16" y2="16" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
</template>

<!-- 微信语音通话风：取消静音 icon -->
<template v-else-if="type === 'mute-off-icon'">
  <!-- 正常麦克风 -->
  <circle cx="12" cy="12" r="10" stroke="currentColor" fill="none" stroke-width="2" />
  <path d="M12 15a3 3 0 0 0 3-3V9a3 3 0 0 0-6 0v3a3 3 0 0 0 3 3Z" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
  <path d="M8 11a4 4 0 0 0 8 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
  <line x1="12" y1="15" x2="12" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
</template>

<!-- 微信语音通话风：打开扬声器 icon -->
<template v-else-if="type === 'speaker-on-icon'">
  <!-- 扬声器 + 声波 -->
  <circle cx="12" cy="12" r="10" stroke="currentColor" fill="none" stroke-width="2" />
  <polygon points="10 9 6 11 6 13 10 15 10 9" stroke="currentColor" fill="none" stroke-width="2" stroke-linejoin="round" />
  <path d="M14 10a3 3 0 0 1 0 4M16 8a6 6 0 0 1 0 8" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none" />
</template>

<!-- 微信语音通话风：关闭扬声器 icon -->
<template v-else-if="type === 'speaker-off-icon'">
  <!-- 扬声器 + 斜杠去声波 -->
  <circle cx="12" cy="12" r="10" stroke="currentColor" fill="none" stroke-width="2" />
  <polygon points="10 9 6 11 6 13 10 15 10 9" stroke="currentColor" fill="none" stroke-width="2" stroke-linejoin="round" />
  <line x1="8" y1="8" x2="16" y2="16" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
</template>

<!-- 用户对话图标 -->
<template v-else-if="type === 'user-talk-1-icon'">
  <!-- 用户头像 - 更大更清晰 -->
  <circle cx="12" cy="10" r="5" :stroke="strokeColor" :stroke-width="strokeWidth" fill="none" />
  <!-- 用户面部特征 -->
  <circle cx="10" cy="9" r="1" :fill="strokeColor" />
  <circle cx="14" cy="9" r="1" :fill="strokeColor" />
  <path d="M10 12 Q12 14 14 12" :stroke="strokeColor" :stroke-width="strokeWidth" fill="none" />
  <!-- 身体轮廓 -->
  <path d="M7 22v-3a5 5 0 0 1 5-5h0a5 5 0 0 1 5 5v3" :stroke="strokeColor" :stroke-width="strokeWidth" fill="none" />
  <!-- 对话气泡 - 更明显 -->
  <ellipse cx="18" cy="8" rx="4" ry="3" :stroke="strokeColor" :stroke-width="strokeWidth" fill="white" />
  <path d="M16 10 L15 12" :stroke="strokeColor" :stroke-width="strokeWidth" />
  <!-- 气泡内的点点 -->
  <circle cx="17" cy="7.5" r="0.5" :fill="strokeColor" />
  <circle cx="18.5" cy="7.5" r="0.5" :fill="strokeColor" />
  <circle cx="19" cy="8.5" r="0.5" :fill="strokeColor" />
</template>

    <!-- Rollback Icon (退出登录图标) -->
    <template v-else-if="type === 'rollback-icon'">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="16,17 21,12 16,7" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="21" y1="12" x2="9" y2="12" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>

    <!-- User Circle Icon (用户头像图标) -->
    <template v-else-if="type === 'user-circle-icon'">
      <circle cx="12" cy="12" r="10" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <circle cx="12" cy="10" r="3" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <path d="M7 20.662V20a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v.662" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>

    <!-- 默认图标 (如果type不匹配) -->
    <template v-else>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <circle cx="12" cy="12" r="2" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <path d="M9 12h6" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <path d="M12 9v6" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>
  </svg>
</template>

<script>
export default {
  name: 'Icon',
  props: {
    type: {
      type: String,
      required: true,
      validator: (value) => {
        return ['copy', 'download', 'edit', 'stop', 'send', 'plus', 'menu', 'menu-fold', 'trash', 'call', 'call-cancel', 'file-pdf', 'file-word', 'file-text', 'file-image', 'file-audio', 'file-default', 'loudspeaker-icon', 'sound-mute-icon', 'sound-mute-1-icon', 'sound-icon', 'mute-on-icon', 'mute-off-icon', 'speaker-on-icon', 'speaker-off-icon', 'user-talk-1-icon', 'rollback-icon', 'user-circle-icon'].includes(value)
      }
    },
    size: {
      type: [String, Number],
      default: 20
    },
    fillColor: {
      type: String,
      default: 'transparent'
    },
    strokeColor: {
      type: String,
      default: 'currentColor'
    },
    strokeWidth: {
      type: [String, Number],
      default: 2
    }
  }
}
</script>

<style scoped>
svg {
  display: inline-block;
  vertical-align: middle;
}
</style>
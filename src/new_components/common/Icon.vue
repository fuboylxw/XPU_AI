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
    <template v-if="type === 'copy'">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
    </template>
    <template v-else-if="type === 'download'">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7,10 12,15 17,10"/>
      <line x1="12" y1="15" x2="12" y2="3"/>
    </template>
    <template v-else-if="type === 'edit'">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
      <path d="m18.5 2.5 a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
    </template>
    <template v-else-if="type === 'stop'">
      <circle cx="12" cy="12" r="10"/>
      <rect x="9" y="9" width="6" height="6"/>
    </template>
    <template v-else-if="type === 'send'">
      <line x1="22" y1="2" x2="11" y2="13"></line>
      <polygon points="22,2 15,22 11,13 2,9 22,2"></polygon>
    </template>
    <template v-else-if="type === 'plus'">
      <g id="anjchat-add">
        <path id="stroke1" d="M21.5 11V17H6.5L2.5 20.5V3H13" stroke-linecap="square" stroke-width="2" stroke="currentColor"></path>
        <path id="stroke2" d="M20 1V4M20 4V7M20 4H17M20 4H23" stroke-linecap="square" stroke-width="2" stroke="currentColor"></path>
      </g>
    </template>
    <template v-else-if="type === 'menu'">
      <line x1="3" y1="6" x2="21" y2="6"></line>
      <line x1="3" y1="12" x2="21" y2="12"></line>
      <line x1="3" y1="18" x2="21" y2="18"></line>
    </template>
    <template v-else-if="type === 'menu-fold'">
      <line x1="3" y1="6" x2="21" y2="6"></line>
      <line x1="3" y1="12" x2="21" y2="12"></line>
      <line x1="3" y1="18" x2="21" y2="18"></line>
    </template>
    <template v-else-if="type === 'home-icon'">
      <path d="M3 9l9-7 9 7"></path>
      <path d="M5 10v10a2 2 0 0 0 2 2h3a2 2 0 0 0 2-2v-6h2v6a2 2 0 0 0 2 2h3a2 2 0 0 0 2-2V10"></path>
    </template>
    <template v-else-if="type === 'chevron-down'">
      <polyline points="6,9 12,15 18,9"></polyline>
    </template>
    <template v-else-if="type === 'more-horizontal'">
      <circle cx="6" cy="12" r="2"/>
      <circle cx="12" cy="12" r="2"/>
      <circle cx="18" cy="12" r="2"/>
    </template>
    <template v-else-if="type === 'rename-square'">
      <path d="M3.00049 21.0007L7.50024 20.9998L17.5002 10.9998L13.0002 6.5L3.0005 16.4998L3.00049 21.0007Z" fill="transparent"/>
      <path d="M21.5 7L17 2.5L13 6.5L17.5 10.9998L21.5 7Z" fill="transparent"/>
      <path d="M13.0002 6.5L3.0005 16.4998L3.00049 21.0007L7.50024 20.9998L17.5002 10.9998M13.0002 6.5L17.0002 2.5L21.5002 7L17.5002 10.9998M13.0002 6.5L17.5002 10.9998" stroke="currentColor" stroke-width="2" stroke-linecap="square"/>
      <path d="M21 21.0008L14 21" stroke="currentColor" stroke-width="2" stroke-linecap="square"/>
    </template>
    <template v-else-if="type === 'delete-bin-square'">
      <path d="M5 5H19L18.5 22H5.5L5 5Z" fill="transparent"/>
      <path d="M5 5H19M5 5L5.5 22H18.5L19 5M5 5H3M19 5H21M8.5 2H15.5V5H8.5V2Z" stroke="currentColor" stroke-width="2" stroke-linecap="square"/>
      <path d="M14.8287 10.6716L12.0003 13.5001M12.0003 13.5001L9.17188 16.3285M12.0003 13.5001L9.17188 10.6716M12.0003 13.5001L14.8287 16.3285" stroke="currentColor" stroke-width="2" stroke-linecap="square"/>
    </template>
    <template v-else-if="type === 'home-variant'">
      <path d="M3 10L12 2.5L21 10V21H3V10Z" fill="transparent" stroke="currentColor" stroke-width="2" stroke-linecap="square"/>
      <path d="M9 14H15V21H9V14Z" fill="transparent" stroke="currentColor" stroke-width="2" stroke-linecap="square"/>
    </template>
    <template v-else-if="type === 'jump-icon'">
      <circle cx="12" cy="12" r="10"/>
      <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"></path>
      <path d="M2 12h20"></path>
    </template>
    <template v-else-if="type === 'trash'">
      <polyline points="3,6 5,6 21,6"></polyline>
      <path d="m19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"></path>
    </template>
    <template v-else-if="type === 'call'">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
    </template>
    <template v-else-if="type === 'call-cancel'">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
      <line x1="18" y1="6" x2="6" y2="18" :stroke="strokeColor" :stroke-width="strokeWidth + 0.5"/>
    </template>
    <template v-else-if="type === 'file-pdf'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="14,2 14,8 20,8" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="16" y1="13" x2="8" y2="13" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="16" y1="17" x2="8" y2="17" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="10" y1="9" x2="8" y2="9" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>
    <template v-else-if="type === 'file-word'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="14,2 14,8 20,8" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="16" y1="13" x2="8" y2="13" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="16" y1="17" x2="8" y2="17" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="10,9 9,9 8,9 8,10 8,11 8,12 8,13" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>
    <template v-else-if="type === 'file-text'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="#38A169" stroke="#38A169" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <polyline points="14,2 14,8 20,8" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <text x="12" y="16" text-anchor="middle" fill="white" font-size="5" font-weight="bold">TXT</text>
    </template>
    <template v-else-if="type === 'file-image'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="14,2 14,8 20,8" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <rect x="8" y="10" width="8" height="6" rx="1" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <circle cx="10" cy="12" r="1" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="14,14 12,12 10,14" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>
    <template v-else-if="type === 'file-audio'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="14,2 14,8 20,8" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <circle cx="12" cy="13" r="2" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <path d="M12 11v6" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <path d="M16 13v2a4 4 0 0 1-8 0v-2" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>
    <template v-else-if="type === 'file-default'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <polyline points="14,2 14,8 20,8" :fill="fillColor" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="16" y1="13" x2="8" y2="13" :stroke="strokeColor" :stroke-width="strokeWidth"/>
      <line x1="16" y1="17" x2="8" y2="17" :stroke="strokeColor" :stroke-width="strokeWidth"/>
    </template>
    <template v-else-if="type === 'mic'">
      <rect x="9" y="4" width="6" height="10" rx="3" ry="3"></rect>
      <path d="M5 10a7 7 0 0 0 14 0"/>
      <line x1="12" y1="17" x2="12" y2="22"></line>
      <line x1="9" y1="22" x2="15" y2="22"></line>
    </template>
    <template v-else-if="type === 'mute-on-icon'">
      <circle cx="12" cy="12" r="10" stroke="currentColor" fill="none" stroke-width="2" />
      <path d="M9 9v2a3 3 0 0 0 5.24 2.12M15 11V9a3 3 0 0 0-5.68-1.33" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      <line x1="8" y1="8" x2="16" y2="16" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    </template>
    <template v-else-if="type === 'mute-off-icon'">
      <circle cx="12" cy="12" r="10" stroke="currentColor" fill="none" stroke-width="2" />
      <path d="M12 15a3 3 0 0 0 3-3V9a3 3 0 0 0-6 0v3a3 3 0 0 0 3 3Z" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      <path d="M8 11a4 4 0 0 0 8 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      <line x1="12" y1="15" x2="12" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    </template>
    <template v-else-if="type === 'speaker-on-icon'">
      <circle cx="12" cy="12" r="10" stroke="currentColor" fill="none" stroke-width="2" />
      <polygon points="10 9 6 11 6 13 10 15 10 9" stroke="currentColor" fill="none" stroke-width="2" stroke-linejoin="round" />
      <path d="M14 10a3 3 0 0 1 0 4M16 8a6 6 0 0 1 0 8" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none" />
    </template>
    <template v-else-if="type === 'speaker-off-icon'">
      <circle cx="12" cy="12" r="10" stroke="currentColor" fill="none" stroke-width="2" />
      <polygon points="10 9 6 11 6 13 10 15 10 9" stroke="currentColor" fill="none" stroke-width="2" stroke-linejoin="round" />
      <line x1="8" y1="8" x2="16" y2="16" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    </template>
    <template v-else-if="type === 'user-talk-1-icon'">
      <circle cx="12" cy="10" r="5" :stroke="strokeColor" :stroke-width="strokeWidth" fill="none" />
      <circle cx="10" cy="9" r="1" :fill="strokeColor" />
      <circle cx="14" cy="9" r="1" :fill="strokeColor" />
      <path d="M10 12 Q12 14 14 12" :stroke="strokeColor" :stroke-width="strokeWidth" fill="none" />
      <path d="M7 22v-3a5 5 0 0 1 5-5h0a5 5 0 0 1 5 5v3" :stroke="strokeColor" :stroke-width="strokeWidth" fill="none" />
      <ellipse cx="18" cy="8" rx="4" ry="3" :stroke="strokeColor" :stroke-width="strokeWidth" fill="white" />
      <path d="M16 10 L15 12" :stroke="strokeColor" :stroke-width="strokeWidth" />
      <circle cx="17" cy="7.5" r="0.5" :fill="strokeColor" />
      <circle cx="18.5" cy="7.5" r="0.5" :fill="strokeColor" />
      <circle cx="19" cy="8.5" r="0.5" :fill="strokeColor" />
    </template>
    <template v-else-if="type === 'rollback-icon'">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
      <polyline points="16,17 21,12 16,7"/>
      <line x1="21" y1="12" x2="9" y2="12"/>
    </template>
    <template v-else-if="type === 'check-circle'">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="8,12 11,15 16,9"></polyline>
    </template>
    <template v-else-if="type === 'x-circle'">
      <circle cx="12" cy="12" r="10"/>
      <line x1="9" y1="9" x2="15" y2="15"></line>
      <line x1="15" y1="9" x2="9" y2="15"></line>
    </template>
    <template v-else-if="type === 'spinner'">
      <path d="M12 2a10 10 0 0 1 10 10"></path>
    </template>
    <template v-else-if="type === 'settings'">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33 1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82 1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </template>
    <template v-else-if="type === 'user-circle-icon'">
      <circle cx="12" cy="12" r="10"/>
      <circle cx="12" cy="10" r="3"/>
      <path d="M7 20.662V20a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v.662"/>
    </template>
    <template v-else>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
      <circle cx="12" cy="12" r="2"/>
      <path d="M9 12h6"/>
      <path d="M12 9v6"/>
    </template>
  </svg>
</template>

<script>
export default {
  name: 'Icon',
  props: {
    type: { type: String, required: true },
    size: { type: [String, Number], default: 20 },
    fillColor: { type: String, default: 'transparent' },
    strokeColor: { type: String, default: 'currentColor' },
    strokeWidth: { type: [String, Number], default: 2 }
  }
}
</script>

<style scoped>
svg { display: inline-block; vertical-align: middle; }
</style>
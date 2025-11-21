<template>
  <div class="task-sidebar" v-if="visible">
    <div class="task-header">
      <span class="task-header-title">任务</span>
      <span class="task-count">{{ taskCount }}</span>
    </div>
    <div class="task-list">
      <div v-for="(task, i) in displayTasks" :key="i" class="task-card" :ref="el => setCardRef(i, el)">
        <div class="task-card-row">
          <span class="status-icon" :class="statusClass(task.status)">
            <Icon v-if="statusIcon(task.status) === 'done'" type="check-circle" :size="18" />
            <Icon v-else-if="statusIcon(task.status) === 'loading'" type="spinner" :size="18" class="spin" />
            <Icon v-else type="x-circle" :size="18" />
          </span>
          <div class="title">{{ task.title }}</div>
          <button class="task-more-btn" title="删除" @click.stop="del(i)">
            <Icon type="trash" :size="18" />
          </button>
        </div>
        <div class="task-subtitle" :class="statusClass(task.status)">{{ statusText(task.status) }}</div>
      </div>
    </div>
  </div>
</template>

<script>
import Icon from '../common/Icon.vue'
export default {
  name: 'TaskSidebar',
  components: { Icon },
  props: { visible: { type: Boolean, default: false }, conversationId: { type: String, default: '' }, apiBaseUrl: { type: String, default: '' }, userId: { type: String, default: 'test_user' }, seedTitle: { type: String, default: '' } },
  emits: [],
  data() { return { items: [], cardEls: [], cardWidths: [] } },
  computed: { displayTasks() { return Array.isArray(this.items) ? this.items : [] }, taskCount() { return this.displayTasks.length } },
  watch: { visible(v) { if (v && this.conversationId) { this.loadTasks(this.conversationId) } }, conversationId(id) { if (this.visible && id) { this.loadTasks(id) } } },
  methods: {
    setCardRef(i, el) { this.cardEls[i] = el; this.cardWidths[i] = el ? el.offsetWidth : 0 },
    del(i) { const t = this.displayTasks[i]; if (!t) return; const url = t.type === 'history' ? `${this.apiBaseUrl}/tasks/history/${encodeURIComponent(t.id)}` : `${this.apiBaseUrl}/tasks/${encodeURIComponent(t.id)}`; fetch(url, { method: 'DELETE' }).then(r => { if (r.ok) this.loadTasks(this.conversationId) }) },
    statusIcon(s) { const v = (s || '').toLowerCase(); if (v === 'done' || v === 'success' || v === 'completed') return 'done'; if (v === 'fail' || v === 'error') return 'fail'; return 'loading' },
    statusText(s) { const v = (s || '').toLowerCase(); if (v === 'done' || v === 'success' || v === 'completed') return '任务完成'; if (v === 'fail' || v === 'error') return '任务失败'; return '任务加载' },
    statusClass(s) { const k = this.statusIcon(s); return { 'is-success': k === 'done', 'is-loading': k === 'loading', 'is-fail': k === 'fail' } },
    async loadTasks(conversationId) { try { const resp = await fetch(`${this.apiBaseUrl}/tasks/?conversation_id=${encodeURIComponent(conversationId)}`); const roots = (resp.ok ? await resp.json() : []) || []; const resp2 = await fetch(`${this.apiBaseUrl}/tasks/${encodeURIComponent(conversationId)}/history/`); const hist = (resp2.ok ? await resp2.json() : []) || []; const rootCards = Array.isArray(roots) ? roots.map(x => ({ id: x.id, title: x.title, status: x.status, type: 'root' })) : []; const histCards = Array.isArray(hist) ? hist.map(h => ({ id: h.id, title: h.task_name || '任务', status: h.status || 'loading', type: 'history' })) : []; this.items = histCards.length > 0 ? histCards : rootCards; if ((!this.items || this.items.length === 0) && this.seedTitle && this.conversationId) { await this.ensureTask(this.conversationId, this.seedTitle); await this.splitTasks(this.conversationId, this.seedTitle); const r2 = await fetch(`${this.apiBaseUrl}/tasks/${encodeURIComponent(conversationId)}/history/`); const hist2 = (r2.ok ? await r2.json() : []) || []; this.items = Array.isArray(hist2) && hist2.length > 0 ? hist2.map(h => ({ id: h.id, title: h.task_name || '任务', status: h.status || 'loading', type: 'history' })) : this.items } } catch (e) {} },
    async appendHistory(conversationId, payload) { const resp = await fetch(`${this.apiBaseUrl}/tasks/${conversationId}/history/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); if (!resp.ok) return null; const data = await resp.json(); await this.loadTasks(conversationId); return data },
    async updateHistory(historyId, payload) { const resp = await fetch(`${this.apiBaseUrl}/tasks/history/${historyId}/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); return resp.ok },
    async ensureTask(conversationId, title) { const body = { conversation_id: conversationId, user_id: this.userId, title, status: 'loading' }; const resp = await fetch(`${this.apiBaseUrl}/tasks/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); if (resp.ok) { await this.loadTasks(conversationId) } },
    async splitTasks(conversationId, title) { const body = { conversation_id: conversationId, user_id: this.userId, title, status: 'loading' }; const resp = await fetch(`${this.apiBaseUrl}/tasks/${encodeURIComponent(conversationId)}/split/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); if (resp.ok) { await this.loadTasks(conversationId) } },
    async updateStatus(i, status) { const t = this.displayTasks[i]; if (!t) return; if (t.type === 'history') { const body2 = { status }; const resp = await fetch(`${this.apiBaseUrl}/tasks/history/${t.id}/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body2) }); if (resp.ok) { await this.loadTasks(this.conversationId) } } else { const body = { status }; const resp = await fetch(`${this.apiBaseUrl}/tasks/${t.id}/status/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); if (resp.ok) { await this.loadTasks(this.conversationId) } } }
  }
}
</script>

<style scoped>
.task-header { height: 40px; display: flex; align-items: center; gap: 8px; padding: 0 12px; }
.task-header-title { font-weight: 500; color: #333; }
.task-count { min-width: 20px; height: 20px; padding: 0 6px; border-radius: 10px; font-size: 12px; color: #4A90E2; background: rgba(74, 144, 226, 0.12); }
.task-card { border: 1px solid rgba(229, 229, 229, 0.3); border-radius: 12px; padding: 10px; margin: 10px 12px; background: rgba(255, 255, 255, 0.95); box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06); width: 220px; max-width: 100%; }
.task-card-row { display: grid; grid-template-columns: 18px 1fr auto; align-items: center; gap: 10px; }
.status-icon svg { display: block; }
.status-icon svg path { fill: currentColor; }
.status-icon.is-success { color: #22c55e; }
.status-icon.is-loading { color: #4A90E2; }
.status-icon.is-fail { color: #ef4444; }
.spin { animation: spin 1.2s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.title { font-weight: 500; color: #333; font-size: 13px; }
.task-subtitle { margin-top: 6px; font-size: 13px; color: #999; }
.task-subtitle.is-success { color: #22c55e; }
.task-subtitle.is-loading { color: #4A90E2; }
.task-subtitle.is-fail { color: #ef4444; }
.task-more-btn { width: 28px; height: 28px; border: none; border-radius: 6px; background: transparent; color: #666; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.task-more-btn:hover { background: rgba(74, 144, 226, 0.1); color: #4A90E2; }
</style>

<style>
.t-dropdown__popup,
.t-dropdown__menu { min-width: 0; width: auto; }
.t-dropdown__item { white-space: nowrap; padding: 8px 12px; font-size: 14px; }
.t-dropdown__item .menu-btn { width: 100%; height: auto; padding: 0; border: none; background: transparent; color: inherit; display: flex; align-items: center; gap: 8px; justify-content: flex-start; }
.menu-icon { color: currentColor; }
.menu-text { color: currentColor; }
.menu-icon.danger, .menu-text.danger { color: #ff4757; }
body.dark .menu-icon.danger, body.dark .menu-text.danger { color: #ff6b7a; }
.task-popconfirm .t-popup__content { background: #ffffff; color: #333333; }
body.dark .task-popconfirm .t-popup__content { background: #1f2937; color: #ffffff; }
body.dark .task-dropdown-popup, body.dark .user-dropdown-popup { background: #1f2937; color: #ffffff; border: 1px solid rgba(74, 85, 104, 0.3); }
body.dark .task-dropdown-popup .t-dropdown__menu, body.dark .user-dropdown-popup .t-dropdown__menu { background: #1f2937; color: #ffffff; }
body.dark .task-dropdown-popup .t-dropdown__item, body.dark .user-dropdown-popup .t-dropdown__item { color: #ffffff; }
body.dark .task-dropdown-popup .t-dropdown__item:hover, body.dark .user-dropdown-popup .t-dropdown__item:hover { background: rgba(147, 197, 253, 0.12); color: #93c5fd; }
</style>

<style>
body.dark .task-header-title { color: #ffffff; }
body.dark .task-card { background: rgba(26, 32, 44, 0.9); border-color: rgba(74, 85, 104, 0.3); }
body.dark .title { color: #ffffff; }
body.dark .task-subtitle { color: #cccccc; }
body.dark .task-count { color: #93c5fd; background: rgba(147, 197, 253, 0.18); }
</style>
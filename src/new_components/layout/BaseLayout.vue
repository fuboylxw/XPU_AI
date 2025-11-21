<template>
  <div class="base-layout" :class="{ dark: isDark, collapsed: collapsed }">
    <TopNav
      :mode="mode"
      :is-dark="isDark"
      :user-menu-options="userMenuOptions"
      :username="username"
      @toggle-theme="toggleTheme"
      @set-mode="$emit('set-mode', $event)"
      @app-download="$emit('app-download')"
      @go-home="$emit('go-home')"
      @school="$emit('school')"
      @user-menu-click="$emit('user-menu-click', $event)"
    />
    <div class="layout-body">
      <div class="side-bar">
        <slot name="sidebar"></slot>
      </div>
      <div class="layout-main">
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<script>
import TopNav from './TopNav.vue'

export default {
  name: 'BaseLayout',
  components: { TopNav },
  props: {
    mode: { type: String, default: 'chat' },
    isDark: { type: Boolean, default: false },
    userMenuOptions: { type: Array, default: () => [] },
    username: { type: String, default: '' },
    collapsed: { type: Boolean, default: false }
  },
  methods: {
    toggleTheme() {
      this.$emit('toggle-theme')
    }
  }
}
</script>

<style scoped>
.base-layout { display: flex; flex-direction: column; height: 100vh; }
.layout-main { position: relative; }
.base-layout { --bg-app: #f5f7fb; --surface-1: rgba(255,255,255,0.95); --surface-2: rgba(255,255,255,0.85); --border-1: rgba(229,229,229,0.25); --text-1: #2b2f36; --text-2: #616a7a; --accent-1: #4A90E2; --accent-2: #5BA7F7; }
.collapsed .layout-body { grid-template-columns: 56px 1fr; }
.base-layout.dark { --bg-app: #0f172a; --surface-1: rgba(18,23,35,0.96); --surface-2: rgba(18,23,35,0.9); --border-1: rgba(255,255,255,0.08); --text-1: #e5e7eb; --text-2: #a7b0c0; --accent-1: #3B82F6; --accent-2: #60A5FA; }
.layout-body { display: grid; grid-template-columns: 250px 1fr; height: calc(100vh - 60px); background: var(--bg-app); }
.layout-main { position: relative; overflow: hidden; background: var(--surface-2); }
/* merged from SideBar.vue */
.side-bar { border-right: 1px solid var(--border-1); background: var(--surface-1); backdrop-filter: blur(20px); display: flex; flex-direction: column; overflow-y: auto; }
.side-bar::-webkit-scrollbar { width: 6px; }
.side-bar::-webkit-scrollbar-track { background: transparent; }
.side-bar::-webkit-scrollbar-thumb { background: rgba(74,144,226,0.3); border-radius: 3px; }
.side-bar::-webkit-scrollbar-thumb:hover { background: rgba(74,144,226,0.5); }
</style>
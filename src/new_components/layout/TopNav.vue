<template>
  <div class="top-nav" :class="{ dark: isDark }">
    <div class="left">
      <img v-if="!isDark" src="/src/pic/tuan7.svg" alt="学校logo" class="brand-logo" />
      <img v-else src="/src/pic/tuan8.svg" alt="学校logo" class="brand-logo" />
    </div>
    <div class="center">
      <div class="mode-toggle">
        <div class="mode-toggle-inner">
          <div class="slider" :class="currentMode"></div>
          <button
            class="mode-pill pill-left"
            :class="{ active: currentMode === 'chat' }"
            @click="setMode('chat')"
            title="聊天"
          >
            <span v-if="currentMode === 'chat'" class="pill-text">聊天</span>
            <span v-else class="pill-icon">
              <svg width="18" height="18" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                <path d="M514 114.3c-219.9 0-398.9 178.9-398.9 398.8 0.1 220 179 398.9 398.9 398.9 219.9 0 398.8-178.9 398.8-398.8S733.9 114.3 514 114.3z m218.3 489v1.7c0 0.5-0.1 1-0.1 1.6 0 0.3 0 0.6-0.1 0.9 0 0.5-0.1 1-0.2 1.5 0 0.3-0.1 0.7-0.1 1-0.1 0.4-0.1 0.8-0.2 1.2-0.1 0.4-0.2 0.9-0.2 1.3-0.1 0.3-0.1 0.6-0.2 0.8-0.1 0.6-0.3 1.2-0.4 1.8 0 0.1-0.1 0.2-0.1 0.3-2.2 8.5-6.6 16.6-13.3 23.3L600.7 755.4c-20 20-52.7 20-72.6 0-20-20-20-52.7 0-72.6l28.9-28.9H347c-28.3 0-51.4-23.1-51.4-51.4 0-28.3 23.1-51.4 51.4-51.4h334c13.2 0 26.4 5 36.4 15s15 23.2 15 36.4c0 0.3-0.1 0.6-0.1 0.8z m0.1-179.5c0 28.3-23.1 51.4-51.4 51.4H347c-13.2 0-26.4-5-36.4-15s-15-23.2-15-36.4v-0.8-1.6c0-0.5 0.1-1.1 0.1-1.6 0-0.3 0-0.6 0.1-0.9 0-0.5 0.1-1 0.2-1.5 0-0.3 0.1-0.7 0.1-1 0.1-0.4 0.1-0.8 0.2-1.2 0.1-0.4 0.2-0.9 0.2-1.3 0.1-0.3 0.1-0.6 0.2-0.8 0.1-0.6 0.3-1.2 0.4-1.8 0-0.1 0.1-0.2 0.1-0.3 2.2-8.5 6.6-16.6 13.3-23.3l116.6-116.6c20-20 52.7-20 72.6 0 20 20 20 52.7 0 72.6L471 372.5h210c28.2 0 51.4 23.1 51.4 51.3z" fill="currentColor"></path>
              </svg>
            </span>
          </button>
          <button
            class="mode-pill pill-right"
            :class="{ active: currentMode === 'work' }"
            @click="setMode('work')"
            title="工作"
          >
            <span v-if="currentMode === 'work'" class="pill-text">工作</span>
            <span v-else class="pill-icon">
              <svg width="18" height="18" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                <path d="M514 114.3c-219.9 0-398.9 178.9-398.9 398.8 0.1 220 179 398.9 398.9 398.9 219.9 0 398.8-178.9 398.8-398.8S733.9 114.3 514 114.3z m218.3 489v1.7c0 0.5-0.1 1-0.1 1.6 0 0.3 0 0.6-0.1 0.9 0 0.5-0.1 1-0.2 1.5 0 0.3-0.1 0.7-0.1 1-0.1 0.4-0.1 0.8-0.2 1.2-0.1 0.4-0.2 0.9-0.2 1.3-0.1 0.3-0.1 0.6-0.2 0.8-0.1 0.6-0.3 1.2-0.4 1.8 0 0.1-0.1 0.2-0.1 0.3-2.2 8.5-6.6 16.6-13.3 23.3L600.7 755.4c-20 20-52.7 20-72.6 0-20-20-20-52.7 0-72.6l28.9-28.9H347c-28.3 0-51.4-23.1-51.4-51.4 0-28.3 23.1-51.4 51.4-51.4h334c13.2 0 26.4 5 36.4 15s15 23.2 15 36.4c0 0.3-0.1 0.6-0.1 0.8z m0.1-179.5c0 28.3-23.1 51.4-51.4 51.4H347c-13.2 0-26.4-5-36.4-15s-15-23.2-15-36.4v-0.8-1.6c0-0.5 0.1-1.1 0.1-1.6 0-0.3 0-0.6 0.1-0.9 0-0.5 0.1-1 0.2-1.5 0-0.3 0.1-0.7 0.1-1 0.1-0.4 0.1-0.8 0.2-1.2 0.1-0.4 0.2-0.9 0.2-1.3 0.1-0.3 0.1-0.6 0.2-0.8 0.1-0.6 0.3-1.2 0.4-1.8 0-0.1 0.1-0.2 0.1-0.3 2.2-8.5 6.6-16.6 13.3-23.3l116.6-116.6c20-20 52.7-20 72.6 0 20 20 20 52.7 0 72.6L471 372.5h210c28.2 0 51.4 23.1 51.4 51.3z" fill="currentColor"></path>
              </svg>
            </span>
          </button>
        </div>
      </div>
    </div>
    <div class="right">
      <span class="theme-label">{{ isDark ? '深色' : '浅色' }}</span>
      <t-switch size="medium" @change="toggleTheme" :value="isDark"></t-switch>
      <button class="nav-btn" @click="goToSchoolHomepage" title="学校首页">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="transparent" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
          <polyline points="9 22 9 12 15 12 15 22"></polyline>
        </svg>
      </button>
      <button class="nav-btn" @click="showAppDownload" title="西工程大APP下载">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="transparent" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
      </button>
      <t-dropdown :options="userMenuOptions" @click="handleUserMenuClick" placement="bottom-right" :popup-props="{ overlayClassName: 'user-dropdown-popup' }">
        <div class="user-menu-trigger">
          <svg class="user-avatar" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg" width="32" height="32">
            <path d="M512 0C229.25 0 0 229.25 0 512c0 174.154167 86.9875 327.979167 219.8625 420.475a287.5875 287.5875 0 0 1 22.366667-55.579167c-26.779167-7.1-44.258333-33.5375-39.616667-61.416666 3.6375-21.858333 19.858333-38.45 40.008333-43.670834-17.370833-11.470833-27.35-32.416667-23.7125-54.270833 3.6375-21.8625 19.858333-38.454167 40.008334-43.675-17.370833-11.466667-27.35-32.416667-23.7125-54.270833a54.3375 54.3375 0 0 1 35.820833-42.441667v-4.291667c-14.75-11.908333-22.858333-31.179167-19.529167-51.216666a54.075 54.075 0 0 1 19.545834-33.354167c-0.016667-1.229167-0.091667-2.445833-0.091667-3.683333 0-21.35 2.808333-42.0375 8.016667-61.75 6.716667-26.75 18.0875-50.925 32.654166-72.25a241.925 241.925 0 0 1 107.8125-88.6125c31.65-13.841667 64.270833-20.316667 93.2875-18.475 97.741667-6.195833 236.308333 81.4375 240.845834 227.7125a54.104167 54.104167 0 0 1 19.475 33.295833c3.35 20.116667-4.8375 39.470833-19.704167 51.366667v4.079166a54.341667 54.341667 0 0 1 36 42.5c3.633333 21.854167-6.341667 42.804167-23.7125 54.270834 20.145833 5.229167 36.370833 21.8125 40.008333 43.675 3.633333 21.858333-6.345833 42.804167-23.716666 54.270833 20.15 5.225 36.375 21.816667 40.0125 43.675 4.925 29.604167-15.0875 57.6-44.695834 62.529167-1.366667 0.229167-2.725 0.345833-4.079166 0.466666 13.341667 21.645833 23.808333 45.445833 31.1625 71 132.783333-92.508333 219.704167-246.279167 219.704166-420.366666C1024 229.25 794.754167 0 512 0z" fill="#A0D9F6"></path>
            <path d="M299.995833 802.45v-0.120833c0.9375-0.85 1.904167-1.666667 2.854167-2.508334l1.5625-1.375a271.333333 271.333333 0 0 1 9.045833-7.558333l0.858334-0.695833a281.958333 281.958333 0 0 1 21.533333-15.479167c0.454167-0.295833 0.920833-0.583333 1.379167-0.875a282.141667 282.141667 0 0 1 9.7-5.958333c0.725-0.429167 1.45-0.85 2.175-1.270834a291.379167 291.379167 0 0 1 9.966666-5.483333c0.529167-0.275 1.05-0.566667 1.583334-0.841667a298.191667 298.191667 0 0 1 24.35-11.2375c0.775-0.316667 1.5625-0.6125 2.3375-0.929166a313.445833 313.445833 0 0 1 23.458333-8.291667c0.925-0.283333 1.841667-0.591667 2.775-0.866667a327.129167 327.129167 0 0 1 26.529167-6.75c1.2-0.258333 2.416667-0.479167 3.620833-0.720833a342.208333 342.208333 0 0 1 24.320833-3.945833c1.379167-0.175 2.75-0.366667 4.133334-0.525a357.916667 357.916667 0 0 1 14.079166-1.358334h25.75c-131.9 0-238.9875-105.945833-240.966666-237.375a54.075 54.075 0 0 0-19.545834 33.354167c-3.333333 20.0375 4.775 39.308333 19.529167 51.216667v4.291666a54.3375 54.3375 0 0 0-35.820833 42.441667c-3.6375 21.854167 6.341667 42.804167 23.7125 54.270833-20.15 5.225-36.370833 21.8125-40.008334 43.675-3.6375 21.854167 6.341667 42.8 23.7125 54.270834-20.15 5.225-36.370833 21.8125-40.008333 43.670833-4.6375 27.879167 12.841667 54.316667 39.616667 61.416667a274.566667 274.566667 0 0 1 57.766666-74.441667zM512.233333 725.65l-0.233333 0.004167 0.233333-0.004167z" fill="#FECF77"></path>
            <path d="M419.420833 261.9875a241.891667 241.891667 0 0 0-107.8125 88.6125c27.6875-40.529167 66.920833-70.725 107.8125-88.6125zM512 725.654167l0.233333-0.004167c130.5-0.125 236.65-103.958333 240.633334-233.525-63.704167 39.183333-229.075-17.679167-279.525-104.479167-46.504167 80.920833-124.8125 152.066667-200.8625 104.158334-1.3125-24.533333 1.108333-47.558333 6.483333-68.954167a241.395833 241.395833 0 0 0-8.016667 61.75c0 1.233333 0.075 2.45 0.091667 3.683333 1.975 131.425 109.0625 237.370833 240.9625 237.370834z" fill="#FCE9EA"></path>
            <path d="M473.3375 387.645833c50.454167 86.8 215.820833 143.6625 279.525 104.479167-3.983333 129.566667-110.133333 233.4-240.633333 233.525v0.004167h25.754166c4.725 0.354167 9.4 0.820833 14.041667 1.354166 1.429167 0.1625 2.8375 0.358333 4.254167 0.541667a348.658333 348.658333 0 0 1 14.35 2.108333 343.416667 343.416667 0 0 1 9.695833 1.795834c1.295833 0.258333 2.595833 0.495833 3.883333 0.770833 8.958333 1.891667 17.733333 4.125 26.304167 6.691667 1.079167 0.320833 2.141667 0.670833 3.2125 1.004166a314.758333 314.758333 0 0 1 13.225 4.433334c3.2375 1.166667 6.445833 2.383333 9.620833 3.65 0.920833 0.366667 1.841667 0.716667 2.754167 1.091666a300.016667 300.016667 0 0 1 24.054167 11.104167c0.716667 0.370833 1.416667 0.758333 2.129166 1.133333a289.391667 289.391667 0 0 1 21.1 12.279167c0.620833 0.404167 1.2625 0.7875 1.883334 1.195833a283.425 283.425 0 0 1 21.1625 15.216667c0.529167 0.416667 1.041667 0.85 1.566666 1.270833a284.583333 284.583333 0 0 1 10.416667 8.8c0.704167 0.620833 1.420833 1.233333 2.116667 1.858334v0.091666a274.25 274.25 0 0 1 49.370833 59.3125c1.354167-0.120833 2.7125-0.241667 4.079167-0.466666 29.604167-4.929167 49.616667-32.920833 44.695833-62.529167-3.633333-21.858333-19.8625-38.454167-40.0125-43.675 17.370833-11.466667 27.35-32.4125 23.716667-54.270833-3.6375-21.8625-19.8625-38.45-40.008334-43.675 17.370833-11.466667 27.345833-32.416667 23.7125-54.270834-3.391667-20.391667-17.729167-36.225-36-42.5v-4.079166c14.8625-11.895833 23.05-31.25 19.704167-51.366667a54.075 54.075 0 0 0-19.475-33.295833c-4.5375-146.270833-143.108333-233.908333-240.845833-227.7125 0.233333 0.016667 0.475 0.008333 0.708333 0.025 8.425 29.75-8.491667 89.179167-40.0625 144.104166z" fill="#FCBA6F"></path>
            <path d="M723.766667 802.05v85.966667c-33.0875-50.583333-167.2625-59.858333-211.65-6.691667-44.6125-53.425-179.875-43.791667-212.120834 7.45v-86.325a274.533333 274.533333 0 0 0-57.770833 74.445833 287.5875 287.5875 0 0 0-22.366667 55.579167c82.854167 57.679167 183.541667 91.525 292.1375 91.525 108.666667 0 209.4125-33.891667 292.295834-91.633333-7.354167-25.554167-17.816667-49.354167-31.1625-71a273.783333 273.783333 0 0 0-49.3625-59.316667z" fill="#F4B3B3"></path>
            <path d="M721.654167 800.095833a272.729167 272.729167 0 0 0-10.416667-8.8c-0.525-0.420833-1.0375-0.854167-1.566667-1.270833a282.233333 282.233333 0 0 0-21.1625-15.216667c-0.620833-0.408333-1.2625-0.791667-1.883333-1.195833a301.958333 301.958333 0 0 0-11.741667-7.129167 281.570833 281.570833 0 0 0-9.358333-5.15c-0.7125-0.379167-1.4125-0.766667-2.129167-1.133333a300.016667 300.016667 0 0 0-24.054166-11.104167c-0.9125-0.375-1.833333-0.725-2.754167-1.091666a301.308333 301.308333 0 0 0-13.195833-4.916667 318.545833 318.545833 0 0 0-9.65-3.166667c-1.075-0.333333-2.1375-0.683333-3.2125-1.004166a328.125 328.125 0 0 0-26.304167-6.691667c-1.2875-0.270833-2.5875-0.5125-3.883333-0.770833a362.041667 362.041667 0 0 0-9.695834-1.795834 331.775 331.775 0 0 0-14.35-2.108333c-1.420833-0.183333-2.829167-0.379167-4.254166-0.541667a356.016667 356.016667 0 0 0-14.041667-1.354166h-51.7375a357.916667 357.916667 0 0 0-14.079167 1.358333c-1.3875 0.158333-2.754167 0.35-4.133333 0.525a343.516667 343.516667 0 0 0-24.320833 3.945833c-1.208333 0.241667-2.420833 0.4625-3.620834 0.720834a327.570833 327.570833 0 0 0-26.529166 6.75c-0.933333 0.275-1.85 0.583333-2.775 0.866666-3.416667 1.058333-6.8 2.166667-10.15 3.329167l-3.2125 1.133333c-3.4 1.220833-6.766667 2.504167-10.095834 3.829167-0.779167 0.3125-1.5625 0.608333-2.3375 0.929167a300.25 300.25 0 0 0-24.35 11.2375c-0.529167 0.275-1.054167 0.566667-1.583333 0.841666a298.745833 298.745833 0 0 0-12.141667 6.754167c-3.279167 1.925-6.5125 3.908333-9.7 5.958333-0.458333 0.291667-0.920833 0.579167-1.379166 0.875a280.816667 280.816667 0 0 0-21.533334 15.479167l-0.858333 0.695833a276.508333 276.508333 0 0 0-9.045833 7.558334l-1.5625 1.375c-0.95 0.8375-1.916667 1.654167-2.854167 2.508333v86.445833c32.245833-51.241667 167.5125-60.875 212.120833-7.45 44.3875-53.166667 178.558333-43.8875 211.65 6.691667v-86.058333c-0.7-0.625-1.4125-1.233333-2.116666-1.858334z" fill="#FEFEFE"></path>
            <path d="M272.475 491.804167c76.05 47.9125 154.358333-23.2375 200.8625-104.158334 31.566667-54.929167 48.483333-114.354167 40.079167-144.108333-0.233333-0.016667-0.475-0.008333-0.708334-0.025-29.016667-1.841667-61.6375 4.633333-93.2875 18.475-40.891667 17.8875-80.125 48.083333-107.8125 88.6125-14.566667 21.325-25.9375 45.5-32.654166 72.25-5.366667 21.395833-7.791667 44.420833-6.479167 68.954167z" fill="#FECF77"></path>
          </svg>
          <span v-if="username" class="username">{{ username }}</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="dropdown-icon">
            <polyline points="6,9 12,15 18,9"></polyline>
          </svg>
        </div>
      </t-dropdown>
    </div>
    
    <!-- APP下载模态框 -->
    <teleport to="body">
      <div v-if="showAppModal" class="modal-overlay" @click="closeAppModal">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h3>西工程大APP下载</h3>
            <button class="close-btn" @click="closeAppModal">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><g id="asxclose"><path id="stroke1" d="M16.9503 7.05029L12.0005 12M12.0005 12L7.05078 16.9498M12.0005 12L16.9503 16.9498M12.0005 12L7.05078 7.05029" stroke-linecap="square" stroke-width="2" stroke="currentColor"/></g></svg>
            </button>
          </div>
          <div class="modal-body">
            <div class="app-clients">
              <div class="client-item">
                <img src="/src/pic/ios.png" alt="iOS客户端二维码" class="app-qr-image" />
                <p>iOS客户端</p>
              </div>
              <div class="client-item">
                <img src="/src/pic/android.png" alt="安卓客户端二维码" class="app-qr-image" />
                <p>安卓客户端</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script>
import { h } from 'vue'
export default {
  name: 'TopNav',
  props: { 
    mode: { type: String, default: 'chat' }, 
    isDark: { type: Boolean, default: false }, 
    userMenuOptions: { type: Array, default: () => [] }, 
    username: { type: String, default: '' } 
  },
  data() {
    return {
      showAppModal: false
    }
  },
  computed: {
    currentMode() { return this.mode }
  },
  methods: {
    setMode(m) { try { this.$emit('set-mode', m); const target = m === 'chat' ? '/chat' : '/work'; if (this.$route && this.$router) { if (this.$route.path !== target) this.$router.push(target) } } catch (_) {} },
    toggleTheme() { this.$emit('toggle-theme') },
    goToSchoolHomepage() { window.open('https://www.xpu.edu.cn/', '_blank') },
    showAppDownload() { this.showAppModal = true },
    closeAppModal() { this.showAppModal = false },
    handleUserMenuClick(data) { this.$emit('user-menu-click', data) }
  }
}
</script>

<style scoped>
.top-nav { height: 60px; display: grid; grid-template-columns: auto 1fr auto; align-items: center; padding: 0 12px; background: var(--surface-1); backdrop-filter: blur(10px); position: sticky; top: 0; z-index: 1000; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05); color: var(--text-1); }
.top-nav.dark { box-shadow: 0 1px 0 rgba(255,255,255,0.06); }
.left { display: flex; gap: 8px; align-items: center; }
.brand-logo { height: 56px; width: auto; display: block; flex-shrink: 0; filter: drop-shadow(0 1px 0 rgba(0,0,0,0.1)); }
.center { display: flex; justify-content: center; align-items: center; }
.right { display: flex; align-items: center; justify-content: flex-end; gap: 8px; }
.nav-btn { width: 28px; height: 28px; border: none; border-radius: 8px; background: transparent; display: flex; align-items: center; justify-content: center; color: var(--text-1); cursor: pointer; transition: all 0.3s ease; }
.nav-btn:hover { background: rgba(74,144,226,0.12); color: var(--accent-1); }
.mode-toggle { display: inline-flex; padding: 4px; border-radius: 16px; background: rgba(229,229,229,0.6); box-shadow: inset 0 0 0 1px rgba(0,0,0,0.04); }
.top-nav.dark .mode-toggle { background: rgba(255,255,255,0.08); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.06); }
.mode-toggle-inner { position: relative; display: grid; grid-template-columns: 1fr 1fr; width: 150px; height: 30px; }
.slider { position: absolute; top: 0; left: 0; width: 50%; height: 100%; border-radius: 12px; background: linear-gradient(135deg, var(--accent-1) 0%, var(--accent-2) 100%); box-shadow: 0 6px 18px rgba(74,144,226,0.30); transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1); }
.slider.chat { transform: translateX(0) }
.slider.work { transform: translateX(100%) }
.mode-pill { border: none; background: transparent; color: var(--text-1); z-index: 1; display: flex; align-items: center; justify-content: center; gap: 6px; font-weight: 600; cursor: pointer; }
.mode-pill .pill-text { color: #fff }
.pill-left { border-radius: 14px 0 0 14px }
.pill-right { border-radius: 0 14px 14px 0 }
.pill-icon { display: inline-flex; color: var(--text-2) }
.theme-label { font-size: 13px; color: var(--text-1); font-weight: 500; }
.user-menu-trigger { display: flex; align-items: center; gap: 6px; padding: 2px 6px; border-radius: 8px; cursor: pointer; transition: all 0.3s ease; }
.user-menu-trigger .username { font-size: 13px; color: var(--text-1); max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-menu-trigger:hover { background: rgba(74,144,226,0.12); }
.user-avatar { width: 28px; height: 28px; flex-shrink: 0; }
.dropdown-icon { color: #666; }

/* 模态框样式 */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; z-index: 2000; backdrop-filter: blur(2px); }
.modal-content { background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); width: 90%; max-width: 600px; overflow: hidden; animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
@keyframes slideUp { from { opacity: 0; transform: translateY(30px) } to { opacity: 1; transform: translateY(0) } }
.modal-header { display: flex; justify-content: center; align-items: center; padding: 32px 32px 24px; border-bottom: 1px solid #f0f0f0; position: relative; }
.modal-header h3 { margin: 0; font-size: 20px; font-weight: 700; color: #333; }
.close-btn { position: absolute; right: 32px; border: none; background: transparent; cursor: pointer; color: #999; transition: all 0.3s ease; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; padding: 0; }
.close-btn:hover { color: #333; transform: rotate(90deg); background: rgba(0, 0, 0, 0.05); border-radius: 8px; }
.modal-body { padding: 40px 32px; }
.app-clients { display: grid; grid-template-columns: repeat(2, 1fr); gap: 40px; }
.client-item { display: flex; flex-direction: column; align-items: center; gap: 16px; text-align: center; }
.app-qr-image { width: 200px; height: 200px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); transition: all 0.3s ease; }
.app-qr-image:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15); }
.client-item p { margin: 0; font-weight: 600; color: #333; font-size: 15px; }

/* 暗色模式下的模态框样式 */
.top-nav.dark .modal-overlay { background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px); }
.top-nav.dark .modal-content { background: rgba(18, 24, 38, 0.96); box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6); }
.top-nav.dark .modal-header { border-bottom-color: rgba(148, 163, 184, 0.2); }
.top-nav.dark .modal-header h3 { color: #e5e7eb; }
.top-nav.dark .close-btn { color: #9ca3af; }
.top-nav.dark .close-btn:hover { color: #e5e7eb; background: rgba(255,255,255,0.08); }
.top-nav.dark .modal-body { color: #cbd5e1; }
.top-nav.dark .client-item p { color: #e5e7eb; }
.top-nav.dark .app-qr-image { box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5); }
</style>
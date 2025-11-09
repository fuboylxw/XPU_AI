import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import TDesign from 'tdesign-vue-next'
import 'tdesign-vue-next/es/style/index.css'
import './store/auth.js' // 导入认证存储以确保初始化
import preloader from './utils/preloader.js' // 导入预加载器

// 创建Vue应用实例
const app = createApp(App)

// 配置TDesign
app.use(TDesign)

// 配置路由
app.use(router)

// 应用启动函数
async function startApp() {
  console.log('🌟 正在启动Vue应用...')
  
  // 初始化认证存储
  const { authStore } = await import('./store/auth.js')
  authStore.init()
  console.log('✅ 认证存储初始化完成')
  
  // 开始预加载
  const preloadStart = Date.now()
  console.log('📦 开始前端预加载...')
  
  try {
    const preloadResults = await preloader.startPreload()
    const preloadDuration = Date.now() - preloadStart
    console.log(`🎯 前端预加载完成 (耗时: ${preloadDuration}ms)`)
    
    // 处理预加载结果
    const tokenResult = preloader.getResult('tokenValidation')
    const healthResult = preloader.getResult('healthCheck')
    const configResult = preloader.getResult('systemConfig')
    
    // 如果token无效，清理本地存储
    if (tokenResult && !tokenResult.success) {
      console.warn('Token预验证失败，清理本地存储')
      authStore.logout()
    } else if (tokenResult && tokenResult.data && !tokenResult.data.valid) {
      console.warn('Token无效，清理本地存储')
      authStore.logout()
    }
    
    // 显示系统状态
    if (healthResult && healthResult.success) {
      const health = healthResult.data
      console.log(`🏥 系统状态: ${health.status}`)
      if (health.system_status) {
        console.log(`⚙️ 后端预加载状态: ${health.system_status}`)
      }
    }
    
    // 存储预加载结果到全局
    window.__PRELOAD_RESULTS__ = preloadResults
    
  } catch (error) {
    console.error('❌ 前端预加载失败:', error)
  }
  
  // 挂载应用
  app.mount('#app')
  console.log('🚀 Vue应用启动完成')
}

// 启动应用
startApp().catch(error => {
  console.error('应用启动失败:', error)
  // 即使预加载失败，也要启动应用
  app.mount('#app')
})
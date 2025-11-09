import { reactive } from 'vue'

// 用户认证状态管理
export const authStore = reactive({
  // 状态
  user: null,
  token: null,
  isAuthenticated: false,
  
  // 初始化状态
  init() {
    const token = localStorage.getItem('access_token')
    const userInfo = localStorage.getItem('user_info')
    
    if (token && userInfo) {
      try {
        this.token = token
        this.user = JSON.parse(userInfo)
        this.isAuthenticated = true
      } catch (error) {
        console.error('解析用户信息失败:', error)
        this.logout()
      }
    }
  },
  
  // 登录
  login(token, user) {
    this.token = token
    this.user = user
    this.isAuthenticated = true
    
    // 持久化存储
    localStorage.setItem('access_token', token)
    localStorage.setItem('user_info', JSON.stringify(user))
  },
  
  // 登出
  logout() {
    this.token = null
    this.user = null
    this.isAuthenticated = false
    
    // 清除存储
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
  },
  
  // 更新用户信息
  updateUser(user) {
    this.user = { ...this.user, ...user }
    localStorage.setItem('user_info', JSON.stringify(this.user))
  },
  
  // 获取认证头
  getAuthHeader() {
    return this.token ? { 'Authorization': `Bearer ${this.token}` } : {}
  },
  
  // 检查是否已登录
  checkAuth() {
    return this.isAuthenticated && this.token && this.user
  }
})

// 初始化状态
authStore.init()
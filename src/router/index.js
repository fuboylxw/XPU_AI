import { createRouter, createWebHistory } from 'vue-router'
import ChatMode from '../new_components/chat/ChatMode.vue'
import Login from '../new_components/login/Login.vue'
import WorkMode from '../new_components/work/WorkMode.vue'

// 通过环境变量控制是否禁用鉴权（Vite 仅暴露以 VITE_ 开头的变量）
const DISABLE_AUTH = ['1', 'true', 'yes', 'on'].includes(String(import.meta.env.VITE_DISABLE_AUTH ?? '').toLowerCase())

const routes = [
  {
    path: '/',
    name: 'Chat',
    component: ChatMode,
    meta: { requiresAuth: true }
  },
  {
    path: '/chat',
    name: 'ChatMode',
    component: ChatMode,
    meta: { requiresAuth: true }
  },
  {
    path: '/work',
    name: 'WorkMode',
    component: WorkMode,
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  if (DISABLE_AUTH) {
    return next()
  }
  const token = localStorage.getItem('access_token')
  
  // 如果路由需要认证
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!token) {
      // 没有token，跳转到登录页
      next('/login')
    } else {
      // 验证token是否有效
      verifyToken(token).then(isValid => {
        if (isValid) {
          next()
        } else {
          // token无效，清除并跳转到登录页
          localStorage.removeItem('access_token')
          localStorage.removeItem('user_info')
          next('/login')
        }
      }).catch(() => {
        // 验证失败，跳转到登录页
        localStorage.removeItem('access_token')
        localStorage.removeItem('user_info')
        next('/login')
      })
    }
  } else if (to.path === '/login' && token) {
    // 已登录用户访问登录页，验证token后决定是否跳转
    verifyToken(token).then(isValid => {
      if (isValid) {
        next('/')
      } else {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user_info')
        next()
      }
    }).catch(() => {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_info')
      next()
    })
  } else {
    next()
  }
})

// 验证token的函数
async function verifyToken(token) {
  try {
    const response = await fetch('http://localhost:8000/api/auth/verify/', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      return data.valid === true
    }
    return false
  } catch (error) {
    console.error('Token验证失败:', error)
    return false
  }
}

export default router

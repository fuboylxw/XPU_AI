/**
 * 前端预加载管理器
 * 负责在应用启动时预加载必要的资源和数据
 */

class FrontendPreloader {
  constructor() {
    this.preloadTasks = new Map()
    this.preloadResults = new Map()
    this.isPreloading = false
    this.preloadComplete = false
    this.startTime = null
  }

  /**
   * 添加预加载任务
   * @param {string} name - 任务名称
   * @param {Function} task - 预加载任务函数
   * @param {number} priority - 优先级 (数字越小优先级越高)
   */
  addTask(name, task, priority = 5) {
    this.preloadTasks.set(name, { task, priority })
  }

  /**
   * 开始预加载
   */
  async startPreload() {
    if (this.isPreloading || this.preloadComplete) {
      return this.preloadResults
    }

    this.isPreloading = true
    this.startTime = Date.now()
    console.log('🚀 开始前端预加载...')

    // 按优先级排序任务
    const sortedTasks = Array.from(this.preloadTasks.entries())
      .sort(([, a], [, b]) => a.priority - b.priority)

    // 执行预加载任务
    for (const [name, { task }] of sortedTasks) {
      try {
        console.log(`📦 预加载: ${name}`)
        const result = await task()
        this.preloadResults.set(name, { success: true, data: result })
        console.log(`✅ ${name} 预加载完成`)
      } catch (error) {
        console.error(`❌ ${name} 预加载失败:`, error)
        this.preloadResults.set(name, { success: false, error })
      }
    }

    this.isPreloading = false
    this.preloadComplete = true
    const duration = Date.now() - this.startTime
    console.log(`🎯 前端预加载完成 (耗时: ${duration}ms)`)

    return this.preloadResults
  }

  /**
   * 获取预加载结果
   * @param {string} name - 任务名称
   */
  getResult(name) {
    return this.preloadResults.get(name)
  }

  /**
   * 检查是否预加载完成
   */
  isComplete() {
    return this.preloadComplete
  }

  /**
   * 等待预加载完成
   */
  async waitForCompletion() {
    if (this.preloadComplete) {
      return this.preloadResults
    }

    return new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (this.preloadComplete) {
          clearInterval(checkInterval)
          resolve(this.preloadResults)
        }
      }, 100)
    })
  }
}

// 创建全局预加载器实例
const preloader = new FrontendPreloader()

// 添加默认预加载任务

// 1. 预加载系统配置
preloader.addTask('systemConfig', async () => {
  try {
    const response = await fetch('http://localhost:8000/api/config/')
    if (response.ok) {
      const config = await response.json()
      return config
    }
    throw new Error('获取系统配置失败')
  } catch (error) {
    console.warn('系统配置预加载失败，将使用默认配置')
    return null
  }
}, 1)

// 2. 预验证用户token
preloader.addTask('tokenValidation', async () => {
  const token = localStorage.getItem('access_token')
  if (!token) {
    return { valid: false, reason: 'no_token' }
  }

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
      return { valid: data.valid === true, data }
    }
    return { valid: false, reason: 'invalid_response' }
  } catch (error) {
    console.warn('Token预验证失败:', error)
    return { valid: false, reason: 'network_error', error }
  }
}, 2)

// 3. 预加载用户会话列表
preloader.addTask('conversationsList', async () => {
  const token = localStorage.getItem('access_token')
  if (!token) {
    return null
  }

  try {
    const response = await fetch('http://localhost:8000/api/conversations/', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      const conversations = await response.json()
      return conversations
    }
    return null
  } catch (error) {
    console.warn('会话列表预加载失败:', error)
    return null
  }
}, 3)

// 4. 预加载系统健康状态
preloader.addTask('healthCheck', async () => {
  try {
    const response = await fetch('http://localhost:8000/health')
    if (response.ok) {
      const health = await response.json()
      return health
    }
    throw new Error('健康检查失败')
  } catch (error) {
    console.warn('系统健康检查失败:', error)
    return { status: 'unknown', error: error.message }
  }
}, 4)

// 5. 预热关键组件
preloader.addTask('componentWarmup', async () => {
  // 预创建一些可能用到的对象
  const warmupData = {
    timestamp: Date.now(),
    userAgent: navigator.userAgent,
    language: navigator.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
  }
  
  // 模拟一些可能的初始化操作
  await new Promise(resolve => setTimeout(resolve, 50))
  
  return warmupData
}, 5)

export default preloader
export { FrontendPreloader }
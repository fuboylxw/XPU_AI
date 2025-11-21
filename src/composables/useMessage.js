import { MessagePlugin } from 'tdesign-vue-next'

/**
 * 全局消息提示组合式函数
 * 提供统一的消息提示接口
 */
export function useMessage() {
  
  /**
   * 显示信息提示
   * @param {string} content - 消息内容
   * @param {number} duration - 显示时长（毫秒）
   */
  const info = (content, duration = 3000) => {
    MessagePlugin.info({
      content,
      duration,
      placement: 'top'
    })
  }

  /**
   * 显示成功提示
   * @param {string} content - 消息内容
   * @param {number} duration - 显示时长（毫秒）
   */
  const success = (content, duration = 3000) => {
    MessagePlugin.success({
      content,
      duration,
      placement: 'top'
    })
  }

  /**
   * 显示警告提示
   * @param {string} content - 消息内容
   * @param {number} duration - 显示时长（毫秒）
   */
  const warning = (content, duration = 3000) => {
    MessagePlugin.warning({
      content,
      duration,
      placement: 'top'
    })
  }

  /**
   * 显示错误提示
   * @param {string} content - 消息内容
   * @param {number} duration - 显示时长（毫秒）
   */
  const error = (content, duration = 5000) => {
    MessagePlugin.error({
      content,
      duration,
      placement: 'top'
    })
  }

  /**
   * 显示询问提示
   * @param {string} content - 消息内容
   * @param {number} duration - 显示时长（毫秒）
   */
  const question = (content, duration = 3000) => {
    MessagePlugin.info({
      content,
      duration,
      placement: 'top',
      theme: 'question'
    })
  }

  /**
   * 处理 API 错误响应
   * @param {Response} response - fetch 响应对象
   * @param {Object} data - 响应数据
   * @param {string} defaultMessage - 默认错误消息
   */
  const handleApiError = (response, data, defaultMessage = '操作失败') => {
    if (!response.ok) {
      const errorMessage = data?.detail || data?.message || defaultMessage
      error(errorMessage)
      return true
    }
    return false
  }

  /**
   * 处理网络错误
   * @param {Error} err - 错误对象
   * @param {string} defaultMessage - 默认错误消息
   */
  const handleNetworkError = (err, defaultMessage = '网络错误，请稍后重试') => {
    console.error('Network error:', err)
    error(defaultMessage)
  }

  return {
    info,
    success,
    warning,
    error,
    question,
    handleApiError,
    handleNetworkError
  }
}
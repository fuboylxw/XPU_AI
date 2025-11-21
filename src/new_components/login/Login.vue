<template>
  <div class="page-wrapper">
    <!-- 导航菜单 -->
    <div class="nav-header">
      <t-head-menu>
        <template #logo>
          <img height="55" src="/src/pic/tuan7.svg" alt="logo" />
        </template>
      </t-head-menu>
    </div>
    
    <!-- 登录页面内容 -->
    <div class="login-container">
    <!-- 左侧装饰图案 -->
    <div class="left-decoration">
      <img src="/src/pic/tuan5.svg" alt="装饰图案" class="decoration-svg" />
    </div>

    <!-- 登录卡片 -->
    <t-card 
      title="用户登录" 
      hover-shadow 
      :style="{ width: '400px', maxWidth: '90vw' }"
      class="login-card"
    >
      <div class="login-content">
        <t-tabs v-model="activeTab" @change="handleTabChange">
          <t-tab-panel :value="'account'" label="用户名或邮箱登录">
            <!-- 用户名或邮箱登录 -->
            <div class="login-form">
          <div class="form-item">
            <label class="form-label">用户名或邮箱</label>
            <t-input 
              v-model="unifiedForm.usernameOrEmail"
              placeholder="请输入用户名或邮箱地址"
              @blur="validateUsernameOrEmail"
            />
            <div v-if="errors.usernameOrEmail" class="error-message">{{ errors.usernameOrEmail }}</div>
          </div>
          
          <div class="form-item">
            <label class="form-label">密码</label>
            <t-input 
              v-model="unifiedForm.password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="请输入密码"
              @blur="validateUnifiedPassword"
              :clearable="false"
            />
            <div v-if="errors.password" class="error-message">{{ errors.password }}</div>
          </div>

          <div class="form-options">
            <t-checkbox v-model="unifiedForm.remember">记住登录</t-checkbox>
            <t-space>
              <t-link theme="primary" @click="showForgotPassword = true">忘记密码？</t-link>
            </t-space>
          </div>

          <t-button 
            theme="primary"
            size="large"
            block
            :loading="isLoading"
            @click="handleUnifiedLogin"
            :disabled="isLoading"
          >
            {{ isLoading ? '登录中...' : '立即登录' }}
          </t-button>
        </div>
      </t-tab-panel>

      <t-tab-panel :value="'qr'" label="扫码登录">
        <!-- 扫码登录 -->
        <div class="qr-login">
          <div class="qr-code">
            <div class="qr-code-container">
              <img src="/src/pic/android.png" alt="扫码登录" width="160" height="160" />
            </div>
          </div>
          <div class="qr-status">
            <p class="qr-tip">
              <t-icon name="mobile" />
              使用西工程大APP扫码登录
            </p>
          </div>
        </div>
      </t-tab-panel>
    </t-tabs>

    <!-- 注册链接 -->
    <div class="register-link">
      <span>还没有账号？</span>
      <t-space>
        <t-link theme="primary" @click="showRegister = true">立即注册</t-link>
      </t-space>
    </div>
  </div>
    </t-card>

    <!-- 注册弹窗 -->
    <t-dialog
      v-model:visible="showRegister"
      header="用户注册"
      :width="380"
      :footer="false"
    >
      <div class="register-form">
        <div class="form-item">
          <label class="form-label">用户名</label>
          <t-input 
            v-model="registerForm.username"
            placeholder="请输入用户名"
            @blur="validateRegisterUsername"
          />
          <div v-if="registerErrors.username" class="error-message">{{ registerErrors.username }}</div>
        </div>

        <div class="form-item">
          <label class="form-label">邮箱</label>
          <t-input 
            v-model="registerForm.email"
            type="email"
            placeholder="请输入邮箱地址"
            @blur="validateRegisterEmail"
          />
          <div v-if="registerErrors.email" class="error-message">{{ registerErrors.email }}</div>
        </div>

        <div class="form-item">
          <label class="form-label">密码</label>
          <t-input 
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码"
            @blur="validateRegisterPassword"
          />
          <div v-if="registerErrors.password" class="error-message">{{ registerErrors.password }}</div>
        </div>

        <div class="form-item">
          <label class="form-label">确认密码</label>
          <t-input 
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            @blur="validateConfirmPassword"
          />
          <div v-if="registerErrors.confirmPassword" class="error-message">{{ registerErrors.confirmPassword }}</div>
        </div>

        <div class="register-buttons">
          <t-button 
            theme="primary"
            size="large"
            block
            :loading="isRegistering"
            @click="handleRegister"
            :disabled="isRegistering"
          >
            {{ isRegistering ? '注册中...' : '立即注册' }}
          </t-button>
          
          <t-button 
            variant="outline"
            size="large"
            block
            @click="showRegister = false"
            style="margin-top: 8px;"
          >
            取消
          </t-button>
        </div>

      </div>
    </t-dialog>
    
    <!-- 忘记密码弹窗 -->
    <t-dialog
      v-model:visible="showForgotPassword"
      header="忘记密码"
      :width="380"
      :footer="false"
    >
      <div class="forgot-password-form">
        <div v-if="forgotPasswordStep === 1">
          <p class="forgot-tip">请输入您的邮箱地址，我们将向您发送密码重置链接。</p>
          
          <div class="form-item">
            <label class="form-label">邮箱地址</label>
            <t-input 
              v-model="forgotPasswordForm.email"
              type="email"
              placeholder="请输入注册时使用的邮箱地址"
              @blur="validateForgotEmail"
            />
            <div v-if="forgotPasswordErrors.email" class="error-message">{{ forgotPasswordErrors.email }}</div>
          </div>

          <div class="forgot-buttons">
            <t-button 
              theme="primary"
              size="large"
              block
              :loading="isSendingResetEmail"
              @click="handleSendResetEmail"
              :disabled="isSendingResetEmail"
            >
              {{ isSendingResetEmail ? '发送中...' : '发送重置邮件' }}
            </t-button>
            
            <t-button 
              variant="outline"
              size="large"
              block
              @click="closeForgotPasswordDialog"
              style="margin-top: 8px;"
            >
              取消
            </t-button>
          </div>
        </div>

        <div v-else-if="forgotPasswordStep === 2">
          <div class="success-message">
            <t-icon name="check-circle" size="48px" style="color: #52c41a; margin-bottom: 16px;" />
            <h3>邮件发送成功！</h3>
            <p class="success-tip">
              我们已向 <strong>{{ forgotPasswordForm.email }}</strong> 发送了密码重置邮件。
              <br>请查收邮件并点击其中的重置链接来设置新密码。
            </p>
            <p class="note">
              <small>如果您没有收到邮件，请检查垃圾邮件文件夹，或稍后重试。</small>
            </p>
          </div>

          <div class="forgot-buttons">
            <t-button 
              theme="primary"
              size="large"
              block
              @click="closeForgotPasswordDialog"
            >
              我知道了
            </t-button>
            
            <t-button 
              variant="outline"
              size="large"
              block
              @click="resetForgotPasswordForm"
              style="margin-top: 8px;"
            >
              重新发送
            </t-button>
          </div>
        </div>
      </div>
    </t-dialog>
    
    <!-- 版权信息 -->
    <div class="copyright">
      Copyright © 2024 - 2025 网信π对. All Rights Reserved.
    </div>
    </div>
  </div>
</template>

<script>
import { authStore } from '../../store/auth.js'
import { useMessage } from '../../composables/useMessage.js'

export default {
  name: 'Login',
  setup() {
    const message = useMessage()
    return {
      message
    }
  },
  data() {
    return {
      activeTab: 'account',
      showPassword: false,
      isLoading: false,
      isRegistering: false,
      showRegister: false,
      codeCountdown: 0,
      isDark: false,
      unifiedForm: {
        usernameOrEmail: '',
        password: '',
        remember: false
      },
      registerForm: {
        username: '',
        email: '',
        password: '',
        confirmPassword: ''
      },
      errors: {},
      registerErrors: {},
      // 忘记密码相关数据
      showForgotPassword: false,
      forgotPasswordStep: 1, // 1: 输入邮箱, 2: 发送成功
      isSendingResetEmail: false,
      forgotPasswordForm: {
        email: ''
      },
      forgotPasswordErrors: {}
    }
  },
  methods: {
    handleTabChange(value) {
      this.activeTab = value
      // 清空错误信息
      this.errors = {}
    },
    validateUsernameOrEmail() {
      if (!this.unifiedForm.usernameOrEmail) {
        this.errors.usernameOrEmail = '请输入用户名或邮箱地址'
      } else if (this.unifiedForm.usernameOrEmail.length < 3) {
        this.errors.usernameOrEmail = '用户名或邮箱至少3个字符'
      } else {
        delete this.errors.usernameOrEmail
      }
    },
    validateUnifiedPassword() {
      if (!this.unifiedForm.password) {
        this.errors.password = '请输入密码'
      } else if (this.unifiedForm.password.length < 6) {
        this.errors.password = '密码至少6个字符'
      } else {
        delete this.errors.password
      }
    },
    async handleUnifiedLogin() {
      this.validateUsernameOrEmail()
      this.validateUnifiedPassword()
      
      if (this.errors.usernameOrEmail || this.errors.password) {
        return
      }

      this.isLoading = true
      try {
        const response = await fetch('http://localhost:8000/api/auth/login/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            username_or_email: this.unifiedForm.usernameOrEmail,
            password: this.unifiedForm.password
          })
        })

        const data = await response.json()
        
        if (response.ok) {
          // 使用状态管理保存登录信息
          authStore.login(data.access_token, data.user)
          
          // 显示成功消息
          this.message.success('登录成功！')
          
          // 跳转到聊天界面
          this.$router.push('/')
        } else {
          // 使用全局消息提示显示错误
          this.message.handleApiError(response, data, '登录失败')
        }
      } catch (error) {
        // 使用全局消息提示处理网络错误
        this.message.handleNetworkError(error, '网络错误，请稍后重试')
      } finally {
        this.isLoading = false
      }
    },

    // 注册相关验证方法
    validateRegisterUsername() {
      if (!this.registerForm.username) {
        this.registerErrors.username = '请输入用户名'
      } else if (this.registerForm.username.length < 3) {
        this.registerErrors.username = '用户名至少3个字符'
      } else {
        delete this.registerErrors.username
      }
    },

    validateRegisterEmail() {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!this.registerForm.email) {
        this.registerErrors.email = '请输入邮箱地址'
      } else if (!emailRegex.test(this.registerForm.email)) {
        this.registerErrors.email = '请输入正确的邮箱地址'
      } else {
        delete this.registerErrors.email
      }
    },
    validateRegisterPassword() {
      if (!this.registerForm.password) {
        this.registerErrors.password = '请输入密码'
      } else if (this.registerForm.password.length < 6) {
        this.registerErrors.password = '密码至少6个字符'
      } else {
        delete this.registerErrors.password
      }
    },
    validateConfirmPassword() {
      if (!this.registerForm.confirmPassword) {
        this.registerErrors.confirmPassword = '请确认密码'
      } else if (this.registerForm.password !== this.registerForm.confirmPassword) {
        this.registerErrors.confirmPassword = '两次输入的密码不一致'
      } else {
        delete this.registerErrors.confirmPassword
      }
    },
    async handleRegister() {
      // 验证所有字段
      this.validateRegisterUsername()
      this.validateRegisterEmail()
      this.validateRegisterPassword()
      this.validateConfirmPassword()
      
      if (Object.keys(this.registerErrors).length > 0) {
        return
      }

      this.isRegistering = true
      try {
        const response = await fetch('http://localhost:8000/api/auth/register/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            username: this.registerForm.username,
            email: this.registerForm.email,
            password: this.registerForm.password,
            nickname: this.registerForm.username, // 使用用户名作为默认昵称
            skip_email_verification: true // 跳过邮箱验证用于测试
          })
        })

        const data = await response.json()
        
        if (response.ok) {
          // 注册成功，关闭弹窗并提示用户登录
          this.showRegister = false
          this.registerForm = {
            username: '',
            email: '',
            password: '',
            confirmPassword: ''
          }
          this.registerErrors = {}
          
          // 显示成功消息
          this.message.success('注册成功！请使用新账号登录。')
        } else {
          // 使用全局消息提示显示错误
          this.message.handleApiError(response, data, '注册失败')
        }
      } catch (error) {
        // 使用全局消息提示处理网络错误
        this.message.handleNetworkError(error, '网络错误，请稍后重试')
      } finally {
        this.isRegistering = false
      }
    },
    // 忘记密码相关方法
    validateForgotEmail() {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!this.forgotPasswordForm.email) {
        this.forgotPasswordErrors.email = '请输入邮箱地址'
      } else if (!emailRegex.test(this.forgotPasswordForm.email)) {
        this.forgotPasswordErrors.email = '请输入有效的邮箱地址'
      } else {
        delete this.forgotPasswordErrors.email
      }
    },
    async handleSendResetEmail() {
      // 验证邮箱
      this.validateForgotEmail()
      
      if (Object.keys(this.forgotPasswordErrors).length > 0) {
        return
      }

      this.isSendingResetEmail = true
      try {
        const response = await fetch('http://localhost:8000/api/auth/forgot-password/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: this.forgotPasswordForm.email
          })
        })

        const data = await response.json()
        
        if (response.ok) {
          // 发送成功，切换到成功页面
          this.forgotPasswordStep = 2
        } else {
          // 使用全局消息提示显示错误
          this.message.handleApiError(response, data, '发送重置邮件失败')
        }
      } catch (error) {
        // 使用全局消息提示处理网络错误
        this.message.handleNetworkError(error, '网络错误，请稍后重试')
      } finally {
        this.isSendingResetEmail = false
      }
    },
    closeForgotPasswordDialog() {
      this.showForgotPassword = false
      this.resetForgotPasswordForm()
    },
    resetForgotPasswordForm() {
      this.forgotPasswordStep = 1
      this.forgotPasswordForm.email = ''
      this.forgotPasswordErrors = {}
      this.isSendingResetEmail = false
    }
  },
  mounted() {
    // 检测当前主题模式
    const savedTheme = localStorage.getItem('theme');
    this.isDark = savedTheme === 'dark';
  }
}
</script>

<style scoped>
/* 页面包装器样式 */
.page-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 导航菜单样式 */
.nav-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.login-container {
  flex: 1;
  margin-top: 64px; /* 为导航菜单留出空间 */
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5%;
  position: relative;
  overflow: hidden;
  background-image: url('/src/pic/tuan1.svg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

/* 左侧装饰图案 */
.left-decoration {
  flex: 0 0 auto;
  margin-right: 3%;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: translateY(-40px) scale(1.1);
}

.decoration-svg {
  max-width: 580px;
  height: auto;
  opacity: 0.9;
  filter: drop-shadow(0 6px 25px rgba(0, 0, 0, 0.15));
  animation: float 6s ease-in-out infinite;
  transform: translateY(80px);
}

@keyframes float {
  0%, 100% {
    transform: translateY(80px);
  }
  50% {
    transform: translateY(70px);
  }
}

/* 登录卡片 */
.login-card {
  flex-shrink: 0;
  margin-left: 10%;
}

.login-card .t-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

/* 卡片标题样式 */
.login-card :deep(.t-card__header) {
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px 24px;
}

.login-card :deep(.t-card__title) {
  font-size: 20px;
  font-weight: 600;
  text-align: center;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 0;
}

.login-content {
  padding: 0;
}

.login-content :deep(.t-tabs) {
  margin-bottom: 24px;
}

.login-content :deep(.t-tabs__nav) {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 4px;
  display: flex;
  justify-content: center; /* 水平居中 */
  gap: 2px; 
}

.login-content :deep(.t-tabs__nav-item) {
  border-radius: 6px;
  transition: all 0.3s ease;
  flex: 1; 
  text-align: center;
  margin: 0; 
  padding: 10px 16px; /* 调整内边距，优化视觉与交互 */
  min-width: 0; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
}

.login-content :deep(.t-tabs__nav-item--active) {
  background: #4A90E2 !important;
  color: white !important;
}

.login-content :deep(.t-tabs__nav-item-text-wrapper) {
  font-size: 14px; 
  font-weight: 500; 
  white-space: nowrap; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  width: 100%; 
  height: 100%; 
}

/* 表单样式 */
.login-form {
  margin-bottom: 20px;
  margin-top: 30px; /* 增加顶部边距，让表单向下移动 */
}

.form-item {
  margin-bottom: 24px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  color: #333;
  font-weight: 500;
  font-size: 14px;
}

/* TDesign输入框样式调整 */
.form-item :deep(.t-input) {
  width: 100%;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  background: white;
  transition: all 0.3s ease;
}

.form-item :deep(.t-input__inner) {
  padding: 12px 16px;
  border: none !important;
  border-radius: 8px;
  font-size: 14px;
  background: transparent;
  box-shadow: none !important;
}

.form-item :deep(.t-input--focused) {
  border-color: #4A90E2;
}

.form-item :deep(.t-input--focused .t-input__inner) {
  border: none !important;
  box-shadow: none !important;
}

/* TDesign按钮样式调整 */
.form-item :deep(.t-button) {
  transition: all 0.3s ease;
}

/* 登录按钮特殊样式 - 增加上边距 */
.login-form > .t-button {
  margin-top: 20px; /* 让登录按钮向下移动 */
}

.form-item :deep(.t-button--variant-text) {
  color: #666;
  padding: 4px;
}

.form-item :deep(.t-button--variant-outline) {
  border: none !important;
  color: #4A90E2 !important;
  background: transparent !important;
  font-size: 12px;
  padding: 6px 12px !important;
  border-radius: 4px !important;
  text-decoration: underline;
}

.form-item :deep(.t-button--variant-outline:hover) {
  background: rgba(74, 144, 226, 0.1) !important;
  color: #357abd !important;
  text-decoration: none;
}

.form-item :deep(.t-button--theme-primary) {
  background: #4A90E2;
  border-color: #4A90E2;
}

.form-item :deep(.t-button--theme-primary:hover) {
  background: #357abd;
  border-color: #357abd;
}

.error-message {
  color: #ff4757;
  font-size: 12px;
  margin-top: 4px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.checkbox-wrapper {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.checkbox {
  margin-right: 8px;
}

.checkbox-label {
  font-size: 14px;
  color: #666;
}

.forgot-link {
  color: #4A90E2;
  text-decoration: none;
  font-size: 14px;
}

.forgot-link:hover {
  color: #357abd;
  text-decoration: underline;
}

/* 扫码登录 */
.qr-login {
  text-align: center;
  padding: 20px 0;
}

.qr-code {
  margin-bottom: 16px;
}

.qr-placeholder {
  display: inline-block;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.qr-placeholder img {
  display: block;
  border-radius: 8px;
}

.qr-tip {
  color: #666;
  margin-bottom: 20px;
  font-size: 14px;
}

.register-link {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: #666;
}

.register-btn {
  color: #4A90E2;
  text-decoration: none;
  margin-left: 8px;
}

.register-btn:hover {
  text-decoration: underline;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
    padding: 20px;
  }
  
  .left-decoration {
    padding-right: 0;
    padding-bottom: 20px;
  }
  
  .decoration-svg {
    max-width: 360px;
  }
}

@media (max-width: 480px) {
  .login-card {
    margin: 20px;
    padding: 30px 20px;
  }
  
  .login-title {
    font-size: 24px;
  }
  
  .social-login {
    gap: 12px;
  }
  
  .social-btn {
    width: 40px;
    height: 40px;
  }
  
  .decoration-svg {
    max-width: 280px;
  }
}

/* 版权信息样式 */
.copyright {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  color: #888888;
  font-size: 12px;
  text-align: center;
  z-index: 10;
}

/* 忘记密码弹窗样式 */
.forgot-password-form {
  padding: 20px 0;
}

.forgot-tip {
  color: #666;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 20px;
  text-align: center;
}

.forgot-buttons {
  margin-top: 24px;
}

.success-message {
  text-align: center;
  padding: 20px 0;
}

.success-message h3 {
  color: #333;
  margin: 16px 0;
  font-size: 18px;
  font-weight: 600;
}

.success-tip {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 16px;
}

.success-tip strong {
  color: #333;
  font-weight: 600;
}

.note {
  color: #999;
  font-size: 12px;
  line-height: 1.4;
  margin-top: 16px;
}
</style>
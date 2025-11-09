"""
邮件服务模块
提供邮件验证码发送和验证功能
"""
import redis
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        # Redis连接配置
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True
        )
        
        # 邮件服务器配置
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.qq.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.email_user = os.getenv('EMAIL_USER', '')
        self.email_password = os.getenv('EMAIL_PASSWORD', '')
        
        # 验证码配置
        self.code_length = 6
        self.code_expire_minutes = 10
        self.send_limit_per_hour = 5
    
    def generate_verification_code(self) -> str:
        """生成6位数字验证码"""
        return ''.join(random.choices(string.digits, k=self.code_length))
    
    def check_email_send_limit(self, email: str) -> bool:
        """检查邮件发送频率限制"""
        try:
            key = f"email_limit:{email}"
            current_count = self.redis_client.get(key)
            
            if current_count is None:
                return True
            
            return int(current_count) < self.send_limit_per_hour
        except Exception:
            # Redis连接失败时允许发送
            return True
    
    def send_verification_code(self, email: str, purpose: str = "register") -> Dict[str, Any]:
        """发送验证码邮件"""
        try:
            # 检查发送频率限制
            if not self.check_email_send_limit(email):
                return {
                    "success": False,
                    "message": "发送频率过高，请稍后再试"
                }
            
            # 生成验证码
            code = self.generate_verification_code()
            
            # 存储验证码到Redis
            code_key = f"email_code:{email}:{purpose}"
            self.redis_client.setex(
                code_key, 
                timedelta(minutes=self.code_expire_minutes), 
                code
            )
            
            # 更新发送计数
            limit_key = f"email_limit:{email}"
            current_count = self.redis_client.get(limit_key) or 0
            self.redis_client.setex(
                limit_key,
                timedelta(hours=1),
                int(current_count) + 1
            )
            
            # 发送邮件（如果配置了邮件服务器）
            if self.email_user and self.email_password:
                self._send_email(email, code, purpose)
            
            return {
                "success": True,
                "message": "验证码发送成功",
                "code": code if not self.email_user else None  # 开发环境返回验证码
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"发送失败: {str(e)}"
            }
    
    def verify_code(self, email: str, code: str, purpose: str = "register") -> Dict[str, Any]:
        """验证邮件验证码"""
        try:
            code_key = f"email_code:{email}:{purpose}"
            stored_code = self.redis_client.get(code_key)
            
            if not stored_code:
                return {
                    "success": False,
                    "message": "验证码已过期或不存在"
                }
            
            if stored_code != code:
                return {
                    "success": False,
                    "message": "验证码错误"
                }
            
            # 验证成功，删除验证码
            self.redis_client.delete(code_key)
            
            return {
                "success": True,
                "message": "验证成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"验证失败: {str(e)}"
            }
    
    def _send_email(self, to_email: str, code: str, purpose: str):
        """发送邮件（需要配置SMTP服务器）"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = to_email
            
            purpose_map = {
                "register": "注册验证",
                "reset_password": "密码重置",
                "login": "登录验证"
            }
            
            subject = f"【智语AI】{purpose_map.get(purpose, '验证')}码"
            msg['Subject'] = subject
            
            body = f"""
            <html>
            <body>
                <h2>智语AI - 邮箱验证</h2>
                <p>您的验证码是：<strong style="color: #007bff; font-size: 18px;">{code}</strong></p>
                <p>验证码有效期为 {self.code_expire_minutes} 分钟，请及时使用。</p>
                <p>如果这不是您的操作，请忽略此邮件。</p>
                <hr>
                <p style="color: #666; font-size: 12px;">此邮件由系统自动发送，请勿回复。</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            print(f"邮件发送失败: {e}")

# 创建全局实例
email_service = EmailService()
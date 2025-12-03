"""
用户认证相关的API路由
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from fastapi_app.database import get_db
from fastapi_app.models import User
from fastapi_app.schemas import UserCreate, UserLogin, LoginResponse, UserResponse
from fastapi_app.auth import (
    authenticate_user, authenticate_user_by_username_or_email, create_access_token, create_user, check_user_exists,
    get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from fastapi_app.email_service import email_service

router = APIRouter()


@router.post("/register/", response_model=LoginResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    try:
        # 检查邮箱是否已存在
        if check_user_exists(db, email=user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )
        

        if user_data.username and check_user_exists(db, username=user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已被注册"
            )
        
        # 创建用户
        user_dict = user_data.dict()
        # 移除验证相关字段（如果存在）
        user_dict.pop('email_code', None)
        user_dict.pop('skip_email_verification', None)
        
        db_user = create_user(db, user_dict)
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.id}, expires_delta=access_token_expires
        )
        
        # 更新最后登录时间
        db_user.last_login = datetime.now()
        db.commit()
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.from_orm(db_user),
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"用户注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post("/login/", response_model=LoginResponse)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """用户登录（支持用户名或邮箱）"""
    try:
        # 验证用户（支持用户名或邮箱登录）
        user = authenticate_user_by_username_or_email(
            db, 
            user_credentials.username_or_email,
            user_credentials.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名/邮箱或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if user.is_active != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="账户已被禁用"
            )
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.id}, expires_delta=access_token_expires
        )
        
        # 更新最后登录时间
        user.last_login = datetime.now()
        db.commit()
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.from_orm(user),
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"用户登录失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )


@router.get("/me/", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return UserResponse.from_orm(current_user)


@router.post("/logout/")
async def logout():
    """用户登出（前端需要删除token）"""
    return {"message": "登出成功"}


@router.get("/verify/")
async def verify_token(current_user: User = Depends(get_current_active_user)):
    """验证token是否有效"""
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username or current_user.nickname
    }


# 邮箱验证相关的Pydantic模型
class EmailVerificationRequest(BaseModel):
    """邮箱验证请求模型"""
    email: str
    purpose: str = "register"  # register, reset_password


class EmailVerificationVerify(BaseModel):
    """邮箱验证码验证模型"""
    email: str
    code: str


@router.post("/send-verification-code/")
async def send_verification_code(request: EmailVerificationRequest):
    """发送邮箱验证码"""
    try:
        # 检查发送频率限制
        if not email_service.check_email_send_limit(request.email):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="发送过于频繁，请稍后再试"
            )
        
        # 发送验证码
        result = email_service.send_verification_code(request.email, request.purpose)
        
        if result['success']:
            return {
                "success": True,
                "message": result['message'],
                "debug_code": result.get('code')  # 仅在调试模式下返回
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"发送验证码失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送验证码失败"
        )


@router.post("/verify-email-code/")
async def verify_email_code(request: EmailVerificationVerify):
    """验证邮箱验证码"""
    try:
        result = email_service.verify_code(request.email, request.code)
        
        if result['success']:
            return {
                "success": True,
                "message": result['message']
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"验证邮箱验证码失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证失败"
        )


# 忘记密码相关的Pydantic模型
class ForgotPasswordRequest(BaseModel):
    """忘记密码请求模型"""
    email: str


class ResetPasswordRequest(BaseModel):
    """重置密码请求模型"""
    email: str
    code: str
    new_password: str


@router.post("/forgot-password/")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """发送密码重置邮件"""
    try:
        # 检查邮箱是否存在
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            # 为了安全考虑，不透露邮箱是否存在，统一返回成功消息
            return {
                "success": True,
                "message": "如果该邮箱已注册，您将收到密码重置邮件"
            }
        
        # 检查发送频率限制
        if not email_service.check_email_send_limit(request.email):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="发送过于频繁，请稍后再试"
            )
        
        # 发送密码重置验证码
        result = email_service.send_verification_code(request.email, "reset_password")
        
        if result['success']:
            return {
                "success": True,
                "message": "密码重置邮件已发送，请查收邮件",
                "debug_code": result.get('code')  # 仅在调试模式下返回
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"发送密码重置邮件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送密码重置邮件失败"
        )


@router.post("/reset-password/")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """重置密码"""
    try:
        # 验证邮箱验证码
        verification_result = email_service.verify_code(request.email, request.code)
        if not verification_result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=verification_result['message']
            )
        
        # 查找用户
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 验证新密码
        if len(request.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码至少需要6个字符"
            )
        
        # 更新密码（需要导入密码哈希函数）
        from fastapi_app.auth import get_password_hash
        user.hashed_password = get_password_hash(request.new_password)
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        return {
            "success": True,
            "message": "密码重置成功，请使用新密码登录"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"重置密码失败: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置密码失败"
        )
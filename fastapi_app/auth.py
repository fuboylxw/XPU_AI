"""
用户认证相关工具函数
"""
import os
import uuid
import hashlib
import json
import base64
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from fastapi_app.database import get_db
from fastapi_app.models import User
from fastapi_app.schemas import TokenData

# JWT配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here-change-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

# HTTP Bearer认证
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # 使用简单的SHA256哈希验证
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌（简化版本）"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire.timestamp()})
    
    # 简单的base64编码作为token
    token_str = json.dumps(to_encode)
    token_bytes = token_str.encode('utf-8')
    token = base64.b64encode(token_bytes).decode('utf-8')
    return token


def verify_token(token: str) -> Optional[TokenData]:
    """验证令牌"""
    try:
        # 解码base64
        token_bytes = base64.b64decode(token.encode('utf-8'))
        token_str = token_bytes.decode('utf-8')
        payload = json.loads(token_str)
        
        # 检查过期时间
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            return None
            
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        token_data = TokenData(user_id=user_id)
        return token_data
    except Exception:
        return None


def authenticate_user_by_username_or_email(db: Session, username_or_email: str, password: str) -> Optional[User]:
    """通过用户名或邮箱验证用户"""
    user = None
    
    # 判断输入是邮箱还是用户名（简单的邮箱格式检查）
    if "@" in username_or_email and "." in username_or_email:
        # 看起来像邮箱，先尝试邮箱查找
        user = db.query(User).filter(User.email == username_or_email).first()
        if not user:
            # 如果邮箱没找到，再尝试用户名查找
            user = db.query(User).filter(User.username == username_or_email).first()
    else:
        # 看起来像用户名，先尝试用户名查找
        user = db.query(User).filter(User.username == username_or_email).first()
        if not user:
            # 如果用户名没找到，再尝试邮箱查找
            user = db.query(User).filter(User.email == username_or_email).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    return user


def authenticate_user(db: Session, login_type: str, login_value: str, password: str) -> Optional[User]:
    """验证用户（保留原有接口兼容性）"""
    # 根据登录类型查找用户
    if login_type == "username":
        user = db.query(User).filter(User.username == login_value).first()
    elif login_type == "email":
        user = db.query(User).filter(User.email == login_value).first()
    elif login_type == "phone":
        user = db.query(User).filter(User.phone == login_value).first()
    else:
        return None
    
    if not user:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if current_user.is_active != 1:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def generate_user_id() -> str:
    """生成用户ID"""
    return str(uuid.uuid4()).replace('-', '')[:32]


def create_user(db: Session, user_data: dict) -> User:
    """创建用户"""
    # 生成用户ID
    user_id = generate_user_id()
    
    # 创建用户对象
    db_user = User(
        id=user_id,
        username=user_data.get("username"),
        email=user_data["email"],  # 邮箱为必填字段
        password_hash=get_password_hash(user_data["password"]),
        nickname=user_data.get("nickname") or user_data.get("username") or "用户" + user_id[:8],
        is_active=1
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


def check_user_exists(db: Session, email: str = None, username: str = None) -> bool:
    """检查用户是否已存在（通过邮箱或用户名）"""
    if email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return True
    
    if username:
        user = db.query(User).filter(User.username == username).first()
        if user:
            return True
    
    return False
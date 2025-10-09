@echo off
echo 启动完整项目...
start "后端服务" cmd /k "cd chat-backend && pip install -r requirements.txt && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 5 /nobreak
start "前端服务" cmd /k "cd chat-frontend && npm install && npm start"
echo 项目启动中，请等待...
echo 后端服务: http://202.200.206.248:8000
echo 前端应用: http://202.200.206.248:3000
echo API文档: http://202.200.206.248:8000/docs
pause
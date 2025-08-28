@echo off
echo 启动新生信息问答Agent系统...
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python环境，请先安装Python
    pause
    exit /b 1
)

REM 安装依赖
echo 安装依赖包...
pip install -r requirements.txt

REM 检查环境变量
if not exist .env (
    echo 警告: 未找到.env文件，请配置DeepSeek API密钥
    echo 创建示例.env文件...
    echo DEEPSEEK_API_KEY=your_deepseek_api_key_here > .env
    echo DEBUG=False >> .env
    echo LOG_LEVEL=INFO >> .env
    echo MCP_SERVER_PORT=3000 >> .env
    echo.
    echo 请编辑.env文件，填入您的DeepSeek API密钥
    pause
)

REM 启动Streamlit应用
echo 启动Web界面...
streamlit run main.py --server.port 8501 --server.address 0.0.0.0

pause
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 2307;

// 启用JSON解析中间件
app.use(express.json());

// 提供静态文件
app.use(express.static(path.join(__dirname, 'public')));

// 处理聊天API请求
app.post('/api/chat', (req, res) => {
  const userMessage = req.body.message;
  
  // 根据用户消息生成格式化响应
  const formattedResponse = formatResponse(userMessage);
  
  // 返回格式化的响应
  res.json({ response: formattedResponse });
});

// 格式化响应函数
function formatResponse(message) {
  // 这里可以根据需要处理不同类型的消息
  // 示例：将响应格式化为分点、换行和缩进的格式
  
  let response = "以下是您需要的信息：\n\n";
  
  // 添加分点内容
  response += "1. **第一要点**\n";
  response += "   - 子要点一\n";
  response += "   - 子要点二\n\n";
  
  response += "2. **第二要点**\n";
  response += "   - 详细说明：\n";
  response += "     * 进一步解释\n";
  response += "     * 补充信息\n\n";
  
  response += "3. **第三要点**\n";
  response += "   ```javascript\n";
  response += "   // 代码示例\n";
  response += "   function example() {\n";
  response += "     console.log('格式规整的代码');\n";
  response += "   }\n";
  response += "   ```\n\n";
  
  response += "希望这些信息对您有所帮助！";
  
  return response;
}

// 启动服务器
app.listen(PORT, () => {
  console.log(`服务器运行在 http://localhost:${PORT}`);
});
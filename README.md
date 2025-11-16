# Vue 3 + Vite

这是 XPU_AI 项目的前端部分，基于 Vue 3 + Vite 构建，提供一个带有对话式 AI 聊天界面的单页应用。

本仓库为教学/产品原型用途，包含实时消息流、语音输入、电话通话模态、主题（浅/深色）切换以及骨架屏（skeleton）等常见交互。

## 主要特性

- Vue 3 + Vite 快速开发体验
- 响应式聊天界面：`src/views/ChatApp.vue`
- 电话/语音呼叫模态：`src/views/CallModal.vue`
- 主题自动切换（浅/深色），通过 `document.body.classList.toggle('dark', isDark)` 控制
- 骨架屏 + shimmer 加载动画以提升加载体验
- 文件上传（拖拽/选择）、消息流式输出、可编辑/复制消息

## 项目亮点

- 体验细节拉满：Skeleton 骨架屏 + Shimmer 动效、输入区聚焦无彩色描边、流式回答打字提示等，减少空窗时间与突兀感。
- 主题无感切换：浅/深色一键切换并自动应用 Logo 与样式，夜间观感友好。
- 可访问性友好：聊天区 `role="log"` + `aria-live="polite"`，输入与操作具备语义化与快捷键（Ctrl/Cmd+Enter 发送、Shift+Enter 换行、Esc 停止）。
- 多模态输入：文本、语音按钮与电话通话 UI 一体化，通话计时稳定显示（父组件计时传递到模态）。
- 文件交互清晰：拖拽/选择上传、类型图标与大小展示、可移除操作，状态明确。
- 流式响应可控：SSE 流式输出过程可随时停止，提升容错与用户掌控感。
- 工程化完善：ESLint + Prettier + husky + lint-staged，提交前自动格式化与校验，保持代码一致性。
- 结构易扩展：`views/components/utils/store/router` 分层清晰，便于后续接入更多 AI 能力与业务模块。

## 目录结构（重要文件）

- `index.html` — 应用入口 HTML
- `src/main.js` — Vue 应用初始化
- `src/App.vue` — 顶层组件
- `src/views/ChatApp.vue` — 主聊天页面，包含侧边栏、消息流、输入区
- `src/views/CallModal.vue` — 电话通话模态实现
- `src/components/Icon.vue` — 项目图标/SVG 封装组件
- `src/composables/useMessage.js` — 复用的消息相关逻辑（若使用）
- `src/store/auth.js` — 简单的认证/用户状态管理
- `src/router/index.js` — 路由定义
- `src/utils/markdown.js` — Markdown 渲染工具
- `public/` — 静态资源

更多细节可在 `src/` 下逐个文件查看。

## 环境要求

- Node.js >= 18（推荐使用 LTS 版本）
- 推荐在 Windows 下使用 PowerShell 或者 WSL 来运行开发命令

## 快速开始 (开发)

1. 安装依赖

```powershell
npm install
```

2. 启动开发服务器

```powershell
npm run dev
```

3. 本地预览生产构建

```powershell
npm run build
npm run preview
```

## 常用脚本

- `npm run dev` — 启动 Vite 开发服务器
- `npm run build` — 打包生产构建
- `npm run preview` — 本地预览构建产物
- `npm run lint` — 运行 ESLint 静态检查
- `npm run lint:fix` — 自动修复可修复的 lint 问题
- `npm run format` — 使用 Prettier 格式化代码

这些脚本在 `package.json` 中定义。

## 开发说明 & 注意点

- 主题：项目使用 `isDark` 状态来控制 `body` 上的 `dark` 类，样式根据 `body.dark` 做区分，若修改主题相关代码请同步更新样式变量。
- 骨架屏：在 `ChatApp.vue` 中，`loading` 标志用于控制是否显示 skeleton 占位，后端接口请求时可置为 `true` 来展示。
- 呼叫计时器：通话时长由父组件维护并通过 `:call-duration` 传递给 `CallModal`（注意模板中 prop 的 kebab-case 与组件内 camelCase 的对应）。
- 无障碍：聊天区使用 `role="log"` 和 `aria-live="polite"` 提高可访问性；若添加动态内容应考虑可访问性通知。

## 调试与排错

- 若发现样式异常（如内层输入框聚焦出现彩色描边），检查 `src/views/ChatApp.vue` 中 `.input-wrapper:focus-within` 与 `.message-input:focus` 样式是否被覆盖。
- 若构建或依赖问题，请先核对 Node 版本并尝试删除 `node_modules` 与 `package-lock.json` 后重新安装。

## 贡献指南

欢迎贡献。请遵循以下建议：

- 在提交前运行 `npm run format` 和 `npm run lint:fix`。
- 提交信息请简洁描述变更意图。

若需要我帮你：我可以根据你的偏好补充更详细的开发流程、单元测试说明或部署脚本。

## 许可

该仓库默认未指定特殊开源许可证。请根据需要添加 `LICENSE` 文件来声明许可条款。


# TOOLS.md - Local Notes

## 国内网络环境关键经验

- **Vercel**: 国内被墙，无法直接访问
- **GitHub Pages**: 国内偶尔能访问，不稳定
- **Firebase**: 国内被墙
- **Cloudflare Tunnel**: 国内被墙
- **Gitee Pages**: 国内可用，但需实名认证
- **DeepSeek API**: 国内直连，免费额度，`api.deepseek.com`
- **智谱AI API**: 国内直连，`open.bigmodel.cn`，手机端注册找API Key较困难
- **LeanCloud**: 国内可用，免费云数据库，适合多设备数据同步

## z-ai-web-dev-sdk 使用经验

- 是 Node.js SDK，不是 Python 包
- Python 后端调用需用 `subprocess` 调 `z-ai chat` CLI，但返回原始JSON需解析
- FastAPI 后端中直接用 `asyncio.run()` 调 SDK 会冲突，需在 Node.js 后端使用
- `z-ai chat --prompt` 返回的是完整JSON响应，不是纯文本

## 服务器环境

- 公网IP: 8.217.147.255
- 所有端口被云平台防火墙封禁，外网无法访问
- `z-ai` CLI 和 `z-ai-web-dev-sdk` 可用
- Python 3.12 + Node.js 24 可用

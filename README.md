# ai-chat-web

一个开箱即用的 AI 聊天界面：打开浏览器就能用，支持 DeepSeek、通义千问、Kimi、GLM 等国内外主流大模型，对话记录保存在你自己的电脑上，无需注册任何平台账号。

---

## 🤔 这是什么？怎么工作的？

这个项目让你**用自己的 API 密钥**直接调用模型，同时提供一个比官方网页更好用的聊天界面。

### 运行原理

```
你 ──浏览器──▶ 本机 Flask 服务 (:5030) ──代理转发──▶ AI 服务商 (DeepSeek / 通义 / Kimi…)
                   ▲                                              │
                   │          AI 回复原路返回                       │
                   └──────────────────────────────────────────────┘
```

你需要的只有两样东西：
1. **一个 API 密钥** — 去 AI 服务商官网免费/付费申请（最低几块钱就能用很久）
2. **本机运行这个项目** — 它充当"中间人"，帮你把消息安全地转发给 AI 并接收回复

**为什么要中间人（后端）？** 因为浏览器出于安全原因，不允许网页直接向第三方 API 发送请求（称为跨域限制）。这个 Python 后端就负责绕过这个限制，同时也做了安全防护（防止有人拿你的服务去攻击别人内网）。

**数据存在哪？** 所有对话记录、模型配置、主题偏好都存在你**自己浏览器的 localStorage** 里——不上传任何服务器，换浏览器或清缓存会丢失。

---

## ✨ 功能特点

### 核心功能
- **多模型支持** — 内置 DeepSeek、通义千问、硅基流动、智谱 GLM、Kimi、百川、零一万物、MiniMax 等 8 家国内外主流服务商，下拉选择即可自动填入接口地址和模型名；也支持手动填写任意兼容 OpenAI 格式的接口
- **流式输出** — AI 回复像打字一样逐字显示，不用等完整结果，体验和 ChatGPT 网页版一致
- **上下文记忆** — 可设置带多少条历史记录，让 AI 记住之前的对话内容，实现多轮连贯对话
- **🔄 重新生成** — 对 AI 回答不满意？点一下按钮重新问，自动去掉上次的回复
- **📥 / 📤 导入导出** — 单条对话可导出为 Markdown 文件（方便备份分享）；模型配置可导出为 JSON 文件，换电脑时一键导入
- **图片输入** — 可以上传图片发给 AI（前提是你用的模型支持识别图片，如 GPT-4V、通义千问 VL 等）

### 用户体验
- **🎨 主题色定制** — 蓝 / 紫 / 绿 / 橙四种预设，还有个取色器可以自己调任意颜色
- **🌙 深色模式** — 晚上不刺眼，一键切换
- **📱 / 🖥 双布局** — 紧凑模式像手机 App，宽屏模式像 ChatGPT 网页版（左侧对话列表 + 右侧聊天区 + 右侧设置面板）
- **📋 Markdown 渲染** — AI 回复里的代码会高亮着色，表格、列表、链接都能正确显示
- **💬 多对话管理** — 同时开多个对话，给每个加标签（工作、学习…），互不干扰

### 安全保护
- **内网防护** — 如果有人把接口地址填成 `http://192.168.1.1`，后端会拒绝请求，防止被利用来扫描你的内网
- **频率限制** — 每个 IP 每分钟最多 30 次请求，防止恶意刷接口
- **可选密码** — 设置 `AUTH_KEY` 后，客户端必须提供同样的密钥才能使用，适合部署在公网时加把锁
- **网页安全策略** — 前端限制了脚本和资源的来源，降低 XSS 攻击风险

---

## 🛠 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | 原生 HTML/CSS/JS（无框架依赖） | 一个 `index.html` 包含全部界面和逻辑 |
| **后端** | Python 3 + Flask + Flask-CORS | Flask 是轻量 Web 框架，Flask-CORS 处理跨域 |
| **生产服务器** | Waitress | 比 Flask 自带服务器更稳定的纯 Python 方案 |
| **数据存储** | 浏览器 localStorage | 所有数据存本地浏览器，不经过服务器 |
| **代码高亮** | highlight.js（CDN 加载） | AI 返回的代码块自动着色 |

---

## 📦 安装与配置

### 前置要求

- **Python 3.8 或更高版本**（[python.org 下载](https://www.python.org/downloads/)）
  - 安装时 **务必勾选 "Add Python to PATH"**（把 Python 加到系统路径），否则终端里找不到 `python` 命令
- 安装完成后打开终端（Win+R 输入 `powershell`，Mac 打开"终端"），验证：
  ```bash
  python --version    # 应显示 Python 3.8.0 或更高
  pip --version       # pip 是 Python 自带的包管理器
  ```

### 1. 下载项目

**方式 A：Git 克隆（推荐，方便后续更新）**

```bash
git clone https://github.com/你的用户名/ai-chat-web.git
cd ai-chat-web
```

**方式 B：直接下载 ZIP**

点击仓库页面的绿色 "Code" 按钮 → "Download ZIP"，解压到任意文件夹，然后终端 `cd` 进入该文件夹。

> ⚠️ 确保 `index.html` 和 `ai.py` 在同一个文件夹里，程序依赖这个结构。

### 2. 安装依赖

项目依赖 4 个 Python 包，在项目目录下执行：

```bash
pip install flask flask-cors requests waitress
```

如果报错 `pip 不是内部或外部命令`，说明安装 Python 时没勾选"Add Python to PATH"，重新安装 Python 或手动添加。

> 💡 推荐使用虚拟环境（让依赖不污染系统全局）：
> ```bash
> python -m venv venv              # 创建虚拟环境（只需一次）
> venv\Scripts\activate            # Windows 激活
> source venv/bin/activate         # macOS / Linux 激活
> pip install flask flask-cors requests waitress
> ```
> 之后每次启动前先激活虚拟环境即可。

### 3. （可选）设置访问密码

如果你的服务暴露在公网上，建议设置一个认证密钥，防止陌生人随便用：

```bash
# Windows PowerShell
$env:AUTH_KEY="你的密码"

# macOS / Linux / Windows CMD
set AUTH_KEY=你的密码
```

不设置则不需要认证，任何人都能访问。客户端在设置页面的「偏好→服务器认证密钥」处填入相同的密码才能正常发送请求。

### 4. （可选）换端口

默认使用 **5030** 端口，如果被其他程序占用：

```bash
# Windows PowerShell
$env:PORT="8080"

# macOS / Linux
export PORT=8080
```

---

## 🚀 使用说明

### 启动服务

```bash
python ai.py
```

终端将显示：

```
PORT=5030 AUTH_KEY=未设置（无需认证）
启动地址: http://0.0.0.0:5030
```

在浏览器中打开 `http://127.0.0.1:5030` 即可使用。

### 快速上手

1. **配置模型** — 点击右上角 ⚙ → 「🔌 模型」页签，填写：
   - **配置名称**：随便起，比如 "DeepSeek Pro"
   - **API 密钥**：在服务商官网申请（见下表），形如 `sk-xxxxxxxx`
   - **接口地址**：可以从"服务商快捷选择"下拉框自动填入
   - **模型名称**：也可以下拉框自动填入，或点「📋 获取列表」拉取
   
   > 不懂这些是什么意思？**API 密钥**就像账号密码，证明你有权调用 AI；**接口地址**是 AI 服务的网址；**模型名称**告诉服务商你要用哪个模型（比如 `deepseek-v4-flash` 便宜快速，`deepseek-v4-pro` 更聪明）。

2. **新建对话** — 点击 + 按钮创建新对话
3. **开始聊天** — 在底部输入框输入消息，按 Enter 发送
4. **切换对话** — 点击左侧对话列表或在手机端点击 ☰ 打开抽屉菜单

### 获取 API 密钥

各服务商的 API 密钥获取地址：

| 服务商 | 获取地址 |
|--------|----------|
| DeepSeek | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) |
| 阿里百炼 | [dashscope.console.aliyun.com/apiKey](https://dashscope.console.aliyun.com/apiKey) |
| 硅基流动 | [cloud.siliconflow.cn/account/ak](https://cloud.siliconflow.cn/account/ak) |
| 智谱 GLM | [open.bigmodel.cn/usercenter/apikeys](https://open.bigmodel.cn/usercenter/apikeys) |
| 月之暗面 Kimi | [platform.moonshot.cn/console/api-keys](https://platform.moonshot.cn/console/api-keys) |
| 百川 Baichuan | [platform.baichuan-ai.com/console/apikey](https://platform.baichuan-ai.com/console/apikey) |
| 零一万物 Yi | [platform.lingyiwanwu.com/apikeys](https://platform.lingyiwanwu.com/apikeys) |
| MiniMax | [platform.minimaxi.com](https://platform.minimaxi.com/user-center/payment/token-plan) |

### 快捷键

| 按键 | 功能 |
|------|------|
| `Enter` | 发送消息 |
| `Shift + Enter` | 换行 |
| `Esc` | 关闭设置弹窗 / 关闭抽屉菜单 |

---

## � 服务器部署

### 方式一：直接运行（适合个人使用）

```bash
python ai.py
```

服务会在前台运行，`Ctrl+C` 停止。适合临时使用或开发调试。

### 方式二：Linux 服务器后台运行

**使用 nohup（简单）**

```bash
nohup python ai.py > server.log 2>&1 &
```

查看日志：`tail -f server.log`，停止：`kill $(lsof -t -i:5030)`

**使用 screen / tmux（推荐）**

```bash
screen -S ai-chat
python ai.py
# 按 Ctrl+A 再按 D 分离会话
# 重新连接：screen -r ai-chat
```

**使用 systemd（生产推荐）**

创建服务文件 `/etc/systemd/system/ai-chat.service`：

```ini
[Unit]
Description=AI Chat Web Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ai-chat-web
Environment="PORT=5030"
Environment="AUTH_KEY=your-secret-key"
ExecStart=/usr/bin/python3 /opt/ai-chat-web/ai.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ai-chat
sudo systemctl status ai-chat
```

### 方式三：Windows 服务器后台运行

**使用 pythonw（静默运行，无终端窗口）**

```powershell
pythonw ai.py
```

**使用 NSSM 注册为 Windows 服务（推荐）**

[NSSM](https://nssm.cc/) 可将任意程序注册为 Windows 服务：

```powershell
nssm install AI-Chat
# 在弹出的界面中设置：
# Path: C:\Python3\python.exe
# Arguments: ai.py
# Start directory: C:\path\to\ai-chat-web
nssm start AI-Chat
```

### 方式四：Nginx 反向代理（启用 HTTPS）

配合 Nginx 实现 HTTPS 访问、负载均衡、静态资源缓存：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5030;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式传输支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 120s;
        chunked_transfer_encoding on;
    }
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}
```

### 方式五：Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install flask flask-cors requests waitress
ENV PORT=5030
EXPOSE 5030
CMD ["python", "ai.py"]
```

```bash
docker build -t ai-chat .
docker run -d -p 5030:5030 --name ai-chat ai-chat
# 设置认证密钥
docker run -d -p 5030:5030 -e AUTH_KEY="secret" --name ai-chat ai-chat
```

---

## 🌐 网络访问说明

### 访问地址对照表

| 场景 | 访问地址 | 说明 |
|------|----------|------|
| 本机访问 | `http://127.0.0.1:5030` | 仅本机可用 |
| 局域网 (LAN) | `http://192.168.x.x:5030` | 同局域网内其他设备可访问 |
| 公网访问 | `http://your-public-ip:5030` | 需防火墙放行端口 |
| 直接打开 HTML | 双击 `index.html` | 仅适配 `file://` 协议，自动连接 `127.0.0.1:5030` |

### 局域网访问

1. 查看本机局域网 IP：
   - Windows：`ipconfig`，找到 `IPv4 地址`
   - Linux / macOS：`ip addr` 或 `ifconfig`
2. 在其他设备浏览器中输入 `http://<本机IP>:5030`

### 常见网络问题

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| **无法访问此网站** | 服务未启动或端口被占用 | 确认 `python ai.py` 正常运行；换端口 `$env:PORT="8080"` |
| **局域网无法访问** | 防火墙拦截 | Windows：允许 Python 通过防火墙；Linux：`sudo ufw allow 5030` |
| **ERR_CONNECTION_REFUSED** | 服务只监听 127.0.0.1 | 代码默认监听 `0.0.0.0`，正常应无此问题 |
| **请求失败 / 网络错误** | 后端未启动或端口不一致 | 确认后端在 `5030` 端口运行 |
| **file:// 协议跨域** | 直接打开 HTML 文件时的跨域限制 | 前端已自动处理：`file://` 下固定请求 `http://127.0.0.1:5030`，需同时启动后端 |
| **公网不安全** | HTTP 明文传输 | 建议使用 Nginx + SSL 或 Cloudflare Tunnel |
| **Nginx 502 Bad Gateway** | Nginx 无法连接后端 | 检查后端是否运行、端口是否一致、SELinux 是否拦截 |

### 内网穿透（无公网 IP 时的替代方案）

如果无公网 IP 或云服务器，可使用内网穿透工具将本地服务暴露到公网：

| 工具 | 简介 | 示例 |
|------|------|------|
| [frp](https://github.com/fatedier/frp) | 开源内网穿透，需自备公网服务器 | 功能强大，适合长期使用 |
| [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/) | 免费，将服务绑定到自定义域名 | `cloudflared tunnel --url http://localhost:5030` |
| [ngrok](https://ngrok.com/) | 开箱即用，免费版有限制 | `ngrok http 5030` |
| [serveo](https://serveo.net/) | 无需安装客户端 | `ssh -R 80:localhost:5030 serveo.net` |

---

## �📁 项目结构

```
ai-chat-web/
├── index.html          # 前端单页面应用（HTML + CSS + JS）
├── ai.py               # Flask 后端代理服务
├── requirements.txt    # Python 依赖列表
├── .gitignore          # Git 忽略规则
└── README.md           # 项目说明文档
```

### 前后端职责

**前端 (`index.html`)**
- 完整的聊天 UI（消息列表、输入框、对话侧边栏、设置面板）
- 数据持久化（对话记录、模型配置、主题偏好存储在 localStorage）
- Markdown 渲染与代码高亮
- SSE 流式数据接收与实时渲染

**后端 (`ai.py`)**
- 静态文件服务（托管 `index.html`）
- API 代理转发（`/ask_ai` 非流式、`/ask_ai_stream` 流式）
- 连接测试（`/test_connection`）
- 模型列表获取（`/list_models`，含预设备选方案）
- 安全防护（SSRF、速率限制、可选认证）

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 贡献流程

1. Fork 本项目
2. 创建特性分支：`git checkout -b feat/amazing-feature`
3. 提交你的更改：`git commit -m 'feat: 添加某个功能'`
4. 推送到分支：`git push origin feat/amazing-feature`
5. 提交 Pull Request

### 代码风格

- 前端使用原生 JavaScript，不引入第三方框架
- 后端遵循 PEP 8 规范
- CSS 使用 CSS 自定义属性（变量）管理主题

### 提交信息规范

推荐使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

- `feat:` 新功能
- `fix:` 修复 Bug
- `refactor:` 代码重构
- `docs:` 文档更新
- `style:` 样式调整

---

## 📄 许可证

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 开源。

---

## ⚠️ 注意事项

- **API 密钥安全**：API 密钥存储在浏览器的 localStorage 中，请勿在不受信任的设备上使用。后端不会持久化存储密钥。
- **生产部署**：建议配合反向代理（如 Nginx）使用，并启用 HTTPS。
- **图片限制**：图片以 Base64 格式存储在 localStorage 中，大量图片可能超出浏览器存储配额（通常 5-10MB）。
- **网络限制**：后端默认禁止访问内网地址，如需调整请修改 `ai.py` 中的 `PRIVATE_IP_RANGES`。

# 安全策略

## 支持的版本

| 版本  | 是否支持           |
| ----- | ------------------ |
| 1.0.x | :white_check_mark: |

## 报告漏洞

如果你发现安全漏洞，请**不要**公开提 Issue。

请通过 GitHub 安全公告私下报告：

1. 前往 [Security 页签](https://github.com/kldsjfas/ai-chat-web/security)
2. 点击 "Report a vulnerability"
3. 详细描述问题

也可以发送邮件给维护者。

## 安全特性

- **内网防护**：后端禁止向私有 / 内网 IP 段发送请求，防止 SSRF 攻击
- **频率限制**：每个 IP 每分钟最多 30 次请求
- **可选认证**：设置 `AUTH_KEY` 环境变量后，客户端需提供相同密钥
- **内容安全策略 (CSP)**：前端限制脚本和样式来源
- **密钥隔离**：API 密钥仅存储在浏览器 localStorage 中，后端不持久化

# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public issue.

Instead, report it privately via GitHub Security Advisories:

1. Go to the [Security tab](https://github.com/kldsjfas/ai-chat-web/security)
2. Click "Report a vulnerability"
3. Describe the issue in detail

You can also send an email to the maintainer.

## Security Features

- **SSRF Protection**: Backend blocks requests to private/internal IP ranges
- **Rate Limiting**: Max 30 requests per minute per IP
- **Optional Authentication**: Set `AUTH_KEY` environment variable to require a shared secret
- **Content Security Policy**: Frontend restricts script and style sources
- **API Key Isolation**: API keys are stored only in the browser's localStorage, never on the server

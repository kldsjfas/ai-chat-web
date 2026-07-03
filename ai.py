from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory
from flask_cors import CORS
import requests
import json
import socket
import ipaddress
import re
import os
import time
import logging
from threading import Lock
from urllib.parse import urlparse

try:
    from waitress import serve
except ImportError:
    serve = None

app = Flask(__name__, static_folder=None)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
CORS(app)

PORT = int(os.environ.get('PORT', '5030'))
AUTH_KEY = os.environ.get('AUTH_KEY', '')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PRIVATE_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'), ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'), ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'), ipaddress.ip_network('0.0.0.0/8'),
    ipaddress.ip_network('100.64.0.0/10'), ipaddress.ip_network('224.0.0.0/4'),
    ipaddress.ip_network('240.0.0.0/4'),
]

rate_limit_store = {}
rate_limit_lock = Lock()


def is_private_host(hostname):
    hostname = hostname.strip().lower()
    if hostname in ('localhost', '0.0.0.0', '[::]', '127.0.0.1', '::1'):
        return True
    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            addr = ipaddress.ip_address(socket.gethostbyname(hostname))
        except (socket.gaierror, TypeError):
            return True
    return any(addr in net for net in PRIVATE_IP_RANGES)


def safe_post(url, headers, json_data, **kwargs):
    url = url.strip()
    if not re.match(r'^https?://', url):
        raise ValueError("接口地址必须以 http:// 或 https:// 开头")
    hostname = urlparse(url).hostname
    if not hostname or is_private_host(hostname):
        raise ValueError("禁止访问内网地址")
    kwargs.setdefault('timeout', 60)
    kwargs.setdefault('allow_redirects', False)
    return requests.post(url, headers=headers, json=json_data, **kwargs)


def check_rate_limit(ip):
    now = time.time()
    with rate_limit_lock:
        entry = rate_limit_store.get(ip)
        if entry:
            count, window_start = entry
            if now - window_start > 60:
                rate_limit_store[ip] = (1, now)
                return True
            if count >= 30:
                return False
            rate_limit_store[ip] = (count + 1, window_start)
        else:
            rate_limit_store[ip] = (1, now)
        return True


def require_auth(data):
    if not AUTH_KEY:
        return None
    auth = (data or {}).get('server_key', '')
    if auth != AUTH_KEY:
        return "服务器认证密钥不正确"
    return None


def validate_payload(data, max_messages=50):
    if not isinstance(data, dict):
        return "请求体必须是 JSON 对象", 400
    msgs = data.get('messages')
    if msgs is not None:
        if not isinstance(msgs, list):
            return "messages 必须是数组", 400
        if len(msgs) > max_messages:
            return f"messages 不能超过 {max_messages} 条", 400
        for m in msgs:
            if not isinstance(m, dict):
                return "每条消息必须是对象", 400
            role = m.get('role', '')
            if role not in ('user', 'assistant', 'system', 'ai'):
                return f"不支持的消息角色: {role}", 400
            if not isinstance(m.get('content', ''), str):
                return "消息内容必须是字符串", 400
    prompt = data.get('prompt', '')
    if prompt and len(prompt) > 100000:
        return "prompt 不能超过 100000 字符", 400
    system = data.get('system_prompt', '')
    if system and len(system) > 100000:
        return "系统提示词不能超过 100000 字符", 400
    images = data.get('images')
    if images is not None:
        if not isinstance(images, list) or len(images) > 10:
            return "images 必须是数组且不超过 10 张", 400
        for img in images:
            if not isinstance(img, str) or not img.startswith('data:image/'):
                return "图片必须是 data:image 格式", 400
    temp = data.get('temperature')
    if temp is not None and not (isinstance(temp, (int, float)) and 0 <= temp <= 2):
        return "temperature 必须在 0-2 之间", 400
    max_tokens = data.get('max_tokens')
    if max_tokens is not None and not (isinstance(max_tokens, int) and 1 <= max_tokens <= 65536):
        return "max_tokens 必须在 1-65536 之间", 400
    return None, None


def build_api_messages(data):
    """把前端传来的 prompt / messages / images 组装成 OpenAI 格式的消息列表"""
    api_messages = []
    system_prompt = data.get('system_prompt', '')
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    for m in data.get('messages') or []:
        role = m["role"]
        if role == 'ai':
            role = 'assistant'
        api_messages.append({"role": role, "content": m["content"]})
    prompt = data.get('prompt', '')
    images = data.get('images') or []
    if images:
        content = [{"type": "image_url", "image_url": {"url": img}} for img in images]
        if prompt:
            content.insert(0, {"type": "text", "text": prompt})
        api_messages.append({"role": "user", "content": content})
    elif prompt:
        api_messages.append({"role": "user", "content": prompt})
    return api_messages


def build_upstream_payload(data, stream=False):
    payload = {"model": data.get('model'), "messages": build_api_messages(data)}
    if data.get('temperature') is not None:
        payload["temperature"] = data['temperature']
    if data.get('max_tokens') is not None:
        payload["max_tokens"] = data['max_tokens']
    if stream:
        payload["stream"] = True
    return payload


@app.route('/')
def index():
    resp = send_from_directory(os.path.dirname(__file__), 'index.html')
    resp.headers['Content-Security-Policy'] = (
        "default-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; "
        "img-src 'self' data: blob: https:; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com"
    )
    return resp


@app.route('/ask_ai', methods=['POST'])
def ask_ai():
    ip = request.remote_addr or '0.0.0.0'
    if not check_rate_limit(ip):
        logger.warning(f"rate_limit_hit ip={ip}")
        return jsonify({"error": "请求过于频繁，请稍后重试"}), 429
    if not request.is_json:
        return jsonify({"error": "请求格式错误，需要 JSON"}), 415
    data = request.json
    if auth_err := require_auth(data):
        return jsonify({"error": auth_err}), 403
    err, code = validate_payload(data)
    if err:
        return jsonify({"error": err}), code

    api_key = data.get('api_key')
    api_url = data.get('api_url')
    model_name = data.get('model')

    if not all([api_key, api_url, model_name]):
        return jsonify({"error": "配置参数不完整"}), 400
    if not data.get('prompt') and not data.get('messages') and not data.get('images'):
        return jsonify({"error": "没有输入内容"}), 400

    logger.info(f"ask_ai ip={ip} model={model_name} len={len(data.get('prompt') or '')}")
    try:
        response = safe_post(api_url, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }, json_data=build_upstream_payload(data))
        response.raise_for_status()
        result = response.json()
        logger.info(f"ask_ai_success model={model_name} status={response.status_code}")
        message = result['choices'][0]['message']
        reply = {"reply": message.get('content') or ''}
        if message.get('reasoning_content'):
            reply["reasoning"] = message['reasoning_content']
        return jsonify(reply)
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        logger.exception(f"ask_ai_error model={model_name} url={api_url}")
        return jsonify({"error": "调用 AI 接口失败，请检查配置后重试"}), 500


@app.route('/ask_ai_stream', methods=['POST'])
def ask_ai_stream():
    ip = request.remote_addr or '0.0.0.0'
    if not check_rate_limit(ip):
        return jsonify({"error": "请求过于频繁"}), 429
    if not request.is_json:
        return jsonify({"error": "请求格式错误"}), 415
    data = request.json
    if auth_err := require_auth(data):
        return jsonify({"error": auth_err}), 403
    err, code = validate_payload(data)
    if err:
        return jsonify({"error": err}), code

    api_key = data.get('api_key')
    api_url = data.get('api_url')
    model_name = data.get('model')

    if not all([api_key, api_url, model_name]):
        return jsonify({"error": "配置参数不完整"}), 400
    if not data.get('prompt') and not data.get('messages') and not data.get('images'):
        return jsonify({"error": "没有输入内容"}), 400

    logger.info(f"ask_ai_stream ip={ip} model={model_name}")

    def generate():
        hostname = urlparse(api_url).hostname
        if not hostname or is_private_host(hostname):
            yield f"data: {json.dumps({'error': '禁止访问内网地址'})}\n\n"
            return
        try:
            resp = safe_post(api_url, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }, json_data=build_upstream_payload(data, stream=True),
                stream=True, timeout=120)
            if resp.status_code != 200:
                detail = resp.text[:200]
                logger.warning(f"stream_upstream_error status={resp.status_code} detail={detail}")
                yield f"data: {json.dumps({'error': f'接口返回 HTTP {resp.status_code}: {detail}'})}\n\n"
                return
            accumulated = ""
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                chunk_str = line[6:]
                if chunk_str.strip() == "[DONE]":
                    yield f"data: {json.dumps({'done': True, 'full': accumulated})}\n\n"
                    break
                try:
                    chunk = json.loads(chunk_str)
                    delta = chunk['choices'][0].get('delta', {})
                    reasoning = delta.get('reasoning_content', '')
                    if reasoning:
                        yield f"data: {json.dumps({'reasoning': reasoning})}\n\n"
                    content = delta.get('content', '')
                    if content:
                        accumulated += content
                        yield f"data: {json.dumps({'content': content})}\n\n"
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
        except Exception:
            logger.exception("stream_error")
            yield f"data: {json.dumps({'error': '流式调用失败'})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/test_connection', methods=['POST'])
def test_connection():
    if not request.is_json:
        return jsonify({"ok": False, "error": "请求格式错误"}), 415
    data = request.json
    if auth_err := require_auth(data):
        return jsonify({"ok": False, "error": auth_err}), 403
    api_key = data.get('api_key')
    api_url = data.get('api_url')
    model = data.get('model', 'deepseek-v4-flash')
    if not api_key or not api_url:
        return jsonify({"ok": False, "error": "缺少 API 密钥或接口地址"}), 400
    try:
        resp = safe_post(api_url, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }, json_data={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}, timeout=15)
        if resp.status_code == 200:
            logger.info(f"test_connection_success model={model} url={api_url}")
            return jsonify({"ok": True, "msg": "连接成功！"})
        detail = resp.text[:200]
        logger.warning(f"test_connection_failed status={resp.status_code} model={model} url={api_url} detail={detail}")
        return jsonify({"ok": False, "error": f"HTTP {resp.status_code}: {detail}"}), 200
    except requests.exceptions.Timeout:
        logger.warning(f"test_connection_timeout model={model} url={api_url}")
        return jsonify({"ok": False, "error": "请求超时"}), 200
    except requests.exceptions.ConnectionError:
        logger.warning(f"test_connection_connection_error model={model} url={api_url}")
        return jsonify({"ok": False, "error": "无法连接"}), 200
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 200
    except Exception as e:
        logger.exception(f"test_connection_exception model={model} url={api_url}")
        return jsonify({"ok": False, "error": "连接失败"}), 200


@app.route('/list_models', methods=['POST'])
def list_models():
    if not request.is_json:
        return jsonify({"ok": False, "error": "格式错误"}), 415
    data = request.json
    if auth_err := require_auth(data):
        return jsonify({"ok": False, "error": auth_err}), 403
    api_key = data.get('api_key')
    api_url = data.get('api_url')
    if not api_key or not api_url:
        return jsonify({"ok": False, "error": "缺少参数"}), 400

    stripped = api_url.strip().rstrip('/')
    base = re.sub(r'/chat/completions$', '', stripped)
    base = re.sub(r'/completions$', '', base)

    urls_to_try = [
        base + '/models',
        re.sub(r'/v1$', '', base) + '/models',
        base + '/v1/models',
    ]
    seen = set()
    urls_to_try = [u for u in urls_to_try if not (u in seen or seen.add(u))]

    KNOWN_MODELS = {
        'deepseek.com': [
            {"id": "deepseek-v4-pro", "owned_by": "deepseek"},
            {"id": "deepseek-v4-flash", "owned_by": "deepseek"},
            {"id": "deepseek-chat", "owned_by": "deepseek"},
            {"id": "deepseek-reasoner", "owned_by": "deepseek"},
            {"id": "deepseek-coder", "owned_by": "deepseek"},
            {"id": "deepseek-math", "owned_by": "deepseek"},
        ],
        'minimax': [
            {"id": "MiniMax-M2.7", "owned_by": "minimax"},
            {"id": "MiniMax-M2.7-highspeed", "owned_by": "minimax"},
            {"id": "MiniMax-M2.5", "owned_by": "minimax"},
            {"id": "MiniMax-M2.5-highspeed", "owned_by": "minimax"},
            {"id": "MiniMax-M2.1", "owned_by": "minimax"},
            {"id": "MiniMax-M2.1-highspeed", "owned_by": "minimax"},
            {"id": "MiniMax-M2", "owned_by": "minimax"},
        ],
        'bigmodel.cn': [
            {"id": "GLM-5.1", "owned_by": "zhipu"},
            {"id": "GLM-5", "owned_by": "zhipu"},
            {"id": "GLM-4.7", "owned_by": "zhipu"},
            {"id": "GLM-4.7-Flash", "owned_by": "zhipu"},
            {"id": "glm-4-flash", "owned_by": "zhipu"},
        ],
        'moonshot': [
            {"id": "kimi-k2.6", "owned_by": "moonshot"},
            {"id": "kimi-k2.5", "owned_by": "moonshot"},
            {"id": "kimi-k2", "owned_by": "moonshot"},
            {"id": "moonshot-v1-8k", "owned_by": "moonshot"},
        ],
        'aliyuncs.com': [
            {"id": "qwen3.6-max-preview", "owned_by": "alibaba"},
            {"id": "qwen3.6-plus", "owned_by": "alibaba"},
            {"id": "qwen3.6-flash", "owned_by": "alibaba"},
            {"id": "qwen3.5-plus", "owned_by": "alibaba"},
            {"id": "qwen-plus", "owned_by": "alibaba"},
        ],
        'siliconflow': [
            {"id": "deepseek-ai/DeepSeek-V3.1", "owned_by": "siliconflow"},
            {"id": "deepseek-ai/DeepSeek-R1", "owned_by": "siliconflow"},
            {"id": "Qwen/Qwen3.5-7B", "owned_by": "siliconflow"},
            {"id": "Pro/kimi-k2.6", "owned_by": "siliconflow"},
            {"id": "Pro/GLM-5.1", "owned_by": "siliconflow"},
        ],
        'baichuan': [
            {"id": "Baichuan4-Turbo", "owned_by": "baichuan"},
            {"id": "Baichuan4-Air", "owned_by": "baichuan"},
            {"id": "Baichuan-M1-preview", "owned_by": "baichuan"},
        ],
        'lingyiwanwu': [
            {"id": "yi-lightning", "owned_by": "lingyiwanwu"},
            {"id": "yi-large", "owned_by": "lingyiwanwu"},
        ],
    }

    for try_url in urls_to_try:
        hostname = urlparse(try_url).hostname
        if not hostname or is_private_host(hostname):
            continue
        try:
            resp = requests.get(try_url, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }, timeout=15, allow_redirects=False)
            if resp.status_code == 200:
                result = resp.json()
                items = result.get('data', result.get('models', []))
                models = []
                for item in items:
                    mid = item.get('id', '')
                    if mid and not mid.startswith('ft:'):
                        models.append({"id": mid, "owned_by": item.get('owned_by', '')})
                if models:
                    return jsonify({"ok": True, "models": models})
        except Exception:
            continue

    host = urlparse(stripped).hostname or ''
    for key, models in KNOWN_MODELS.items():
        if key in host:
            return jsonify({"ok": True, "models": models, "source": "predefined"})

    return jsonify({"ok": False, "error": "无法获取模型列表，请检查 API 密钥和地址"}), 200


if __name__ == '__main__':
    print(f"PORT={PORT} AUTH_KEY={'已设置' if AUTH_KEY else '未设置（无需认证）'}")
    print(f"启动地址: http://0.0.0.0:{PORT}")

    if serve is not None:
        logger.info(f"使用 waitress 启动，端口 {PORT}")
        serve(app, host='0.0.0.0', port=PORT, threads=8)
    else:
        logger.warning("waitress 未安装，使用 Flask 开发服务器")
        app.run(host='0.0.0.0', port=PORT, debug=False)

"""v17 Unified LLM Provider — 50+ models across all major providers"""

import json, logging, os
from typing import Optional

logger = logging.getLogger(__name__)

# 2026年5月最新模型 — 基于GPT-5.5/Claude Opus 4.7/DeepSeek V4/GLM-5.1/Qwen3.5等
MODELS = {
    # ── OpenAI (2026.4-5月最新) ──
    "gpt-5.5": {"provider":"openai","base":"https://api.openai.com/v1","desc":"GPT-5.5 最新旗舰 2026.4"},
    "gpt-5.5-instant": {"provider":"openai","base":"https://api.openai.com/v1","desc":"GPT-5.5 Instant 默认模型"},
    "gpt-4o": {"provider":"openai","base":"https://api.openai.com/v1","desc":"GPT-4o 全能旗舰"},
    "gpt-4o-mini": {"provider":"openai","base":"https://api.openai.com/v1","desc":"GPT-4o Mini 高性价比"},
    "o3": {"provider":"openai","base":"https://api.openai.com/v1","desc":"o3 深度推理"},
    # ── Anthropic (2026.4月最新) ──
    "claude-opus-4-7": {"provider":"anthropic","desc":"Claude Opus 4.7 最强 Q1收入第一"},
    "claude-sonnet-4-6": {"provider":"anthropic","desc":"Claude Sonnet 4.6 推荐"},
    "claude-haiku-4-5": {"provider":"anthropic","desc":"Claude Haiku 4.5 快速"},
    # ── Google (2026年最新) ──
    "gemini-3-deep-think": {"provider":"google","desc":"Gemini 3 Deep Think 推理"},
    "gemini-3.1-flash": {"provider":"google","desc":"Gemini 3.1 Flash 快速"},
    "gemini-3-pro": {"provider":"google","desc":"Gemini 3 Pro 1M上下文"},
    # ── DeepSeek (2026.4月 V4发布) ──
    "deepseek-v4": {"provider":"openai","base":"https://api.deepseek.com/v1","desc":"DeepSeek V4 1M上下文"},
    "deepseek-v4-flash": {"provider":"openai","base":"https://api.deepseek.com/v1","desc":"DeepSeek V4 Flash 极速"},
    "deepseek-r1": {"provider":"openai","base":"https://api.deepseek.com/v1","desc":"DeepSeek R1 推理"},
    # ── Alibaba 通义 (2026.1-2月最新) ──
    "qwen3.5-plus": {"provider":"openai","base":"https://dashscope.aliyuncs.com/compatible-mode/v1","desc":"Qwen3.5 Plus 397B/170B激活"},
    "qwen3-max-thinking": {"provider":"openai","base":"https://dashscope.aliyuncs.com/compatible-mode/v1","desc":"Qwen3 Max Thinking 万亿参数"},
    "qwen-plus": {"provider":"openai","base":"https://dashscope.aliyuncs.com/compatible-mode/v1","desc":"通义千问Plus"},
    # ── Zhipu 智谱 (2026.4-5月最新) ──
    "glm-5.1": {"provider":"openai","base":"https://open.bigmodel.cn/api/paas/v4","desc":"GLM-5.1 编程超Opus4.6 8h长程"},
    "glm-5": {"provider":"openai","base":"https://open.bigmodel.cn/api/paas/v4","desc":"GLM-5 744B/256Expert"},
    "glm-4-plus": {"provider":"openai","base":"https://open.bigmodel.cn/api/paas/v4","desc":"GLM-4 Plus"},
    "glm-4-flash": {"provider":"openai","base":"https://open.bigmodel.cn/api/paas/v4","desc":"GLM-4 Flash 免费"},
    # ── ByteDance 豆包 ──
    "doubao-pro-32k": {"provider":"openai","base":"https://ark.cn-beijing.volces.com/api/v3","desc":"豆包Pro 32K"},
    "doubao-lite": {"provider":"openai","base":"https://ark.cn-beijing.volces.com/api/v3","desc":"豆包Lite 免费"},
    # ── Moonshot Kimi ──
    "kimi-k2.6": {"provider":"openai","base":"https://api.moonshot.cn/v1","desc":"Kimi K2.6 多模态Agent"},
    "moonshot-v1-128k": {"provider":"openai","base":"https://api.moonshot.cn/v1","desc":"Kimi 128K"},
    # ── MiniMax ──
    "minimax-m2.5": {"provider":"openai","base":"https://api.minimax.chat/v1","desc":"MiniMax M2.5 10B超Opus4.6"},
    # ── StepFun 阶跃星辰 ──
    "step-3.5-flash": {"provider":"openai","base":"https://api.stepfun.com/v1","desc":"Step 3.5 Flash 1960B"},
    # ── 科大讯飞 ──
    "spark-x2": {"provider":"openai","base":"https://spark-api-open.xf-yun.com/v1","desc":"讯飞星火X2 国产算力"},
    # ── Baidu 百度 ──
    "ernie-4.0": {"provider":"openai","base":"https://qianfan.baidubce.com/v2","desc":"文心一言4.0"},
    # ── Tencent 腾讯 ──
    "hunyuan-pro": {"provider":"openai","base":"https://api.hunyuan.cloud.tencent.com/v1","desc":"腾讯混元Pro"},
    # ── 零一万物 ──
    "yi-large": {"provider":"openai","base":"https://api.lingyiwanwu.com/v1","desc":"Yi-Large"},
    # ── xAI ──
    "grok-3": {"provider":"openai","base":"https://api.x.ai/v1","desc":"xAI Grok-3"},
    # ── Mistral ──
    "mistral-large": {"provider":"openai","base":"https://api.mistral.ai/v1","desc":"Mistral Large"},
    # ── 聚合/代理平台 ──
    "siliconflow-deepseek": {"provider":"openai","base":"https://api.siliconflow.cn/v1","desc":"SiliconFlow DeepSeek V4"},
    "groq-llama": {"provider":"openai","base":"https://api.groq.com/openai/v1","desc":"Groq Llama 超快推理"},
    "together-qwen": {"provider":"openai","base":"https://api.together.xyz/v1","desc":"Together Qwen3.5"},
    # ── Local ──
    "ollama": {"provider":"ollama","desc":"本地Ollama"},
}

def call_llm(prompt: str, model: str = "gpt-4o-mini", api_key: str = "", max_tokens: int = 500, base_url: str = "", verify_ssl: bool = True, proxy: str = "", timeout: int = 60) -> str:
    """统一LLM调用入口 — 支持SSL/代理/超时配置"""
    if not api_key and model != "ollama":
        return "[错误] 请提供API密钥"

    config = dict(MODELS.get(model, MODELS.get("gpt-4o-mini", {})))
    if base_url:
        config["base"] = base_url
    provider = config.get("provider", "openai")

    try:
        if provider == "openai":
            return _openai(prompt, model, api_key, config.get("base"), max_tokens, verify_ssl, proxy, timeout)
        elif provider == "anthropic":
            return _anthropic(prompt, model, api_key, max_tokens, verify_ssl, proxy, timeout)
        elif provider == "google":
            return _google(prompt, model, api_key, max_tokens)
        elif provider == "ollama":
            return _ollama(prompt, max_tokens)
        return f"[错误] 不支持的provider: {provider}"
    except Exception as e:
        msg = str(e)[:200]
        logger.error(f"LLM call failed ({model}): {msg}")
        if "401" in msg or "Unauthorized" in msg:
            return "[错误] API密钥无效或已过期"
        if "429" in msg:
            return "[错误] API调用频率超限，请稍后重试"
        if "timeout" in msg.lower() or "timed out" in msg.lower():
            return "[错误] 模型响应超时，请检查网络或使用代理"
        if "SSL" in msg or "certificate" in msg or "ssl" in msg.lower() or "unreachable" in msg.lower():
            return f"[错误] SSL/网络连接失败。如果你在本地部署(尤其国内)，请：\n1. 确保网络能访问API\n2. 在config.py设置 VERIFY_SSL=False\n3. 或设置环境变量 HTTP_PROXY/HTTPS_PROXY\n4. 原始错误: {msg[:150]}"
        return f"[错误] 调用失败: {msg}"

def _openai(prompt, model, key, base, max_tok, verify_ssl=True, proxy="", timeout=60):
    from openai import OpenAI
    import httpx
    http_kw = {"timeout": httpx.Timeout(timeout, connect=15.0)}
    if not verify_ssl:
        http_kw["verify"] = False
    if proxy:
        http_kw["proxy"] = proxy
    client = OpenAI(api_key=key, base_url=base, http_client=httpx.Client(**http_kw))
    resp = client.chat.completions.create(
        model=model, messages=[{"role":"user","content":prompt}],
        max_tokens=max_tok, temperature=0.3)
    return resp.choices[0].message.content or "" if resp.choices else ""

def _anthropic(prompt, model, key, max_tok, verify_ssl=True, proxy="", timeout=60):
    import httpx
    http_kw = {"timeout": httpx.Timeout(timeout, connect=15.0)}
    if not verify_ssl:
        http_kw["verify"] = False
    if proxy:
        http_kw["proxy"] = proxy
    import anthropic
    client = anthropic.Anthropic(api_key=key, http_client=httpx.Client(**http_kw))
    resp = client.messages.create(
        model=model, max_tokens=max_tok,
        messages=[{"role":"user","content":prompt}])
    return resp.content[0].text

def _google(prompt, model, key, max_tok):
    import google.generativeai as genai
    genai.configure(api_key=key)
    mdl = genai.GenerativeModel(model)
    resp = mdl.generate_content(prompt, generation_config={"max_output_tokens":max_tok,"temperature":0.3})
    return resp.text or ""

def _ollama(prompt, max_tok):
    import ollama
    resp = ollama.chat(model="qwen2.5:7b", messages=[{"role":"user","content":prompt}],
                       options={"temperature":0.3,"num_predict":max_tok})
    return resp["message"]["content"]

def list_models() -> list:
    return [{"id":k,"provider":v.get("provider","?"),"desc":v.get("desc","")} for k,v in MODELS.items()]

def validate_key(api_key: str, model: str = "gpt-4o-mini", base_url: str = "", verify_ssl: bool = True, proxy: str = "") -> dict:
    if not api_key:
        return {"valid":False,"error":"请提供API密钥"}
    try:
        result = call_llm("回复OK", model, api_key, 10, base_url, verify_ssl, proxy, 30)
        ok = "OK" in result
        return {"valid":ok,"test_response":result[:80],"model":model}
    except Exception as e:
        return {"valid":False,"error":str(e)[:120]}

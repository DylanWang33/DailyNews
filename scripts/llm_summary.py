# LLM 集成模块：支持 Anthropic 原生 API 和 OpenClaw/OpenAI 兼容 Gateway
# 优先级：anthropic_api_key → openclaw_base_url（OpenAI 兼容）→ 返回 None（回退到传统方法）

import os
import re
import sys
import json

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

try:
    import requests
except ImportError:
    requests = None

_DEFAULT_TIMEOUT = 60
_MAX_TEXT = 12000
_BATCH_SIZE = 15


def _load_dotenv():
    """加载 .env 文件中的环境变量（仅补充，不覆盖已有环境变量）。"""
    env_path = os.path.join(_REPO, ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


_load_dotenv()  # 模块导入时自动加载


def _get_config():
    try:
        import yaml
        path = os.path.join(_REPO, "config.yaml")
        if not os.path.isfile(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


# ─── 底层调用（Anthropic 原生 / OpenAI 兼容二选一） ──────────────────────────

def _call_llm(cfg, prompt, max_tokens=500, temperature=0.1):
    """
    统一 LLM 调用入口。
    优先使用 Anthropic 原生 API（anthropic_api_key），
    其次使用 OpenClaw/OpenAI 兼容 Gateway（openclaw_base_url）。
    返回 str 或 None。
    """
    # 优先：Anthropic 原生 SDK
    api_key = (
        cfg.get("anthropic_api_key")
        or os.environ.get("ANTHROPIC_API_KEY")
        or ""
    ).strip()
    if api_key:
        return _call_anthropic(api_key, cfg, prompt, max_tokens, temperature)

    # 次选：OpenAI 兼容 Gateway（OpenClaw / Ollama / OpenAI 等）
    base_url = (cfg.get("openclaw_base_url") or "").strip().rstrip("/")
    if base_url and requests:
        return _call_openai_compat(base_url, cfg, prompt, max_tokens, temperature)

    return None


def _call_anthropic(api_key, cfg, prompt, max_tokens, temperature):
    """使用 Anthropic 原生 SDK 调用。"""
    try:
        import anthropic
        model = (cfg.get("anthropic_model") or "claude-haiku-4-5-20251001").strip()
        timeout = int(cfg.get("anthropic_timeout") or _DEFAULT_TIMEOUT)
        client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        content = msg.content[0].text if msg.content else ""
        return content.strip() if content.strip() else None
    except Exception as e:
        print(f"  [LLM] Anthropic 调用失败：{e}")
        return None


def _call_openai_compat(base_url, cfg, prompt, max_tokens, temperature):
    """使用 OpenAI 兼容 HTTP API 调用（OpenClaw/Ollama 等）。"""
    model = (cfg.get("openclaw_model") or "gpt-4o-mini").strip()
    timeout = int(cfg.get("openclaw_timeout") or _DEFAULT_TIMEOUT)
    api_key = (
        cfg.get("openclaw_api_key")
        or os.environ.get("GROQ_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    try:
        r = requests.post(f"{base_url}/v1/chat/completions", json=payload, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json()
        choice = (data.get("choices") or [None])[0]
        if not choice:
            return None
        content = (choice.get("message") or {}).get("content") or ""
        return content.strip() if content.strip() else None
    except Exception:
        return None


def _llm_available(cfg=None):
    """检查是否配置了任意 LLM 后端。"""
    if cfg is None:
        cfg = _get_config()
    has_anthropic = bool((cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY") or "").strip())
    has_openai = bool((cfg.get("openclaw_base_url") or "").strip())
    return has_anthropic or has_openai


# ─── 核心功能 1：批量相关性判断（替换单标签字符串匹配） ─────────────────────

def batch_is_relevant_llm(items, keyword):
    """
    批量判断文章列表是否与关键词语义相关。
    items: [{"title": ..., "summary": ...}, ...]
    返回 [bool, ...] 与 items 等长，或 None（LLM 不可用/失败时回退传统方法）。
    """
    if not items or not keyword:
        return None
    cfg = _get_config()
    if not _llm_available(cfg):
        return None

    results = []
    for batch_start in range(0, len(items), _BATCH_SIZE):
        batch = items[batch_start: batch_start + _BATCH_SIZE]
        lines = []
        for j, item in enumerate(batch):
            title = (item.get("title") or "")[:150]
            summary = (item.get("summary") or "")[:200]
            lines.append(f'{j + 1}. 标题：{title}  摘要：{summary}')
        prompt = (
            f"以下是 {len(batch)} 篇文章的标题和摘要。\n"
            f"请判断每篇文章是否与主题「{keyword}」相关（内容直接相关，而非仅偶然提及）。\n"
            f"仅以 JSON 对象格式回复，key 为序号字符串，value 为 true/false，例如：{{\"1\":true,\"2\":false}}\n\n"
            + "\n".join(lines)
        )
        response = _call_llm(cfg, prompt, max_tokens=150, temperature=0.0)
        if response is None:
            return None
        batch_results = _parse_bool_json(response, len(batch))
        if batch_results is None:
            return None
        results.extend(batch_results)

    return results


def _parse_bool_json(text, expected_count):
    """解析 LLM 返回的 {"1":true,"2":false} 格式，容忍 markdown 代码块。"""
    try:
        cleaned = re.sub(r"```[a-z]*\n?", "", text).strip().rstrip("`").strip()
        data = json.loads(cleaned)
        results = []
        for i in range(1, expected_count + 1):
            val = data.get(str(i))
            if val is None:
                val = data.get(i)
            results.append(bool(val))
        return results
    except Exception:
        try:
            results = []
            for i in range(1, expected_count + 1):
                found = bool(re.search(rf"{i}[：:\s]*(是|true)", text, re.IGNORECASE))
                results.append(found)
            return results
        except Exception:
            return None


# ─── 核心功能 2：多标签 AI 主题匹配（替换 entity 提取 + 字符串检测） ────────

def all_tags_match_llm(title, summary_rss, tags):
    """
    用 LLM 判断文章（仅凭标题+RSS摘要）是否同时涉及所有指定标签。
    返回 True/False 或 None（LLM 不可用/失败时回退传统方法）。
    """
    if not tags:
        return None
    cfg = _get_config()
    if not _llm_available(cfg):
        return None

    tag_str = "、".join(tags)
    prompt = (
        f"文章标题：{(title or '')[:200]}\n"
        f"摘要：{(summary_rss or '')[:400]}\n\n"
        f"请判断：该文章是否**同时**涉及以下所有主题：{tag_str}？\n"
        f"（每个主题须有实质性内容，不能仅偶然提及）\n"
        f"仅回答「是」或「否」。"
    )
    response = _call_llm(cfg, prompt, max_tokens=10, temperature=0.0)
    if response is None:
        return None
    return "是" in response and "否" not in response


# ─── 核心功能 3：生成式 AI 摘要 ──────────────────────────────────────────────

def summarize_with_llm(article_text, topic_hint="", max_sentences=3):
    """
    用 LLM 生成摘要，替代 sumy 抽取式摘要。
    返回摘要字符串，或 None（LLM 不可用/失败时由调用方回退到 sumy）。
    """
    if not article_text or not isinstance(article_text, str):
        return None
    cfg = _get_config()
    if not _llm_available(cfg):
        return None

    text = article_text[:_MAX_TEXT]
    prompt = f"请用{max_sentences}句话概括以下文章内容，使用中文。"
    if topic_hint:
        prompt += f" 若与「{topic_hint}」相关，请在摘要中突出。"
    prompt += f"\n\n文章：\n{text}"

    return _call_llm(cfg, prompt, max_tokens=500, temperature=0.3)


def summarize_professional(article_text, article_title="", keywords=""):
    """
    为「我的关注」生成专业学术化总结。

    要求：
    1. 客观、中性、学术化表达
    2. 保留核心论点、关键事实与逻辑结构
    3. 避免个人评价或推测
    4. 200-300 字
    5. 完整段落，逻辑清晰、语言简洁
    6. 准确概括背景与意义

    返回总结字符串，或 None（LLM 不可用/失败时）
    """
    if not article_text or not isinstance(article_text, str):
        return None
    cfg = _get_config()
    if not _llm_available(cfg):
        return None

    text = article_text[:_MAX_TEXT]

    prompt = """请对以下文章进行专业化摘要，总结其核心观点与主要信息。要求：

1. 使用客观、中性、学术化表达
2. 保留文章的核心论点、关键事实与逻辑结构
3. 避免加入个人评价或推测
4. 内容控制在200-300字之间
5. 用完整段落表达，逻辑清晰、语言简洁
6. 如文章涉及政策、人物或事件，应准确概括其背景与意义"""

    if article_title:
        prompt += f"\n\n文章标题：{article_title}"
    if keywords:
        prompt += f"\n关键词：{keywords}"

    prompt += f"\n\n文章内容：\n{text}"

    return _call_llm(cfg, prompt, max_tokens=800, temperature=0.2)


# ─── 可选功能 4：AI 批量翻译标题（替代 argostranslate） ─────────────────────

def translate_titles_with_llm(titles):
    """
    批量将英文标题翻译为中文。需在 config 中设置 openclaw_translate: true 才启用。
    返回 [str, ...] 或 None（回退到 argostranslate）。
    """
    if not titles:
        return None
    cfg = _get_config()
    if not cfg.get("openclaw_translate"):
        return None
    if not _llm_available(cfg):
        return None

    results = []
    for batch_start in range(0, len(titles), 20):
        batch = titles[batch_start: batch_start + 20]
        lines = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(batch))
        prompt = (
            f"请将以下 {len(batch)} 条新闻标题翻译为简洁准确的中文，保留专有名词。\n"
            f"仅以 JSON 格式回复：{{\"1\":\"译文\",\"2\":\"译文\"}}\n\n{lines}"
        )
        response = _call_llm(cfg, prompt, max_tokens=600, temperature=0.1)
        if response is None:
            return None
        try:
            cleaned = re.sub(r"```[a-z]*\n?", "", response).strip().rstrip("`").strip()
            data = json.loads(cleaned)
            for i in range(len(batch)):
                translated = data.get(str(i + 1)) or data.get(i + 1) or batch[i]
                results.append(str(translated).strip() or batch[i])
        except Exception:
            return None

    return results

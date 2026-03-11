# OpenClaw 接入分析与方案

**安全与权限分析**：接入后的安全隐患、OpenClaw 对项目的支持方式与权限、以及已知漏洞（含 ClawJacked/CVE-2026-25253）的说明见 **[openclaw-安全与权限分析.md](openclaw-安全与权限分析.md)**。

---

## OpenClaw 是什么

- **开源 AI 助手框架**（TypeScript，MIT），可在本机/自建环境运行，不依赖单一云厂商。
- **统一网关（Gateway）**：默认 `http://127.0.0.1:18789`，提供 **OpenAI 兼容** 的 HTTP API（如 `POST /v1/chat/completions`）。
- **多模型后端**：可接 OpenAI、Claude（含 Defapi 等中转）、Ollama 等，配置在一个地方即可切换。
- **本地优先**：用 Ollama 时数据不出本机；也可用已有 API Key 走云端模型。

因此：**接入 OpenClaw = 让你的 Python 脚本通过 HTTP 调用「本机或你已配置好的」大模型**，而不必在 DailyNews 里单独配各家的 key/endpoint。

---

## 与现有程序的关系

| 能力           | 现有程序                     | 接入 OpenClaw 后可增强的部分                    |
|----------------|-----------------------------|------------------------------------------------|
| 每日新闻       | RSS 标题+链接，不抓正文     | 不变；仍只存标题/链接。                         |
| 我的关注·单标签 | 标题 + RSS 摘要 契合度      | 不变；或可选用 LLM 做「是否相关」二次判断。     |
| 我的关注·多标签 | 抓正文 → entities + sumy 摘要 | **用 LLM 做生成式摘要**，替代/补充 sumy。       |
| 实体           | spacy 英文实体              | 可不变；或将来用 LLM 做关键词/主题抽取。        |

**核心可替换/增强点**：当前多标签条目用的是 **sumy（LSA 抽取式摘要）**；接入 OpenClaw 后，可改为（或与 sumy 并存）**调用 Gateway 的 chat/completions 做「用自然语言总结这篇文章」**，效果更接近「AI 总结」。

---

## 接入后相比现有的优势

1. **摘要质量更好**
   - 现有：sumy 是抽取原文句子、无理解，中英文混排或中文为主时效果一般。
   - OpenClaw：用 Claude/GPT/Ollama 做**生成式总结**，可指定「用中文、3 句话概括」「突出与美伊相关的内容」等，更贴你的「我的关注」场景。

2. **一处配置、多端复用**
   - 若你已在用 OpenClaw（例如 Telegram/其他机器人），同一 Gateway、同一套模型配置即可给 DailyNews 用，无需在 Python 里再配一遍各厂商 API。

3. **可选本地/隐私**
   - Gateway 后端选 Ollama 时，摘要完全在本机跑，不把新闻正文发到云端。

4. **扩展空间大**
   - 以后可让 LLM 做：多标签是否命中（如「这篇文章是否在讲美伊关系？」）、自动打标签、关键事实抽取等，而不只依赖 entities + 关键词匹配。

5. **成本可控**
   - 用 Ollama：免费、仅耗本机算力；用云端 API：由你在 OpenClaw 侧配置 key/额度，DailyNews 只调 Gateway，不碰 key。

---

## 如何接入（思路）

### 1. 前置条件

- 本机已安装并启动 OpenClaw，Gateway 可访问（如 `http://127.0.0.1:18789`）。
- 在 OpenClaw 中已配置至少一个模型（Ollama / OpenAI / Claude 等）。

### 2. 在 DailyNews 中的调用方式

OpenClaw Gateway 兼容 **OpenAI 的 chat/completions**，因此：

- 用 Python 的 `requests` 或 `openai` 库（`base_url` 指到 Gateway）即可。
- 例如：`POST http://127.0.0.1:18789/v1/chat/completions`，body 里 `model` 填你在 OpenClaw 里配置的模型 id，`messages` 里放 `[{"role":"user","content":"请用 3 句话总结以下文章，突出与石油/能源相关的内容：\n\n" + article_text}]`。

### 3. 与现有逻辑的衔接

- **可选配置**：在 `config.yaml` 中增加一项，例如：
  - `openclaw_base_url: "http://127.0.0.1:18789"`（不填或为空则不用 OpenClaw，保持当前 sumy 行为）。
- **摘要逻辑**：在「我的关注」多标签分支里，生成摘要时：
  - 若配置了 `openclaw_base_url` 且请求成功，则用 LLM 返回的文本作为该条目的 `summary`；
  - 否则回退到当前 `summarize(text, sentences=3)`（sumy）。
- **不改变**：每日新闻拉取、单标签契合度、entities 按日期存储、分号多标签匹配逻辑等，都可保持不变；只是「多标签条目的 summary 从哪来」多了一个 OpenClaw 来源。

### 4. 实现上建议

- 新建一个小模块（如 `scripts/llm_summary.py`）：  
  - 输入：`(article_text, prompt_suffix="")`  
  - 内部：读 `config` 的 `openclaw_base_url`、`openclaw_model`（可选），请求 Gateway 的 `/v1/chat/completions`，超时与错误时返回 `None`。  
- 在 `fetch_news.py` 里，多标签分支中「生成 item["summary"]」的那一步：  
  - 先调 `llm_summary.summarize_with_llm(text)`，若得到字符串则用；否则再用现有 `summarize(text, sentences=3)`。

这样：**不配 OpenClaw 时行为与现在完全一致；配了则多标签条目自动用 OpenClaw 做 AI 总结**。

---

## 小结

| 项目         | 说明 |
|--------------|------|
| **接入含义** | DailyNews 通过 HTTP 调用本机 OpenClaw Gateway（OpenAI 兼容 API），用大模型做「我的关注」多标签条目的摘要（或后续的关联判断等）。 |
| **主要优势** | 摘要质量更好、一处配置多端复用、可选本地/隐私、便于扩展更多 LLM 能力。 |
| **与现有关系** | 不替代现有 RSS/每日新闻/单标签逻辑，只增强「多标签条目的总结」来源；通过 config 开关与回退到 sumy 保持兼容。 |

---

## 本仓库已实现的全面集成（当前版本）

### 新增的三大 AI 能力

| 能力 | 函数 | 替代什么 | 回退方案 |
|------|------|----------|----------|
| **单标签 AI 相关性判断** | `batch_is_relevant_llm()` | 字符串契合度评分 | 传统关键词匹配 |
| **多标签 AI 主题匹配** | `all_tags_match_llm()` | spacy 实体提取 + 字符串检测 | 抓正文 → 实体提取 |
| **生成式 AI 摘要** | `summarize_with_llm()` | sumy LSA 抽取式摘要 | sumy 回退 |
| **可选：AI 批量翻译** | `translate_titles_with_llm()` | argostranslate 逐条翻译 | argostranslate 回退 |

### 关键改进亮点

- **单标签更智能**：LLM 能理解「crude oil」=「油价」、「armed conflict」=「战争」等语义关联，不再局限于字符串精确匹配
- **多标签更快速**：LLM 直接用标题+RSS摘要判断是否同时涉及所有主题，**无需先抓取正文**，跳过不相关文章更高效
- **摘要质量更好**：生成式总结可指定侧重点（如「请突出与美伊相关的内容」），支持纯中文输出
- **完全向后兼容**：未配置 `openclaw_base_url` 时，行为与之前完全一致

### 配置方式

在 `config.yaml` 中取消注释并填写：

```yaml
openclaw_base_url: "http://127.0.0.1:18789"   # OpenClaw Gateway 地址
openclaw_model: "gpt-4o-mini"                  # 模型 id
openclaw_timeout: 60
openclaw_api_key: ""                            # Gateway 无需 key 时留空
openclaw_translate: false                       # 设为 true 则 LLM 批量翻译英文标题
```

### 数据流（OpenClaw 配置后）

```
RSS 拉取（不变）
    ↓
每日新闻（不变，标题翻译可选 LLM 批量翻译）
    ↓
我的关注筛选（AI 驱动）：
  单标签：batch_is_relevant_llm() → 语义相关性判断（每批 15 篇）
  多标签：all_tags_match_llm() → 用标题+摘要直接 AI 判断（无需抓正文）
            ↓ 命中后才抓正文
          summarize_with_llm() → 生成式 AI 摘要
    ↓
git push（不变）
```

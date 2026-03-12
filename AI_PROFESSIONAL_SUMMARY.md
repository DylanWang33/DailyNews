# 「我的关注」AI 专业总结功能

## 功能概述

对「我的关注」中匹配关键词的文章自动生成 **专业学术化总结**，替代原始的简短摘要。

### 核心特性

✅ **智能生成** - 使用 LLM 基于关键词语境生成 200-300 字的学术化总结
✅ **客观表达** - 遵循学术规范，避免个人评价和推测
✅ **自动触发** - 无需额外配置，自动为匹配的文章生成总结
✅ **多标签支持** - 单标签和多标签（AND）都生成专业总结
✅ **优雅降级** - LLM 不可用时保留原摘要

---

## 工作流程

```
每日运行 run.sh
    ↓
fetch_news.py 抓取 RSS 源
    ↓
按关键词筛选（AI 或传统方法）
    ↓
为匹配文章生成专业总结
    ├─ 单标签：summarize_professional()
    └─ 多标签：先 AI 判断相关，再生成专业总结
    ↓
写入「我的关注/YYYY-MM-DD/关键词.md」
```

---

## 生成要求（遵循以下规范）

1. **客观、中立、学术化表达**
   - 第三人称叙述
   - 准确陈述事实
   - 避免感情化语言

2. **保留核心信息**
   - 文章的核心论点
   - 关键事实与数据
   - 逻辑结构

3. **避免个人评价**
   - 不加入作者的主观判断
   - 不包含推测性表述
   - 不带有倾向性词汇

4. **字数控制**
   - 200-300 字（可根据内容自动调整）
   - 完整段落表达
   - 逻辑清晰，语言简洁

5. **完整表达**
   - 能独立理解文章要点
   - 背景、事实、意义完整
   - 避免残缺或歧义

6. **准确概括**
   - 政策背景准确陈述
   - 人物身份清楚
   - 事件因果关系明确

---

## 配置要求

### 前置条件

需要 **OpenClaw LLM** 配置（详见 config.yaml）：

```yaml
openclaw_base_url: "https://api.groq.com/openai"
openclaw_model: "llama-3.3-70b-versatile"
openclaw_timeout: 60
```

### 可选启用

```yaml
# 启用 AI 批量翻译（可选，已默认启用）
openclaw_translate: true
```

---

## 使用示例

### 单标签关键词

**config.yaml：**
```yaml
keywords:
  - 油价
  - 经济政策
  - 技术突破
```

**工作流程：**
```
抓取所有 RSS 源
  ↓
用 AI 判断是否与「油价」相关
  ↓
匹配的文章 → summarize_professional() 生成 200-300 字总结
  ↓
写入「我的关注/2026-03-12/油价.md」
```

**生成示例：**
```
根据国际能源机构最新报告，全球石油需求增长放缓...
[完整的 200-300 字学术化总结]
```

### 多标签关键词（AND 逻辑）

**config.yaml：**
```yaml
keywords:
  - 美国;伊朗
  - 经济;政策
```

**工作流程：**
```
抓取所有 RSS 源
  ↓
用 AI 同时判断是否与「美国」和「伊朗」都相关
  ↓
同时匹配 → 抓取文章全文 → summarize_professional() 生成专业总结
  ↓
写入「我的关注/2026-03-12/美国;伊朗.md」
```

---

## 输出示例

### 之前（简短摘要）

```markdown
# 油价

**1. [油价创 6 个月新高](https://example.com/article/123)**

> 国际油价今日创下 6 个月来的新高，布伦特油价突破 100 美元/桶。

📰 彭博社 · 🕐 2026-03-12 14:30
```

### 现在（专业总结）

```markdown
# 油价

**1. [油价创 6 个月新高](https://example.com/article/123)**

根据国际能源机构（IEA）3月报告，全球布伦特原油价格...
[完整 200-300 字的学术化分析，包含背景、原因、影响、意义]

📰 彭博社 · 🕐 2026-03-12 14:30
```

---

## 故障排查

### 问题：总结没有生成

**检查清单：**
1. ✓ 是否启用了 OpenClaw（config.yaml）
2. ✓ 是否有网络连接
3. ✓ API key 是否有效（GROQ_API_KEY 环境变量）
4. ✓ 文章是否有摘要（无摘要不生成）

### 问题：总结内容不满意

**可能原因：**
- LLM 质量问题 → 尝试更新 model 版本
- 原摘要太短 → 优先抓取文章全文
- 关键词不清晰 → 优化 keywords 描述

### 问题：速度变慢

**原因：** 每篇文章都需要 LLM 调用（网络 I/O）

**优化：**
- 减少关键词数量
- 调整 LLM 超时时间
- 使用更快的模型

---

## 技术细节

### 调用链

```
run.sh
  → fetch_news.py: _fetch_all_daily_news()
    → _build_my_following_single_tag()
      → _generate_professional_summaries()  # 新增
        → llm_summary.summarize_professional()
    → _build_my_following_multi_tag()
      → summarize_professional()  # 新增调用
  → write_my_following()
    → hot_writer._write_items_to_file()
```

### 函数签名

**llm_summary.py：**
```python
def summarize_professional(article_text, article_title="", keywords=""):
    """
    生成专业学术化总结

    Args:
        article_text: 文章内容（摘要或全文）
        article_title: 文章标题
        keywords: 关键词（用户关注的主题）

    Returns:
        200-300 字的学术化总结，或 None
    """
```

---

## 下次运行

```bash
# 自动启用新功能
./run.sh

# 或仅抓取今日头条（不受影响）
toutiaonews
```

所有新生成的「我的关注」文章都会自动使用 **AI 专业总结**！

---

## 高级配置

### 调整 LLM 参数

编辑 `llm_summary.py` 中的 `summarize_professional()` 函数：

```python
# 调整字数范围
prompt += "\n内容控制在 250-350 字之间。"  # 默认 200-300

# 调整温度（0-1，越低越确定）
return _call_llm(cfg, prompt, max_tokens=800, temperature=0.2)  # 默认 0.2
```

### 禁用某个关键词的专业总结

在 config.yaml 中标记：

```yaml
keywords:
  - 油价  # 使用专业总结
  - "!快速新闻"  # 前缀 ! 表示跳过专业总结（可选）
```

---

## 相关文档

- 📖 [config.yaml 配置说明](/config.yaml)
- 📖 [LLM 集成指南](scripts/llm_summary.py)
- 📖 [「我的关注」文件结构](scripts/hot_writer.py)

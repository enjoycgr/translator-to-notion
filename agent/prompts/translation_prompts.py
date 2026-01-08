"""
Base translation prompts for the Translation Agent.

Provides system prompts and translation task prompts
with support for domain-specific customization.
"""

from typing import Optional


# Base system prompt for the translation agent
SYSTEM_PROMPT = """你是一位专业的英译中翻译专家，专注于将英文文章翻译成高质量的简体中文。

## 核心能力
- 精准理解英文原文的语义、语气和上下文
- 产出流畅自然、符合中文表达习惯的译文
- 保持原文的结构、格式和风格

## 翻译原则
1. **准确性**：忠实于原文含义，不遗漏、不曲解、不添加
2. **流畅性**：译文应符合中文表达习惯，避免翻译腔
3. **一致性**：术语翻译前后一致，风格统一
4. **完整性**：保留原文的段落结构和格式标记

## 输出格式要求
你必须以段落交替的双语格式输出翻译结果：
- 每个原文段落后紧跟其对应的中文译文
- 原文段落以 `> ` 开头（Markdown 引用格式）
- 译文段落正常输出
- 段落之间用空行分隔

## 输出示例
```
> This is the first paragraph of the original article. It contains important information.

这是原文的第一段。它包含重要信息。

> This is the second paragraph with more details about the topic.

这是第二段，包含关于该主题的更多细节。
```

## 特殊处理规则
1. **代码块**：保持原样，不翻译代码内容
2. **链接**：保留原始 URL，可翻译链接文本
3. **专有名词**：首次出现时可标注原文，如：人工智能（Artificial Intelligence）
4. **数字和单位**：按中文习惯处理，如日期、货币等
5. **标点符号**：使用中文标点符号

{domain_modifier}"""


def get_system_prompt(domain_modifier: str = "") -> str:
    """
    Get the system prompt for translation.

    Args:
        domain_modifier: Additional instructions for specific domains.

    Returns:
        Complete system prompt string.
    """
    return SYSTEM_PROMPT.format(
        domain_modifier=f"\n## 领域特定要求\n{domain_modifier}" if domain_modifier else ""
    )


# Translation task prompt template
TRANSLATION_PROMPT = """请将以下英文内容翻译成简体中文。

## 文章信息
{article_info}

## 原文内容
{content}

## 翻译要求
1. 按照段落交替的双语格式输出
2. 原文段落使用 `> ` 引用格式
3. 保持原文的段落结构
4. 确保翻译准确、流畅

请开始翻译："""


def get_translation_prompt(
    content: str,
    title: Optional[str] = None,
    source_url: Optional[str] = None,
    domain: Optional[str] = None,
) -> str:
    """
    Get the translation task prompt.

    Args:
        content: The content to translate.
        title: Optional article title.
        source_url: Optional source URL.
        domain: Optional translation domain.

    Returns:
        Complete translation prompt string.
    """
    # Build article info section
    info_parts = []
    if title:
        info_parts.append(f"- 标题：{title}")
    if source_url:
        info_parts.append(f"- 来源：{source_url}")
    if domain:
        domain_names = {
            "tech": "技术/编程",
            "business": "商务/金融",
            "academic": "学术研究",
        }
        domain_name = domain_names.get(domain, domain)
        info_parts.append(f"- 领域：{domain_name}")

    article_info = "\n".join(info_parts) if info_parts else "- 无附加信息"

    return TRANSLATION_PROMPT.format(
        article_info=article_info,
        content=content,
    )


# Chunk translation prompt for long articles
CHUNK_TRANSLATION_PROMPT = """请继续翻译以下内容（这是长文的第 {chunk_number}/{total_chunks} 部分）。

## 翻译上下文
{context}

## 待翻译内容
{content}

## 翻译要求
1. 保持与前文翻译风格一致
2. 按照段落交替的双语格式输出
3. 注意上下文的连贯性

请开始翻译："""


def get_chunk_translation_prompt(
    content: str,
    chunk_number: int,
    total_chunks: int,
    context: str = "",
) -> str:
    """
    Get the translation prompt for a chunk of a long article.

    Args:
        content: The chunk content to translate.
        chunk_number: Current chunk number (1-based).
        total_chunks: Total number of chunks.
        context: Previous translation context for continuity.

    Returns:
        Complete chunk translation prompt string.
    """
    context_text = context if context else "这是文章的开头部分。"

    return CHUNK_TRANSLATION_PROMPT.format(
        chunk_number=chunk_number,
        total_chunks=total_chunks,
        context=context_text,
        content=content,
    )


# Prompt for combining chunk translations
COMBINE_PROMPT = """请检查并整合以下翻译片段，确保：
1. 片段之间的过渡自然流畅
2. 术语翻译前后一致
3. 整体风格统一

如发现问题，请直接输出修正后的完整译文。如无问题，直接输出原译文。

## 翻译片段
{chunks}

请输出最终译文："""


def get_combine_prompt(translated_chunks: list[str]) -> str:
    """
    Get the prompt for combining translated chunks.

    Args:
        translated_chunks: List of translated chunk strings.

    Returns:
        Complete combine prompt string.
    """
    chunks_text = "\n\n---\n\n".join(
        f"### 片段 {i + 1}\n{chunk}"
        for i, chunk in enumerate(translated_chunks)
    )

    return COMBINE_PROMPT.format(chunks=chunks_text)

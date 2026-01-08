"""
Domain-specific prompts for specialized translation.

Provides tailored prompts for different content domains:
- tech: Technology and programming
- business: Business and finance
- academic: Academic research
"""

from typing import Dict, Optional

from dataclasses import dataclass


@dataclass
class DomainPromptInfo:
    """Information about a domain-specific prompt."""

    name: str  # Display name in Chinese
    name_en: str  # English name
    system_modifier: str  # Additional system prompt instructions
    examples: list[str]  # Example translations (optional)


# Domain-specific prompts dictionary
DOMAIN_PROMPTS: Dict[str, DomainPromptInfo] = {
    "tech": DomainPromptInfo(
        name="技术/编程",
        name_en="Technology/Programming",
        system_modifier="""你正在翻译技术/编程领域的内容。请特别注意：

1. **代码处理**
   - 代码块、代码片段保持原样，不翻译
   - 变量名、函数名、类名保持原文
   - 注释可以翻译，但保留原始格式

2. **技术术语**
   - 常见术语使用业界通用中文译法
   - 首次出现的专业术语可标注原文，如：容器（Container）
   - 保持术语翻译的一致性

3. **常用技术术语参考**
   - API → API（应用程序接口）
   - Container → 容器
   - Microservice → 微服务
   - Framework → 框架
   - Repository → 仓库
   - Deployment → 部署
   - Pipeline → 管道/流水线
   - Middleware → 中间件
   - Cache → 缓存
   - Thread → 线程
   - Process → 进程
   - Callback → 回调
   - Async/Await → 异步/等待
   - Dependency → 依赖
   - Component → 组件
   - Module → 模块

4. **格式保持**
   - 保留 Markdown 格式
   - 保持代码块的语言标记
   - 列表、表格结构不变""",
        examples=[
            "> The container orchestration platform uses a declarative approach.\n\n容器编排平台采用声明式方法。",
            "> You need to install the dependency first.\n\n你需要先安装这个依赖。",
        ],
    ),
    "business": DomainPromptInfo(
        name="商务/金融",
        name_en="Business/Finance",
        system_modifier="""你正在翻译商务/金融领域的内容。请特别注意：

1. **专业术语**
   - 金融缩写保留原文并首次标注中文
   - 使用正式的商务用语
   - 财务数据保持精确

2. **常用金融术语参考**
   - ROI → ROI（投资回报率）
   - EBITDA → EBITDA（息税折旧摊销前利润）
   - IPO → IPO（首次公开募股）
   - P/E Ratio → 市盈率
   - Market Cap → 市值
   - Revenue → 营收
   - Profit Margin → 利润率
   - Cash Flow → 现金流
   - Asset → 资产
   - Liability → 负债
   - Equity → 股权/权益
   - Dividend → 股息
   - Portfolio → 投资组合
   - Hedge → 对冲
   - Leverage → 杠杆

3. **数字格式**
   - 货币符号和数值保持原格式
   - 百分比、比率精确保留
   - 大数字按中文习惯表述（亿、万）

4. **语气风格**
   - 使用正式、专业的商务语言
   - 避免口语化表达
   - 保持客观、中立的叙述风格""",
        examples=[
            "> The company reported a 15% increase in quarterly revenue.\n\n该公司报告季度营收增长了 15%。",
            "> Investors are concerned about the high P/E ratio.\n\n投资者对高市盈率表示担忧。",
        ],
    ),
    "academic": DomainPromptInfo(
        name="学术研究",
        name_en="Academic Research",
        system_modifier="""你正在翻译学术研究领域的内容。请特别注意：

1. **学术规范**
   - 保持学术写作的严谨性和客观性
   - 准确传达研究方法和结论
   - 使用学术界通用的表达方式

2. **术语处理**
   - 专业术语首次出现时标注原文
   - 遵循学科领域的术语规范
   - 保持术语翻译的一致性

3. **引用格式**
   - 保留原有的引用格式（APA、MLA、Chicago 等）
   - 作者姓名、年份、页码等保持原样
   - 参考文献列表不翻译

4. **结构元素**
   - 摘要（Abstract）保持简洁客观
   - 方法论（Methodology）描述精确
   - 结论（Conclusion）逻辑清晰
   - 假设、论点表述准确

5. **语言风格**
   - 使用被动语态和第三人称
   - 避免主观性表达
   - 保持逻辑连贯性
   - 使用学术连接词（因此、然而、此外等）

6. **常用学术表达**
   - Hypothesis → 假设
   - Methodology → 方法论
   - Literature Review → 文献综述
   - Empirical → 实证的
   - Qualitative → 定性的
   - Quantitative → 定量的
   - Correlation → 相关性
   - Significance → 显著性
   - Sample Size → 样本量
   - Control Group → 对照组""",
        examples=[
            "> The study found a significant correlation between the two variables (p < 0.05).\n\n研究发现两个变量之间存在显著相关性（p < 0.05）。",
            "> According to Smith et al. (2023), this methodology has been widely adopted.\n\n根据 Smith 等人（2023）的研究，这种方法论已被广泛采用。",
        ],
    ),
}


def get_domain_prompt(domain: str) -> str:
    """
    Get the domain-specific system prompt modifier.

    Args:
        domain: The translation domain key (tech, business, academic).

    Returns:
        The domain-specific prompt modifier, or empty string if domain not found.
    """
    domain_info = DOMAIN_PROMPTS.get(domain)
    if domain_info:
        return domain_info.system_modifier
    return ""


def get_domain_name(domain: str, language: str = "zh") -> str:
    """
    Get the display name for a domain.

    Args:
        domain: The translation domain key.
        language: Language for the name ('zh' or 'en').

    Returns:
        The domain display name, or the domain key if not found.
    """
    domain_info = DOMAIN_PROMPTS.get(domain)
    if domain_info:
        return domain_info.name if language == "zh" else domain_info.name_en
    return domain


def get_available_domains() -> Dict[str, str]:
    """
    Get all available domains with their display names.

    Returns:
        Dictionary mapping domain keys to display names.
    """
    return {key: info.name for key, info in DOMAIN_PROMPTS.items()}


def get_domain_examples(domain: str) -> list[str]:
    """
    Get example translations for a domain.

    Args:
        domain: The translation domain key.

    Returns:
        List of example translation strings, or empty list if not found.
    """
    domain_info = DOMAIN_PROMPTS.get(domain)
    if domain_info:
        return domain_info.examples
    return []

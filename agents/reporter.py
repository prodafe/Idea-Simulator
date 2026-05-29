"""Reporter — 推荐导向的分析报告"""

import logging
import ollama
from config import Config

logger = logging.getLogger(__name__)

PROMPT = """你是一个风险投资分析师。基于以下信息，生成一份创业想法可行性报告。

## 用户想法
{idea}

## 用户画像
- 行业：{industry}
- 资金：{capital}
- 团队：{team_size}人
- 经验：{experience}
- 城市：{city}
- 优势：{advantage}

## 推演结果
- 行业基础成功率：{baseline}%
- 用户条件调整后：{adjusted}%
- 最终综合评估：{final}%
- 推荐结论：{verdict}

## 四条策略路径推演
{paths_text}

请生成一份专业分析报告。要求：
1. 开头直接给出结论（推荐还是不推荐）
2. 列出每个策略路径的利弊
3. 如果有不合法或擦边的策略，明确标注法律风险
4. 如果所有路径都低于50%，直接告诉用户"在当前条件下很难实现"，并给出改进建议
5. 用中文，简洁专业

报告："""


def generate_report(idea: str, profile: dict, result: dict) -> str:
    paths = result.get("all_paths", [])
    paths_text = ""
    for p in paths:
        warnings = " | ".join(p.get("warnings", []))
        w = f" ⚠️ {warnings}" if warnings else ""
        paths_text += (
            f"- **{p['strategy_name']}** ({p['legality']}): "
            f"成功率 {p['success_rate']}%, "
            f"预估 {p['time_to_profit_months']}个月盈利, "
            f"需资金约 {_fmt(p.get('capital_required_cny', 0))}"
            f"{w}\n"
        )

    verdict_text = result.get("verdict", {}).get("text", "")

    prompt = PROMPT.format(
        idea=idea,
        industry=profile.get("industry", "未指定"),
        capital=_fmt(profile.get("capital", 0)),
        team_size=profile.get("team_size", 1),
        experience=profile.get("experience", "未知"),
        city=profile.get("city", "未知"),
        advantage=profile.get("advantage", "无"),
        baseline=result.get("baseline_rate", 0),
        adjusted=result.get("adjusted_rate", 0),
        final=result.get("final_rate", 0),
        verdict=verdict_text,
        paths_text=paths_text,
    )

    try:
        from core.llm_provider import call_llm
        return call_llm(prompt, getattr(Config,"LLM_MODEL","gpt-4o-mini"), getattr(Config,"LLM_API_KEY",""), 800)
    except Exception as e:
        logger.error(f"Report error: {e}")
        return f"报告生成失败: {e}"


def _fmt(amount: int) -> str:
    if amount >= 100000000:
        return f"{amount/100000000:.1f}亿"
    if amount >= 10000:
        return f"{amount/10000:.0f}万"
    return str(amount)

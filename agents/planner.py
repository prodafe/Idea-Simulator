"""Planner — 结合用户画像拆解想法"""

import json
import logging
from config import Config

logger = logging.getLogger(__name__)

PROMPT = """你是一个创业战略顾问。根据用户的自身条件和想法，拆解为实现路径。

用户画像：
- 行业：{industry}
- 启动资金：{capital}
- 团队规模：{team_size}人
- 经验：{experience}
- 所在城市：{city}
- 学历：{education}
- 核心优势：{advantage}

用户想法：{idea}

请分析该想法在用户当前条件下的可行性，并拆解为具体的子目标。输出 JSON（不要输出其他内容）：
{{
    "idea": "想法概述",
    "domain": "所属行业",
    "feasibility_comment": "一句话评价在当前条件下的可行性",
    "sub_goals": [
        {{
            "name": "子目标名称",
            "description": "具体描述",
            "variables": [
                {{"name": "变量名", "type": "boolean|range|category", "values": ["取值1", "取值2"]}}
            ]
        }}
    ],
    "key_risks": ["主要风险1", "主要风险2"],
    "key_opportunities": ["机会点1", "机会点2"]
}}

JSON:"""


def decompose_idea(idea: str, profile: dict) -> dict:
    prompt = PROMPT.format(
        idea=idea,
        industry=profile.get("industry", "未指定"),
        capital=_fmt(profile.get("capital", 0)),
        team_size=profile.get("team_size", 1),
        experience=profile.get("experience", "未知"),
        city=profile.get("city", "未知"),
        education=profile.get("education", "未知"),
        advantage=profile.get("advantage", "无特别说明"),
    )
    try:
        from core.llm_provider import call_llm
        text = call_llm(prompt, getattr(Config,"LLM_MODEL","gpt-4o-mini"), getattr(Config,"LLM_API_KEY",""), 800)
        return _parse_json(text, idea)
    except Exception as e:
        logger.error(f"Planner error: {e}")
    return _fallback(idea, profile)


def _parse_json(text: str, idea: str) -> dict:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            raw = text[start:end].replace(",\n}", "\n}").replace(", }", "}")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
    return _fallback(idea, {})


def _fallback(idea: str, profile: dict) -> dict:
    industry = profile.get("industry", "综合")
    return {
        "idea": idea,
        "domain": industry,
        "sub_goals": [
            {"name": f"{industry}市场验证", "description": "验证目标市场规模和需求", "variables": [
                {"name": "市场规模", "type": "range", "values": ["小", "中", "大"]},
                {"name": "竞争强度", "type": "category", "values": ["低", "中", "高"]},
            ]},
            {"name": "产品/服务开发", "description": "MVP开发和用户测试", "variables": [
                {"name": "技术难度", "type": "category", "values": ["低", "中", "高"]},
                {"name": "开发周期", "type": "range", "values": ["1-3月", "3-6月", "6-12月"]},
            ]},
            {"name": "获客与增长", "description": "获取首批用户并验证增长模型", "variables": [
                {"name": "获客成本", "type": "range", "values": ["低", "中", "高"]},
                {"name": "转化率", "type": "range", "values": ["低", "中", "高"]},
            ]},
            {"name": "盈利模式验证", "description": "验证收入模型可持续性", "variables": [
                {"name": "付费意愿", "type": "boolean", "values": ["愿意", "不愿意"]},
                {"name": "客单价", "type": "range", "values": ["低", "中", "高"]},
            ]},
        ],
        "key_risks": ["市场竞争", "资金不足", "执行能力"],
        "key_opportunities": ["市场增长空间", "差异化机会"],
    }


def _fmt(amount: int) -> str:
    if amount >= 100000000:
        return f"{amount/100000000:.0f}亿"
    if amount >= 10000:
        return f"{amount/10000:.0f}万"
    return str(amount)

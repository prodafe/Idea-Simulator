"""幻觉检测 — 识别虚构统计、不可验证来源、过度精确的预测"""

import re
import json
import logging

logger = logging.getLogger(__name__)


class AntiHallucination:
    name = "hallucination"
    display_name = "幻觉检测"

    # 可疑模式
    SUSPICIOUS_PATTERNS = [
        (r'(\d+\.\d{2,})\s*%', "过度精确的百分比（多位小数）"),
        (r'第\s*(\d+)\s*天', "过于精确的天数预测"),
        (r'根据.{2,10}(?:报告|研究|调查|统计|数据)', "未验证来源引用"),
        (r'(?:所有|全部|每个|任何).{0,5}(?:都会|必然|一定|肯定)', "绝对化断言"),
        (r'(?:10{2,}|[5-9]\d{2,})\s*[万亿]', "超大数值声称"),
    ]

    # 空话 filler
    FILLER_PATTERNS = [
        "通过全面的分析和战略优化",
        "在深度洞察的基础上",
        "凭借卓越的执行力",
        "充分利用协同效应",
    ]

    def evaluate(self, idea: str, profile: dict, agent_outputs: dict,
                 llm_fn=None, anchors: dict = None) -> dict:
        violations = []

        # 1. 正则扫描：所有输出文本
        all_text = str(agent_outputs)
        for pattern, desc in self.SUSPICIOUS_PATTERNS:
            matches = re.findall(pattern, all_text)
            for match in matches[:2]:  # 每种类型最多2个
                violations.append({
                    "type": "suspicious_pattern", "severity": "medium",
                    "message": f"{desc}: '{match}' — 可能为虚构或不可验证",
                })

        # 2. 空话检测
        for fp in self.FILLER_PATTERNS:
            if fp[:10] in all_text:
                violations.append({
                    "type": "filler_language", "severity": "low",
                    "message": f"检测到空话套话: '{fp[:30]}...'",
                })

        # 3. LLM验证
        if llm_fn is not None:
            llm_violations = self._llm_check(llm_fn, idea, profile, agent_outputs)
            violations.extend(llm_violations)

        score = self._compute_score(violations)
        return {
            "score": score,
            "violations": violations,
            "corrections": [],
            "details": f"幻觉检测: {len(violations)} 项可疑, 得分 {score}/100",
        }

    def _llm_check(self, llm_fn, idea, profile, agent_outputs) -> list:
        report = str(agent_outputs.get("report", ""))[:1500]
        if not report or report == "报告生成失败":
            return []

        prompt = f"""你是事实核查员。审查以下推演报告，找出可能存在的信息幻觉。

场景: {idea}
报告: {report}

识别以下问题:
1. 引用不存在的研究/报告/统计数据
2. 过于精确且无法验证的预测数字
3. 明显编造的公司/人物/事件
4. 常识性错误

如果没有发现问题，返回空violations数组。只输出JSON:
{{"violations":[{{"severity":"medium","message":"具体问题描述"}}]}}
JSON:"""

        try:
            text = llm_fn(prompt, 300)
            s = text.find("{"); e = text.rfind("}") + 1
            if s >= 0 and e > s:
                result = json.loads(text[s:e])
                return result.get("violations", [])
        except Exception:
            pass
        return []

    def _compute_score(self, violations: list) -> int:
        base = 100
        for v in violations:
            sev = v.get("severity", "low")
            if sev == "critical": base -= 25
            elif sev == "high": base -= 15
            elif sev == "medium": base -= 8
            else: base -= 3
        return max(5, base)

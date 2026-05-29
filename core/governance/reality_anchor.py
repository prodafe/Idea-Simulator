"""真实性锚定 — 校验预测值是否在真实世界统计范围内"""

import re
import logging

logger = logging.getLogger(__name__)


class RealityAnchor:
    name = "reality"
    display_name = "真实性锚定"

    # 场景类型成功率上限（基于全球统计数据）
    MAX_SUCCESS_RATE = {
        "daily_life": 99.9, "career_job": 85, "career_promotion": 70,
        "business_startup": 65, "business_operation": 75, "investment": 80,
        "negotiation": 85, "relocation": 95, "education": 85, "legal": 80,
        "health": 90, "other": 80,
    }
    # 行业增长率的合理上限(%)
    MAX_GROWTH_BY_INDUSTRY = {
        "AI与大模型": 300, "AI": 250, "半导体": 200, "SaaS": 120,
        "电商": 100, "金融科技": 150, "生物医药": 180, "_default": 200,
    }
    # 最小盈利时间(月)
    MIN_TIME_TO_PROFIT = {
        "hardware": 18, "saas": 9, "service": 3, "consumer": 6,
        "biotech": 36, "ai": 12, "_default": 6,
    }

    def evaluate(self, idea: str, profile: dict, agent_outputs: dict,
                 llm_fn=None, anchors: dict = None) -> dict:
        violations = []
        sc_type = profile.get("_scenario_type", "other")
        deep_sim = agent_outputs.get("deep_sim", {})
        strategy = agent_outputs.get("strategy", {})
        market = agent_outputs.get("market", {})
        scenario = agent_outputs.get("scenario", {})

        # ✅ 从综合锚定库读取场景基准
        sb = (anchors or {}).get("scenario_benchmarks", {}).get(sc_type, {})
        rate_range = sb.get("baseline_rate_range", [5, 99])

        # 1. 基准成功率锚定（使用场景专属范围）
        llm_baseline = profile.get("_llm_baseline", 50)
        max_rate = rate_range[1] if rate_range else self.MAX_SUCCESS_RATE.get(sc_type, 80)
        min_rate = rate_range[0] if rate_range else 0.5
        if llm_baseline > max_rate + 5:
            violations.append({
                "type": "rate_anchor", "severity": "high",
                "message": f"LLM估算基准成功率 {llm_baseline}%，超过 {sc_type} 场景合理上限 {max_rate}%。建议锚定到 {max_rate}%。",
            })
        if llm_baseline < min_rate - 5 and min_rate > 10:
            violations.append({
                "type": "rate_anchor_low", "severity": "medium",
                "message": f"LLM估算基准成功率 {llm_baseline}%，低于 {sc_type} 场景合理下限 {min_rate}%。可能是保守估计。",
            })

        # 2. 行业增长率锚定
        industry = profile.get("industry", "")
        growth_str = str(market.get("growth_rate", ""))
        growth_match = re.search(r'(\d+\.?\d*)', str(growth_str))
        if growth_match:
            growth_val = float(growth_match.group(1))
            max_growth = self.MAX_GROWTH_BY_INDUSTRY.get(industry, 200)
            if growth_val > max_growth:
                violations.append({
                    "type": "growth_anchor", "severity": "medium",
                    "message": f"声称 {growth_val}% 增长率，{industry} 行业上限约 {max_growth}%",
                })

        # 3. 策略时间线锚定
        strategies = strategy.get("strategies", [])
        for s in strategies:
            time_months = s.get("time_months", 12)
            if isinstance(time_months, (int, float)) and time_months < 3:
                violations.append({
                    "type": "timeline_anchor", "severity": "high",
                    "message": f"策略 '{s.get('name','')}' 声称 {time_months} 个月完成，低于合理下限 3 个月",
                })

        # 4. 成功率声称检测（扫描所有输出中的离谱数字）
        all_text = str(agent_outputs)
        pct_claims = re.findall(r'(\d+\.?\d*)\s*%\s*(?:的|以)', all_text)
        for claim in pct_claims:
            val = float(claim)
            if val > 95 and sc_type != "daily_life":
                violations.append({
                    "type": "absurd_rate_claim", "severity": "critical",
                    "message": f"输出中包含 {val}% 的离谱成功率声称，非日常场景几乎不可能达到此概率",
                })
                break  # 一个就够了

        # 计算分数
        score = self._compute_score(violations)
        return {
            "score": score,
            "violations": violations,
            "corrections": self._build_corrections(violations, llm_baseline, max_rate),
            "details": f"真实性锚定完成: {len(violations)} 项违规, 得分 {score}/100",
        }

    def _compute_score(self, violations: list) -> int:
        base = 100
        for v in violations:
            sev = v.get("severity", "low")
            if sev == "critical": base -= 25
            elif sev == "high": base -= 15
            elif sev == "medium": base -= 8
            else: base -= 3
        return max(5, base)

    def _build_corrections(self, violations: list, llm_baseline: float,
                           max_rate: float) -> list:
        corrections = []
        for v in violations:
            if v["type"] == "rate_anchor":
                corrected = min(llm_baseline, max_rate)
                if corrected < llm_baseline * 0.8:
                    corrections.append({
                        "target": "baseline_rate",
                        "from": round(llm_baseline, 1),
                        "to": round(corrected, 1),
                        "reason": f"锚定到 {v.get('message', '')}",
                    })
        return corrections

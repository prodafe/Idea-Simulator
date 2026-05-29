"""可行性检查 — 验证经济/物理/资源可行性"""

import json
import logging

logger = logging.getLogger(__name__)


class FeasibilityCheck:
    name = "feasibility"
    display_name = "可行性检查"

    # 最低跑道(月)
    MIN_RUNWAY_MONTHS = 6
    # 项目类型最低团队
    MIN_TEAM = {"hardware": 5, "platform": 3, "saas": 2, "service": 1, "ai_model": 3, "_default": 2}
    # 每人每月最大任务数
    MAX_TASKS_PER_PERSON_MONTH = 4
    # 监管障碍
    REGULATORY_BLOCKERS = {
        "金融": ["银行牌照", "支付牌照", "证券牌照", "保险牌照"],
        "医疗": ["医疗器械注册证", "临床试验批件", "GMP认证"],
        "教育": ["办学许可证", "教育培训备案"],
        "食品": ["食品经营许可证", "卫生许可证"],
        "交通": ["网约车牌照", "道路运输许可证"],
        "AI": ["算法备案", "深度合成服务备案"],
    }

    def evaluate(self, idea: str, profile: dict, agent_outputs: dict,
                 llm_fn=None, anchors: dict = None) -> dict:
        violations = []
        sc_type = profile.get("_scenario_type", "other")

        # 非商业场景不检查资金/团队
        if sc_type in ("daily_life",):
            return {"score": 98, "violations": [], "corrections": [],
                    "details": "日常行为无可行性障碍"}

        deep_sim = agent_outputs.get("deep_sim", {})
        strategy = agent_outputs.get("strategy", {})
        burn_rate = deep_sim.get("burn_rate", {})

        # 1. 资金跑道检查
        capital = profile.get("capital", 0)
        monthly_burn = burn_rate.get("monthly_burn", 0)
        if monthly_burn > 0 and capital > 0:
            runway = capital / monthly_burn
            if runway < self.MIN_RUNWAY_MONTHS:
                violations.append({
                    "type": "capital_shortfall", "severity": "critical",
                    "message": f"资金仅够 {runway:.1f} 个月跑道，低于最低要求 {self.MIN_RUNWAY_MONTHS} 个月。月消耗 {monthly_burn:,.0f}，总资金 {capital:,.0f}",
                })

        # 2. 团队规模检查
        team_size = profile.get("team_size", 1)
        # 从策略推测项目复杂度
        strategies = strategy.get("strategies", [])
        if strategies:
            total_steps = sum(len(s.get("steps", [])) for s in strategies[:2])
            min_team = self._estimate_min_team(total_steps, sc_type)
            if team_size < min_team and sc_type in ("business_startup", "business_operation"):
                violations.append({
                    "type": "team_undersize", "severity": "high",
                    "message": f"{team_size} 人团队可能不足以执行 {total_steps} 个策略步骤，建议至少 {min_team} 人",
                })

        # 3. 监管障碍检查
        industry = profile.get("industry", "")
        for sector, blockers in self.REGULATORY_BLOCKERS.items():
            if sector in industry or sector in idea:
                for blocker in blockers[:2]:
                    if blocker not in str(agent_outputs).lower() and blocker not in idea:
                        violations.append({
                            "type": "regulatory_blindspot", "severity": "medium",
                            "message": f"未提及 {sector} 行业必需的「{blocker}」，可能存在合规盲区",
                        })
                break

        # 3.5 城市成本锚定(使用综合锚定库，支持多币种)
        city_name = profile.get("city", "")
        city_data = (anchors or {}).get("city_benchmarks", {}).get(city_name, {})
        if city_data and sc_type in ("career_job", "relocation", "business_startup"):
            avg_salary = city_data.get("avg_salary_month_cny") or city_data.get("avg_salary_month_usd") or city_data.get("avg_salary_month_gbp") or city_data.get("avg_salary_month_jpy") or 0
            avg_rent = city_data.get("avg_rent_1br_cny") or city_data.get("avg_rent_1br_usd") or city_data.get("avg_rent_1br_gbp") or city_data.get("avg_rent_1br_jpy") or 0
            if avg_salary > 0 and avg_rent > 0:
                rent_ratio = avg_rent / avg_salary
                if rent_ratio > 0.4:
                    violations.append({
                        "type": "city_cost_pressure", "severity": "medium",
                        "message": f"{city_name} 房租收入比 {rent_ratio:.1%} (月租{avg_rent}/月薪{avg_salary})，生活成本压力大",
                    })

        # 4. 经济合理性
        if sc_type in ("business_startup", "business_operation", "investment"):
            strategies = strategy.get("strategies", [])
            for s in strategies:
                prob = s.get("success_probability", 50)
                if prob > 80:
                    violations.append({
                        "type": "overoptimistic_strategy", "severity": "medium",
                        "message": f"策略 '{s.get('name','')}' 声称 {prob}% 成功概率，创业场景中>80%过于乐观",
                    })

        score = self._compute_score(violations)
        return {
            "score": score,
            "violations": violations,
            "corrections": [],
            "details": f"可行性检查: {len(violations)} 项违规, 得分 {score}/100",
        }

    def _estimate_min_team(self, total_steps: int, sc_type: str) -> int:
        if total_steps <= 4: return 2
        if total_steps <= 8: return 3
        if total_steps <= 15: return 5
        return 8

    def _compute_score(self, violations: list) -> int:
        base = 100
        for v in violations:
            sev = v.get("severity", "low")
            if sev == "critical": base -= 25
            elif sev == "high": base -= 15
            elif sev == "medium": base -= 8
            else: base -= 3
        return max(5, base)

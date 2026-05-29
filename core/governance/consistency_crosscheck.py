"""一致性交叉校验 — 检测Agent输出间的矛盾和数值不一致"""

import json
import logging

logger = logging.getLogger(__name__)


class ConsistencyCrossCheck:
    name = "consistency"
    display_name = "一致性校验"

    def evaluate(self, idea: str, profile: dict, agent_outputs: dict,
                 llm_fn=None, anchors: dict = None) -> dict:
        violations = []

        # 1. 结构检查：baseline_rate vs deep_sim base_rate
        scenario = agent_outputs.get("scenario", {})
        deep_sim = agent_outputs.get("deep_sim", {})
        llm_baseline = scenario.get("baseline_rate", 50) if scenario else profile.get("_llm_baseline", 50)
        ds_base = deep_sim.get("base_rate", llm_baseline)
        if abs(llm_baseline - ds_base) > 20:
            violations.append({
                "type": "numeric_mismatch", "severity": "critical",
                "message": f"LLM基准成功率({llm_baseline}%)与MC实际基准({ds_base}%)偏差超过20个百分点，数据严重不一致",
            })

        # 2. 场景类型 vs 策略类型匹配
        sc_type = profile.get("_scenario_type", "other")
        strategy = agent_outputs.get("strategy", {})
        strategies = strategy.get("strategies", [])
        if sc_type == "daily_life" and any(s.get("type") in ("speculative", "gray") for s in strategies):
            violations.append({
                "type": "type_mismatch", "severity": "high",
                "message": "日常场景不应出现投机/灰色策略，分析框架与场景类型不匹配",
            })

        # 3. 市场 vs 风险一致性
        market = agent_outputs.get("market", {})
        risk = agent_outputs.get("risk", {})
        barrier = str(market.get("entry_barrier", "")).lower()
        overall_risk = str(risk.get("overall_risk", "")).lower()
        # 如果市场说门槛低但风险说高 → 矛盾
        barrier_low = any(w in barrier for w in ["低", "low"])
        risk_high = any(w in overall_risk for w in ["高", "high"])
        if barrier_low and risk_high:
            violations.append({
                "type": "barrier_risk_contradiction", "severity": "medium",
                "message": f"市场分析认为进入门槛低，但风险评估为高风险——两者存在矛盾",
            })

        # 4. LLM语义矛盾检测
        if llm_fn is not None and len(violations) == 0:
            ctx = json.dumps({
                "market": {k: str(v)[:200] for k, v in market.items()} if isinstance(market, dict) else str(market)[:200],
                "risk": {k: str(v)[:200] for k, v in risk.items()} if isinstance(risk, dict) else str(risk)[:200],
                "strategy": str(strategy)[:300],
            }, ensure_ascii=False)
            semantic = self._llm_check(llm_fn, idea, sc_type, ctx)
            violations.extend(semantic)

        score = self._compute_score(violations)
        return {
            "score": score,
            "violations": violations,
            "corrections": [],
            "details": f"一致性校验: {len(violations)} 项矛盾, 得分 {score}/100",
        }

    def _llm_check(self, llm_fn, idea, sc_type, ctx) -> list:
        prompt = f"""你是逻辑审计员。检查以下多Agent分析是否存在语义矛盾。

场景: {idea} (类型: {sc_type})
分析数据: {ctx}

找出互相矛盾的论断（例如"竞争少"和"竞争激烈"同时出现）。如果一致则返回空列表。
只输出JSON: {{"contradictions":[{{"severity":"high/medium/low","message":"矛盾描述"}}]}}
JSON:"""
        try:
            text = llm_fn(prompt, 400)
            s = text.find("{"); e = text.rfind("}") + 1
            if s >= 0 and e > s:
                result = json.loads(text[s:e])
                return result.get("contradictions", [])
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

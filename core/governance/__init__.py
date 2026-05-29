"""Constitutional Governance Layer — 宪法治理层
5 维交叉校验：真实性锚定、社会规范、可行性、一致性、防幻觉
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from .reality_anchor import RealityAnchor
from .social_norm import SocialNormCheck
from .feasibility_check import FeasibilityCheck
from .consistency_crosscheck import ConsistencyCrossCheck
from .anti_hallucination import AntiHallucination


class GovernanceLayer:
    """宪法治理编排器：协调5子Agent，计算治理分，修正成功率"""

    def __init__(self, llm_fn=None):
        self.llm = llm_fn
        self.anchors = self._load_anchors()
        self.agents = [
            RealityAnchor(),
            SocialNormCheck(),
            FeasibilityCheck(),
            ConsistencyCrossCheck(),
            AntiHallucination(),
        ]
        self.weights = {
            "reality": 0.25, "social_norm": 0.15, "feasibility": 0.25,
            "consistency": 0.20, "hallucination": 0.15,
        }

    def _load_anchors(self) -> dict:
        path = Path(__file__).parent.parent.parent / "data" / "governance_anchors.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to load governance anchors: {e}")
        return {}

    def evaluate(self, idea: str, profile: dict, agent_outputs: dict) -> dict:
        """运行全部5子Agent，聚合治理结果"""
        results = {}
        all_violations = []
        all_corrections = []
        interventions = []

        for agent in self.agents:
            try:
                result = agent.evaluate(idea, profile, agent_outputs, self.llm, self.anchors)
            except Exception as e:
                logger.error(f"[{agent.name}] evaluation failed: {e}")
                result = {"score": 50, "violations": [], "corrections": [], "details": f"评估失败: {str(e)[:80]}", "error": True}
            results[agent.name] = result
            all_violations.extend(result.get("violations", []))
            all_corrections.extend(result.get("corrections", []))
            if result.get("score", 50) < 30:
                interventions.append({
                    "agent": agent.name,
                    "action": "critical_intervention",
                    "message": f"{agent.display_name} 得分 {result['score']}/100，触发紧急干预",
                })

        # 加权治理分
        governance_score = sum(
            results[k].get("score", 50) * self.weights.get(k, 0.2)
            for k in results
        )

        # 单个Agent极低分的额外惩罚
        penalty = 0
        for k, r in results.items():
            if r.get("score", 50) < 20:
                penalty += 0.05
        governance_score = max(0, governance_score - penalty * 100)

        # 判定
        if governance_score < 40:
            verdict = "reject"
        elif governance_score < 60:
            verdict = "warn"
        else:
            verdict = "approve"

        return {
            "scores": {k: results[k].get("score", 50) for k in results},
            "governance_score": round(governance_score, 1),
            "all_violations": all_violations,
            "corrections": all_corrections,
            "interventions": interventions,
            "verdict": verdict,
            "summary": self._build_summary(governance_score, all_violations, verdict),
        }

    def apply_correction(self, final_rate: float, governance_result: dict) -> float:
        """将治理分转化为成功率修正乘数"""
        gs = governance_result.get("governance_score", 50)
        multiplier = 0.70 + (gs / 100.0) * 0.30
        # 单Agent极低分惩罚
        for k, s in governance_result.get("scores", {}).items():
            if s < 20:
                multiplier -= 0.15
            elif s < 40:
                multiplier -= 0.05
        multiplier = max(0.40, min(1.0, multiplier))
        return round(final_rate * multiplier, 1)

    def _build_summary(self, score: float, violations: list, verdict: str) -> str:
        critical = sum(1 for v in violations if v.get("severity") == "critical")
        high = sum(1 for v in violations if v.get("severity") == "high")
        verdict_cn = {"approve": "通过", "warn": "警告", "reject": "拒绝"}
        parts = [f"治理判定: {verdict_cn.get(verdict, verdict)}，综合治理分 {score}/100"]
        if critical:
            parts.append(f"{critical} 项严重违规")
        if high:
            parts.append(f"{high} 项高优先级违规")
        if not critical and not high:
            parts.append("未发现严重违规")
        return "；".join(parts)

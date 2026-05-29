"""社会规范校验 — 检查行为假设是否符合人类社会现实"""

import json
import logging

logger = logging.getLogger(__name__)


class SocialNormCheck:
    name = "social_norm"
    display_name = "社会规范校验"

    # 各国社会规范
    COUNTRY_NORMS = {
        "中国": {"guanxi_speed": "中", "trust_basis": "关系/人脉", "cold_approach_ok": True},
        "日本": {"guanxi_speed": "慢", "trust_basis": "正式引荐", "cold_approach_ok": False},
        "美国": {"guanxi_speed": "快", "trust_basis": "资质/品牌", "cold_approach_ok": True},
        "英国": {"guanxi_speed": "中", "trust_basis": "社交圈/背书", "cold_approach_ok": False},
    }

    def evaluate(self, idea: str, profile: dict, agent_outputs: dict,
                 llm_fn=None, anchors: dict = None) -> dict:
        """LLM驱动的社会规范校验"""
        if llm_fn is None:
            return {"score": 50, "violations": [], "corrections": [],
                    "details": "LLM不可用，跳过社会规范校验"}

        sc_type = profile.get("_scenario_type", "other")
        country = profile.get("country", "中国")
        norm = self.COUNTRY_NORMS.get(country, self.COUNTRY_NORMS["中国"])
        ctx = json.dumps(agent_outputs, ensure_ascii=False)[:2000]

        prompt = f"""你是社会学家和行为经济学家。审查以下推演结果中的社会行为假设是否现实。

场景: {idea}
场景类型: {sc_type}
国家: {country} (社会规范: 关系建立速度={norm['guanxi_speed']}, 信任基础={norm['trust_basis']}, 适合冷启动={norm['cold_approach_ok']})
推演数据: {ctx}

检查要点:
1. 用户/客户增长速度是否现实（社交媒体病毒传播<200%/月，B2B销售<50%/月）
2. 人脉/信任的建立时间是否合理（特别是{country}文化下）
3. 是否有对他人行为的不合理假设（"所有人都会..."、"必然..."）
4. 文化适配性：策略是否符合{country}的社会习俗
5. 场景类型({sc_type})的行为模式是否合理

请评分(0-100)并列出具体违规项。只输出JSON:
{{"score":75,"violations":[{{"type":"adoption_speed","severity":"medium","message":"声称1个月覆盖10万用户不符合{country}的社交传播规律"}}]}}
JSON:"""

        try:
            text = llm_fn(prompt, 400)
            s = text.find("{"); e = text.rfind("}") + 1
            if s >= 0 and e > s:
                result = json.loads(text[s:e])
                result.setdefault("violations", [])
                result.setdefault("details", f"社会规范校验完成, 得分 {result.get('score', 50)}/100")
                return result
        except Exception as e:
            logger.warning(f"Social norm check failed: {e}")

        return {"score": 50, "violations": [], "corrections": [],
                "details": f"社会规范校验出错: {str(e)[:60]}"}

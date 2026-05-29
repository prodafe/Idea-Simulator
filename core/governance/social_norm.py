"""社会规范校验 — 规则优先+LLM辅助，检查行为假设是否符合人类社会现实"""

import json, re, logging

logger = logging.getLogger(__name__)


class SocialNormCheck:
    name = "social_norm"
    display_name = "社会规范校验"

    # 各国社会规范
    COUNTRY_NORMS = {
        "中国": {"trust_speed": "中", "trust_basis": "关系/人脉", "cold_ok": True, "b2b_cycle_months": 3},
        "日本": {"trust_speed": "慢", "trust_basis": "正式引荐", "cold_ok": False, "b2b_cycle_months": 6},
        "美国": {"trust_speed": "快", "trust_basis": "资质/品牌", "cold_ok": True, "b2b_cycle_months": 1},
        "英国": {"trust_speed": "中", "trust_basis": "社交圈/背书", "cold_ok": False, "b2b_cycle_months": 2},
    }
    # 行为边界（规则引擎）
    BEHAVIORAL_BOUNDS = {
        "max_monthly_user_growth_pct": 200,     # 月用户增长率上限
        "max_b2b_conversion_first_month_pct": 15, # B2B首月转化率上限
        "max_viral_coefficient": 1.5,            # 病毒系数上限
        "min_trust_build_months_b2b": 1,         # B2B信任建立最短时间
        "max_sustainable_weekly_hours": 60,       # 可持续周工时
    }

    def evaluate(self, idea: str, profile: dict, agent_outputs: dict,
                 llm_fn=None, anchors: dict = None) -> dict:
        violations = []
        sc_type = profile.get("_scenario_type", "other")
        country = profile.get("country", "中国")
        norm = self.COUNTRY_NORMS.get(country, self.COUNTRY_NORMS["中国"])
        all_text = str(agent_outputs)
        strategy = agent_outputs.get("strategy", {})

        # ── 规则检查 ──

        # 1. 病毒传播速度检查
        viral_patterns = [
            (r'(\d+)\s*[个万]\s*用户.{0,10}(\d+)\s*[天周月]', "用户增长速度"),
            (r'病毒.{0,5}(?:传播|式|营销)', "病毒传播声称"),
            (r'(\d+)%?\s*(?:转化|付费|留存)', "转化率/付费率声称"),
        ]
        for pattern, desc in viral_patterns:
            matches = re.findall(pattern, all_text)
            if matches:
                violations.append({
                    "type": "growth_claim", "severity": "medium",
                    "message": f"包含{desc}('{str(matches[0])[:40]}')，需核实是否符合{country}社交传播规律",
                })
                break  # 每种类型一个够

        # 2. 文化适配检查
        strategies = strategy.get("strategies", [])
        for s in strategies:
            steps = " ".join(str(s.get("steps", [])))
            if not norm["cold_ok"] and any(w in steps for w in ["电话销售", "冷邮件", "直接拜访", "陌生拜访"]):
                violations.append({
                    "type": "cultural_mismatch", "severity": "high",
                    "message": f"策略包含冷启动销售方式，但{country}社会规范依赖{norm['trust_basis']}，不适合陌生拜访",
                })
                break

        # 3. 信任建立时间检查
        for s in strategies:
            time_m = s.get("time_months", 12)
            b2b_words = ["企业", "B2B", "大客户", "政府", "招标"]
            if any(w in str(s) for w in b2b_words) and time_m < norm["b2b_cycle_months"]:
                violations.append({
                    "type": "trust_timeline", "severity": "medium",
                    "message": f"B2B策略声称{time_m}个月完成，{country}的B2B销售周期通常至少{norm['b2b_cycle_months']}个月",
                })
                break

        # 4. 绝对化断言检查
        absolutes = re.findall(r'(?:所有|全部|每个|任何|必然|一定|肯定|绝对).{0,15}(?:都会|能|可以|不会)', all_text)
        if absolutes:
            violations.append({
                "type": "absolute_claim", "severity": "low",
                "message": f"包含绝对化断言: '{absolutes[0][:40]}'——现实世界极少100%确定",
            })

        # 5. 场景行为合理性（日常/应聘不应有商业策略框架）
        if sc_type == "daily_life" and any(s.get("type") in ("aggressive", "speculative", "gray") for s in strategies):
            violations.append({
                "type": "type_behavior_mismatch", "severity": "medium",
                "message": "日常行为场景不应出现商业策略框架，分析维度与场景不匹配",
            })

        # ── LLM辅助（可选，失败不影响分数）──
        if llm_fn is not None:
            try:
                llm_violations = self._llm_check(llm_fn, idea, sc_type, country, str(agent_outputs)[:600])
                violations.extend(llm_violations)
            except Exception:
                pass  # LLM失败不阻塞规则结果

        score = self._compute_score(violations)
        return {
            "score": score,
            "violations": violations,
            "corrections": [],
            "details": f"社会规范校验(规则+LLM): {len(violations)}项违规, 得分{score}/100 | {country}·{norm['trust_basis']}型社会",
        }

    def _llm_check(self, llm_fn, idea, sc_type, country, ctx) -> list:
        prompt = f"""审查以下场景是否存在社会行为假设不合理之处。
场景({sc_type}, {country}): {idea}
上下文: {ctx[:400]}
发现的问题(JSON数组，无问题则空): {{"violations":[{{"severity":"low/medium","message":"..."}}]}}
JSON:"""
        try:
            text = llm_fn(prompt, 300)
            s = text.find("{"); e = text.rfind("}") + 1
            if s >= 0 and e > s:
                result = json.loads(text[s:e])
                return result.get("violations", [])
        except Exception:
            return []

    def _compute_score(self, violations: list) -> int:
        base = 95  # 起始分稍低(规则引擎不如LLM精细)
        for v in violations:
            sev = v.get("severity", "low")
            if sev == "critical": base -= 25
            elif sev == "high": base -= 15
            elif sev == "medium": base -= 8
            else: base -= 3
        return max(5, base)

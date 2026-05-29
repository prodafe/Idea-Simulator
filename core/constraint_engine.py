"""v13 Constraint Engine — 变量交互×文化圈层×资源可及性×认知偏差"""

import json, random
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"

class ConstraintEngine:
    def __init__(self):
        self.cd = self._load("constraints.json")

    def _load(self, f):
        return json.loads((DATA/f).read_text(encoding="utf-8")) if (DATA/f).exists() else {}

    def analyze(self, profile: dict) -> dict:
        city = profile.get("city", "北京")
        country = profile.get("country", "中国")
        capital = profile.get("capital", 1000000)
        exp = profile.get("experience", "")
        skills = profile.get("skills", "") or profile.get("advantage", "")
        edu = profile.get("education", "")

        # 1. 文化圈层判断
        layer = self._identify_layer(city, country, capital, exp, edu)

        # 2. 资源可及性评估
        resources = self._assess_resources(city, capital, exp, skills)

        # 3. 约束网络连锁效应
        constraints = self._find_constraints(profile, resources)

        # 4. 认知偏差影响
        biases = self._apply_biases(profile)

        # 5. 综合修正
        total_modifier = layer.get("access_bonus", 0) * 0.3
        total_modifier += (sum(resources.values()) / max(len(resources), 1) - 0.5) * 0.4
        total_modifier += sum(b["impact"] for b in biases) * 0.2
        for c in constraints:
            total_modifier += sum(ch["impact"] for ch in c.get("cascade", [])) * 0.1

        return {
            "cultural_layer": layer,
            "resource_access": resources,
            "constraint_chains": constraints,
            "cognitive_biases": biases,
            "total_constraint_modifier": round(max(-0.4, min(0.3, total_modifier)), 3),
            "awareness_score": self._awareness(profile, resources),
        }

    def _identify_layer(self, city, country, capital, exp, edu) -> dict:
        layers = self.cd.get("cultural_layers", {})
        tier1_cn = ["北京","上海","深圳","广州","杭州"]
        tier2_cn = ["成都","武汉","南京","苏州","西安","重庆","长沙","合肥","天津","厦门","福州","济南","青岛","大连","郑州","东莞","佛山","珠海","宁波","无锡"]
        tier1_us = ["旧金山/硅谷","纽约","波士顿","西雅图","洛杉矶"]
        tier1_uk = ["伦敦","剑桥","牛津"]
        tier1_jp = ["东京23区","横浜"]

        is_tier1 = city in (tier1_cn + tier1_us + tier1_uk + tier1_jp)
        is_tier2 = city in tier2_cn

        # Has elite markers
        has_elite_markers = False
        elite_keywords = ["大厂","BAT","字节","腾讯","阿里","谷歌","微软","Amazon","FAANG","MBA","EMBA","常春藤","清北","985","海归","留学"]
        if any(w in str(exp) for w in elite_keywords) or any(w in str(edu) for w in elite_keywords):
            has_elite_markers = True

        if country == "中国":
            if is_tier1 and has_elite_markers and capital >= 5000000:
                return layers.get("一线城市精英圈", {})
            elif is_tier1 and not has_elite_markers:
                return layers.get("一线城市草根圈", {})
            elif is_tier2:
                return layers.get("二线城市中产圈", {})
            elif capital < 100000:
                return layers.get("乡镇农村圈", {})
            else:
                return layers.get("三线及以下城市圈", {})
        elif country in ("美国","英国"):
            return layers.get("海外华人精英圈", {}) if "中国" in str(exp) or "华人" in str(exp) else layers.get("一线城市精英圈", {})
        else:
            return layers.get("二线城市中产圈", {})

    def _assess_resources(self, city, capital, exp, skills_str) -> dict:
        ra = self.cd.get("resource_accessibility", {})
        result = {}

        # Capital access
        cap = ra.get("资本可及性", {})
        if capital >= 10000000: result["资本"] = 0.8
        elif capital >= 2000000: result["资本"] = 0.5
        elif capital >= 500000: result["资本"] = 0.3
        else: result["资本"] = 0.1
        if any(w in str(exp) for w in ["投资人","VC","融资","成功退出","卖过公司"]):
            result["资本"] += 0.2

        # Talent access
        talent = ra.get("人才可及性", {})
        tier1_cn = ["北京","上海","深圳","广州","杭州"]
        if city in tier1_cn + ["旧金山/硅谷","纽约","波士顿","伦敦"]:
            result["人才"] = 0.7
        elif any(w in str(exp) for w in ["大厂","BAT","字节"]):
            result["人才"] = 0.6
        else:
            result["人才"] = 0.3

        # Information access
        info = ra.get("信息可及性", {})
        if any(w in str(skills_str).lower() for w in ["english","英语","英文"]):
            result["信息"] = 0.8
        elif any(w in str(exp) for w in ["大厂","科技","互联网","AI"]):
            result["信息"] = 0.6
        else:
            result["信息"] = 0.4

        # Policy access
        if city in tier1_cn:
            result["政策"] = 0.7
        elif any(w in str(exp) for w in ["政府","央企","体制内"]):
            result["政策"] = 0.8
        else:
            result["政策"] = 0.3

        return {k: min(1.0, v) for k, v in result.items()}

    def _find_constraints(self, profile, resources) -> list:
        chains = self.cd.get("constraint_network", {}).get("chains", [])
        active = []
        capital = profile.get("capital", 0)
        exp = str(profile.get("experience", ""))
        skills = str(profile.get("skills", "") or profile.get("advantage", ""))

        if capital < 500000:
            active.append(chains[0])  # 资金不足
        if resources.get("资本", 0) < 0.3 and resources.get("人才", 0) < 0.4:
            active.append(chains[1])  # 人脉匮乏
        if profile.get("disease") or profile.get("health_impact"):
            active.append(chains[2])  # 健康问题
        if any(w in exp for w in ["刚毕业","首次","第一"]) and capital > 1000000:
            active.append(chains[3])  # 过度自信
        if resources.get("信息", 0) < 0.3:
            active.append(chains[4])  # 信息洼地
        age = profile.get("age_num", 30)
        gender = profile.get("gender", "")
        if age > 45 and capital < 1000000:
            active.append({"trigger":"年龄+资金双重约束","cascade":[{"target":"融资","impact":-0.3},{"target":"团队招募","impact":-0.2}]})

        return active

    def _apply_biases(self, profile) -> list:
        biases = self.cd.get("cognitive_biases", [])
        active = []
        exp = str(profile.get("experience", ""))
        capital = profile.get("capital", 0)

        if "首次" in exp or "刚毕业" in exp or "第一" in exp:
            active.append(biases[3])  # 达克效应
        if capital > 5000000 and "首次" in exp:
            active.append(biases[0])  # 幸存者偏差
        if "AI" in str(profile.get("industry","")) and "AI" in str(profile.get("idea","")):
            active.append(biases[4])  # 从众效应
        active.append(biases[2])  # 确认偏误(几乎人人都有)
        active.append(biases[6])  # 框架效应

        return active[:4]

    def _awareness(self, profile, resources) -> dict:
        resource_avg = sum(resources.values()) / max(len(resources), 1)
        exp = str(profile.get("experience", ""))
        has_experience = any(w in exp for w in ["年","大厂","创业","成功","失败"])

        score = resource_avg * 0.6 + (0.3 if has_experience else 0.1) * 0.4
        level = "高" if score > 0.6 else "中" if score > 0.3 else "低"

        return {
            "score": round(score, 2),
            "level": level,
            "insight": self._awareness_insight(level, profile),
        }

    def _awareness_insight(self, level, profile) -> str:
        if level == "高":
            return "你对行业和资源有较清晰认知,最大的风险是过度自信和路径依赖"
        elif level == "中":
            return "你知道一些但也有很多不知道的,最大的风险是被表面信息误导"
        else:
            city = profile.get("city", "")
            return f"在{ city }这样的信息环境下,你可能根本不知道外面有多少机会,最大的风险是认知局限让你选择了错误的方向"

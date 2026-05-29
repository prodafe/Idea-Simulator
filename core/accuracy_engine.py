"""v10 Accuracy Engine — 变量相关性 + 事实校验 + 回测 + 幂律分布"""

import json, random, math
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"

class AccuracyEngine:
    def __init__(self):
        self.hc = self._load("historical_cases.json")
        self.correlation = self._build_correlation()

    def _load(self, f):
        return json.loads((DATA/f).read_text(encoding="utf-8")) if (DATA/f).exists() else {}

    # ═══════════════════════════════════════════
    # 1. 变量相关性矩阵
    # ═══════════════════════════════════════════
    def _build_correlation(self) -> dict:
        """真实世界变量相关性——不是独立随机，它们是联动的"""
        return {
            # 宏观经济→行业
            "经济衰退": {"VC融资": -0.8, "消费意愿": -0.7, "招聘需求": -0.6},
            "大规模刺激": {"VC融资": 0.6, "消费意愿": 0.5, "基建投资": 0.8},
            "利率上升": {"VC融资": -0.5, "房地产": -0.7, "股市": -0.6},
            # 科技趋势
            "AI突破": {"AI投资": 0.9, "自动化需求": 0.8, "白领失业恐慌": 0.6},
            "芯片短缺": {"硬件成本": 0.7, "汽车生产": -0.5, "电子产品价格": 0.6},
            # 社会因素
            "生育率下降": {"教育需求": -0.4, "银发经济": 0.7, "劳动力供给": -0.6},
            "老龄化加速": {"医疗支出": 0.8, "养老金压力": 0.7, "劳动力短缺": 0.6},
            # 个人因素
            "高负债": {"风险承受": -0.7, "投资意愿": -0.6, "消费意愿": -0.5},
            "技术能力": {"创业成功率": 0.4, "降维打击能力": 0.5, "转型难度": -0.3},
            "健康问题": {"工作效率": -0.6, "决策质量": -0.4, "出勤率": -0.7},
            # 城市因素
            "一线城市": {"生活成本": 0.8, "人才密度": 0.7, "竞争强度": 0.8, "融资机会": 0.7},
            "二线城市": {"生活成本": 0.3, "人才密度": 0.2, "竞争强度": 0.3, "政府补贴": 0.5},
        }

    def apply_correlation(self, event_name: str, rate: float) -> float:
        """如果某事件发生，检查并应用相关事件的影响"""
        if event_name not in self.correlation:
            return rate
        corr = self.correlation[event_name]
        adjustment = 0.0
        for related_event, coefficient in corr.items():
            if random.random() < abs(coefficient) * 0.5:
                adjustment += coefficient * random.uniform(0.01, 0.05)
        return rate * (1 + max(-0.2, min(0.2, adjustment)))

    # ═══════════════════════════════════════════
    # 2. 幂律分布采样（替代高斯分布）
    # ═══════════════════════════════════════════
    def power_law_sample(self, base_rate: float, alpha: float = 2.5) -> float:
        """幂律分布：大多数创业失败，少数超级成功"""
        # Pareto distribution sampling
        u = random.random()
        x_min = base_rate / 100 * 0.5
        sample = x_min / (u ** (1.0 / alpha))
        return min(0.99, max(0.001, sample * 2))

    def gaussian_sample(self, mean: float, std: float) -> float:
        return max(0.001, min(0.99, random.gauss(mean, std)))

    # ═══════════════════════════════════════════
    # 3. 历史回测
    # ═══════════════════════════════════════════
    def back_test(self, predicted_rate: float, industry: str, profile: dict) -> dict:
        """用历史案例验证预测的合理性"""
        cases = self.hc.get("cases", [])
        matches = []
        for c in cases:
            if not c.get("outcome") or not c.get("industry"):
                continue
            # Industry match
            score = 0
            if industry and (industry in c.get("industry", "") or c.get("industry", "") in industry):
                score += 2
            if score >= 2:
                outcomes = {"成功": 1, "IPO": 1, "超级成功": 1, "高速增长": 1, "成功退出": 1, "超级IPO": 1, "盈利超级成功": 1, "全球霸主": 1}
                failed = {"失败": 1, "破产": 1, "崩塌": 1, "欺诈": 1, "倒闭": 1, "暴雷": 1, "衰落": 1, "欺诈破产": 1}
                matches.append({
                    "company": c["company"], "outcome": c["outcome"],
                    "lesson": c.get("lesson", ""), "year": c.get("year", 0),
                    "was_success": c["outcome"] in outcomes,
                })

        if not matches:
            return {"anchored": False, "message": "无足够历史对标数据"}
        successes = sum(1 for m in matches if m["was_success"])
        historical_rate = successes / len(matches) * 100
        # 如果预测和历史偏差超过30%，发出警告
        deviation = abs(predicted_rate - historical_rate)
        return {
            "anchored": True,
            "historical_rate": round(historical_rate, 1),
            "predicted_rate": round(predicted_rate, 1),
            "deviation": round(deviation, 1),
            "warning": f"预测({predicted_rate:.0f}%)与历史({historical_rate:.0f}%)偏差{deviation:.0f}%——请谨慎解读" if deviation > 30 else None,
            "similar_cases": len(matches),
            "sample": [{"company": m["company"], "outcome": m["outcome"], "lesson": m["lesson"][:60]} for m in matches[:5]],
        }

    # ═══════════════════════════════════════════
    # 4. 事实锚定
    # ═══════════════════════════════════════════
    def fact_anchor(self, profile: dict) -> dict:
        """根据用户真实条件锚定成功率范围"""
        anchors = []
        cap = profile.get("capital", 1000000)
        team = profile.get("team_size", 3)
        exp = profile.get("experience", "")
        country = profile.get("country", "中国")

        # 基于真实统计数据的锚定规则
        if cap < 100000:
            anchors.append("启动资金<10万：全球统计表明此资金段创业成功率<3%")
        elif cap < 500000:
            anchors.append("启动资金<50万：成功率约5-8%，多数死于资金链断裂")

        if team <= 1:
            anchors.append("单人创业：统计存活率仅2-5%，缺乏团队是最致命短板")
        elif team <= 3:
            anchors.append("小团队(2-5人)：成功率约8-12%")

        if "首次" in exp or "刚毕业" in exp:
            anchors.append("首次创业者成功率约为连续创业者的40-60%")

        if country == "中国":
            anchors.append("中国市场：创业公司5年存活率约7%(工商总局数据)")
        elif country == "美国":
            anchors.append("美国市场：创业公司5年存活率约50%(SBA数据)，但'存活'≠'成功'")
        elif country == "日本":
            anchors.append("日本市场：创业率G7最低，社会容错率极低")
        elif country == "英国":
            anchors.append("英国市场：FinTech/创意产业生态强，但脱欧后的跨境壁垒仍在")

        # 年龄锚定
        age = profile.get("age_num", 30)
        if age > 50:
            anchors.append(f"50岁以上创业：成功率比30岁低约40%，但行业经验丰富可部分抵消")
        elif age < 22:
            anchors.append("22岁以下：成功率极低，但试错成本低，有成长空间")

        # 健康锚定
        if profile.get("extreme_events"):
            anchors.append(f"健康/债务/前科等负面因素累计影响：预计降低成功率{abs(profile.get('extreme_mod',0))*100:.0f}%")

        return {
            "anchors": anchors,
            "suggested_range": self._suggest_range(anchors, profile),
        }

    def _suggest_range(self, anchors, profile) -> dict:
        cap = profile.get("capital", 1000000)
        if cap < 100000:
            low, high = 0.5, 5
        elif cap < 500000:
            low, high = 3, 12
        elif cap < 2000000:
            low, high = 8, 25
        elif cap < 10000000:
            low, high = 12, 35
        else:
            low, high = 15, 45
        return {"low": low, "high": high}

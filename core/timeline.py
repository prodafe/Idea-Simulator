"""Timeline Engine — 月级推演，穿越未来"""

import json
import random
from pathlib import Path


class TimelineEngine:
    """时间线推演引擎：按月模拟想法从0到24个月的发展"""

    def __init__(self):
        methods_path = Path(__file__).parent.parent / "data" / "methods.json"
        self.phases = {
            "0-3月": "验证期：市场调研、MVP开发、种子用户获取",
            "3-6月": "启动期：产品迭代、付费验证、团队组建",
            "6-12月": "增长期：规模化获客、收入模型验证、融资",
            "12-18月": "扩张期：跨区域/跨品类扩张、团队50+",
            "18-24月": "成熟期：盈利稳定、退出/IPO/持续扩张",
        }

    def project(self, idea: str, profile: dict, plan: dict, strategy: str, methods: list[dict]) -> list[dict]:
        """生成24个月的逐月推演

        Returns:
            [{month, milestone, revenue_estimate, team_size, risk_events, cash_remaining, key_decision}]
        """
        capital = profile.get("capital", 1000000)
        team = profile.get("team_size", 3)
        city = profile.get("city", "北京")

        # 城市数据
        city_data = self._load_city(city)

        timeline = []
        cash = capital
        current_team = team
        monthly_burn, monthly_revenue = self._calc_burn_rate(capital, city_data, current_team), 0

        sub_goals = plan.get("sub_goals", [])
        method_names = [m.get("name", "") for m in methods[:3]]

        for month in range(1, 25):
            phase = self._get_phase(month)
            milestone = ""
            risk_events = []
            revenue = 0

            # 月度模拟
            if month <= 3:
                milestone = f"第{month}个月: {self._pick(['完成市场调研', '搭建MVP原型', '注册公司和商标', '组建核心团队', '对接第一批潜在客户'])}"
                monthly_burn = self._estimate_burn(city_data, current_team) * 0.6
                if month == 3:
                    milestone += "。完成种子用户验证"

            elif month <= 6:
                milestone = f"第{month}个月: {self._pick(['产品1.0上线', '获得首批付费客户', '开始接触投资人', '完善商业计划书', '申请行业资质'])}"
                monthly_burn = self._estimate_burn(city_data, current_team) * 0.85
                if month == 4 and random.random() > 0.6:
                    risk_events.append("客户反馈产品体验差，需紧急迭代")

            elif month <= 12:
                milestone = f"第{month}个月: {self._pick(['月营收突破10万', '团队扩张至15人', '完成天使/A轮融资', '推出2.0版本', '跨城市试点'])}"
                monthly_burn = self._estimate_burn(city_data, current_team) * 1.2
                revenue = random.randint(20000, 150000) if month > 8 else random.randint(5000, 50000)
                if month == 9 and random.random() > 0.5:
                    risk_events.append(f"竞争对手推出类似产品，{city}市场受冲击")

            elif month <= 18:
                milestone = f"第{month}个月: {self._pick(['月营收突破50万', 'B轮融资到账', '进入3个新城市', '团队突破50人', '合作渠道破百'])}"
                monthly_burn = self._estimate_burn(city_data, current_team) * 1.5
                revenue = random.randint(50000, 500000)
                if month == 15 and random.random() > 0.5:
                    risk_events.append("核心员工被挖，关键岗位空缺")

            else:
                milestone = f"第{month}个月: {self._pick(['月营收稳定200万+', '启动C轮/Pre-IPO', '行业前三地位确立', '并购谈判', '海外市场拓展'])}"
                monthly_burn = self._estimate_burn(city_data, current_team) * 1.3
                revenue = random.randint(100000, 1000000)

            # 现金流更新
            cash = cash - monthly_burn + revenue
            monthly_revenue = revenue

            # 方法影响
            for m in methods:
                if m.get("risk") == "critical" and random.random() > 0.85:
                    risk_events.append(f"使用「{m['name']}」出现法律/合规问题")

            # 城市特有风险
            city_risks = {"北京": "监管审查趋严", "上海": "外资撤退影响市场", "深圳": "同行挖角激烈"}
            if month in [6, 12, 18] and random.random() > 0.7:
                risk_events.append(city_risks.get(city, "地方政策变动"))

            # 人员变化
            if month in [6, 12, 18, 24]:
                current_team += random.randint(1, 3) if cash > 0 else random.randint(-2, 0)

            timeline.append({
                "month": month,
                "phase": phase,
                "milestone": milestone,
                "revenue_estimate": max(0, revenue),
                "burn_rate": int(monthly_burn),
                "cash_remaining": max(0, int(cash)),
                "team_size": max(0, current_team),
                "risk_events": risk_events,
                "key_decision": self._get_decision(month, cash),
                "status": "存活" if cash > 0 else "现金流断裂",
            })

            if cash <= 0:
                break

        return timeline

    def _load_city(self, city: str) -> dict:
        path = Path(__file__).parent.parent / "data" / "city_data.json"
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        for country_name, cdata in data.get("countries", {}).items():
            for rk in ("provinces", "states", "regions"):
                for region_name, region_data in cdata.get(rk, {}).items():
                    if city in region_data.get("cities", {}):
                        ci = region_data["cities"][city]
                        return {
                            "success_mod": ci.get("s", ci.get("success_mod", 0.8)),
                            "competition": ci.get("co", ci.get("competition", 0.5)),
                            **ci
                        }
        return {}

    def _get_phase(self, month: int) -> str:
        for period, desc in self.phases.items():
            start, end = period.split("-")
            end = end.replace("月+", "99")
            if int(start.replace("月", "")) <= month <= int(end):
                return desc
        return "持续运营期"

    def _estimate_burn(self, city_data: dict, team_size: int) -> float:
        avg_salary = city_data.get("metrics", {}).get("avg_salary_cny", 12000)
        rent = city_data.get("metrics", {}).get("office_rent_sqm_month", 100)
        return team_size * avg_salary * 1.4 + rent * max(20, team_size * 10)

    def _calc_burn_rate(self, capital: int, city_data: dict, team: int) -> float:
        return self._estimate_burn(city_data, team)

    def _pick(self, options: list[str]) -> str:
        return random.choice(options)

    def _get_decision(self, month: int, cash: float) -> str:
        if cash <= 0:
            return "现金流已断裂，需要立即融资或缩减规模"
        if month == 6 and cash < 500000:
            return "建议尽快启动融资，现金仅够支撑3个月"
        if month == 12 and cash < 1000000:
            return "关键决策点：继续独立发展还是寻求被收购"
        if month == 18:
            return "考虑是否启动B轮或接受并购要约"
        return "按计划推进"

"""v4 全球跨国推演引擎"""

import json, math, random
from dataclasses import dataclass, field
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"

@dataclass
class PathResult:
    strategy: str; strategy_name: str; legality: str
    methods: list; success_rate: float; risk_level: str
    time_months: int; capital: int
    warnings: list = field(default_factory=list)
    timeline: list = field(default_factory=list)
    narrative: str = ""
    def to_dict(self):
        return {"strategy":self.strategy,"strategy_name":self.strategy_name,"legality":self.legality,"methods":[{"name":m.name,"category":m.category,"risk":m.risk,"desc":m.desc} for m in self.methods],"success_rate":round(self.success_rate,1),"risk_level":self.risk_level,"time_to_profit_months":self.time_months,"capital_required_cny":self.capital,"warnings":self.warnings,"timeline":self.timeline,"future_narrative":self.narrative}


class GlobalSimulator:
    def __init__(self):
        self.bm = self._j("benchmarks.json")
        self.cd = self._j("city_data.json")
        self.md = self._j("methods.json")

    def _j(self, f): return json.loads((DATA/f).read_text(encoding="utf-8")) if (DATA/f).exists() else {}

    def simulate(self, profile: dict, plan: dict, research: list) -> dict:
        country = profile.get("country", "中国")
        city_name = profile.get("city", "北京")
        industry = profile.get("industry", "")

        ind = self._match_industry(industry)
        city = self._match_city(country, city_name)
        baseline = ind.get("baseline_success_rate", 10)
        adjusted = self._apply_profile(profile, baseline, city, country)

        evidence = min(8, sum(r.get("evidence_count",0) for r in research)*0.15)
        adjusted = min(95, adjusted + evidence)

        paths = self._simulate_all(profile, plan, adjusted, ind, city, country, research)

        # 跨国对比：如果用户所在城市成功率>50%，找出全球更优城市
        cross_country = []
        if paths and paths[0].success_rate > 0:
            cross_country = self._cross_country_compare(profile, plan, ind)

        max_rate = paths[0].success_rate if paths else 0
        rec = [p for p in paths if p.success_rate >= 50]

        return {
            "baseline_rate": baseline, "adjusted_rate": adjusted,
            "final_rate": round(max_rate, 1),
            "all_paths": [p.to_dict() for p in paths],
            "recommended_paths": [p.to_dict() for p in rec],
            "has_recommendation": len(rec) > 0,
            "verdict": self._verdict(max_rate, len(rec)),
            "industry": {k:v for k,v in ind.items() if k!="failure_reasons"},
            "city_info": {"name":city_name,"country":country,**{k:v for k,v in city.items() if k not in ("success_mod",)}},
            "cross_country": cross_country,
            "methods_count": sum(len(v["methods"]) for v in self.md.get("categories",{}).values()),
        }

    def _cross_country_compare(self, profile, plan, ind) -> list:
        """跨国对比：在全球所有城市中推演，找到成功率最高的"""
        results = []
        user_country = profile.get("country", "中国")
        user_city = profile.get("city", "北京")
        user_rate = 0

        countries = self.cd.get("countries", {})
        for cname, cdata in countries.items():
            for region_key in ["provinces", "states", "regions"]:
                for region_name, region_data in cdata.get(region_key, {}).items():
                    for city_name, city_info in region_data.get("cities", {}).items():
                        if city_name in ("其他", "その他"): continue
                        # 紧凑格式取s字段作为success_mod
                        if "s" in city_info and "success_mod" not in city_info:
                            city_info = {**city_info, "success_mod": city_info.get("s", 0.8)}
                        baseline = ind.get("baseline_success_rate", 10)
                        p = dict(profile)
                        p["country"] = cname; p["city"] = city_name
                        rate = self._apply_profile(p, baseline, city_info, cname)
                        rate = min(95, rate + random.uniform(-2,5))
                        results.append({"country":cname,"city":city_name,"rate":round(rate,1),"flag":cdata.get("flag","")})
                if cname == user_country and city_name == user_city:
                    user_rate = rate

        results.sort(key=lambda x: x["rate"], reverse=True)
        # 过滤：只保留高于用户城市的
        better = [r for r in results if r["rate"] > user_rate + 2 and not (r["country"]==user_country and r["city"]==user_city)]
        return better[:8]

    def _simulate_all(self, profile, plan, base, ind, city, country, research):
        strategies = self.bm.get("strategy_types", {})
        methods = self._load_methods()
        paths = []
        for sk, si in strategies.items():
            ms = self._pick_methods(methods, sk)
            p = self._sim_one(sk, si, ms, profile, plan, base, ind, city, country, research)
            paths.append(p)
        paths.sort(key=lambda x: x.success_rate, reverse=True)
        return paths

    def _sim_one(self, sk, si, ms, profile, plan, base, ind, city, country, research):
        smod = sum(m.success_mod for m in ms)/max(len(ms),1)
        spd = sum(m.speed for m in ms)/max(len(ms),1)
        risks = [m.risk for m in ms]
        samples = [max(1,min(99,base*smod+random.gauss(0,4))) for _ in range(60)]
        rate = sum(samples)/len(samples)
        base_m = ind.get("avg_time_months",18)
        time_m = max(4, int(base_m/spd))
        cap = int(ind.get("avg_capital",2000000)*city.get("living",0.7)*1.5)
        risk_lv = "critical" if "critical" in risks else "high" if "high" in risks else "low"
        hidden = self._hidden(profile, ind, city, country)
        tml = self._timeline(profile, plan, city, country, rate, ind)
        nar = self._narrate(profile, sk, ms, rate, city, country, ind)
        return PathResult(sk,si.get("name",sk),si.get("legality",""),ms,rate,risk_lv,time_m,cap,si.get("warnings",[])+hidden,tml,nar)

    def _load_methods(self):
        all_m = []
        for ck, cv in self.md.get("categories",{}).items():
            for m in cv.get("methods",[]):
                all_m.append(type('M',(),{"name":m["name"],"category":cv["label"],"risk":m["risk"],"speed":m["speed"],"success_mod":m["success_mod"],"desc":m["desc"]})())
        return all_m

    def _pick_methods(self, methods, sk):
        if sk=="conservative": return [m for m in methods if m.category=="主流方法" and m.risk=="low"][:3]
        if sk=="aggressive": return [m for m in methods if m.risk in ("low","medium")][2:5]
        if sk=="gray": return [m for m in methods if m.category in ("灰色地带","漏洞利用")][:3]
        return [m for m in methods if m.category in ("漏洞利用","不道德但存在的方法")][:3]

    def _hidden(self, profile, ind, city, country) -> list:
        r = []
        cap = profile.get("capital",0)
        team = profile.get("team_size",1)
        city_n = profile.get("city","")
        if country=="中国" and city_n=="北京" and ind.get("failure_reasons",{}).get("监管政策",0)>20:
            r.append(f"北京是政策监管第一站——{profile.get('industry','该行业')}属重点监管领域，政策突变风险是其他城市的2-3倍")
        if cap<2000000 and city_n in ["北京","上海","深圳","旧金山/硅谷","纽约","伦敦","东京"]:
            r.append(f"你的资金在{city_n}仅够维持6-8个月，而本地平均融资周期是9-12个月——存在3-4个月的「死亡谷」")
        if team<=3:
            r.append("单人/小团队的最大风险：你生病/出意外/家庭变故→项目瞬间停摆，没有冗余")
        if country=="日本" and profile.get("experience","") in ["首次创业","1-3年行业经验"]:
            r.append("日本社会对创业失败容忍度极低，一次失败可能影响终身职业声誉")
        if country=="英国" and city_n=="伦敦":
            r.append("脱欧后伦敦的金融科技人才面临签证/工作权不确定，尤其是非英籍创始人")
        return r

    def _timeline(self, profile, plan, city, country, rate, ind):
        from core.timeline import TimelineEngine
        te = TimelineEngine()
        return te.project(profile.get("idea",""), profile, plan, "conservative", [{"name":"精益创业","risk":"low","speed":1.0,"success_mod":1.3,"desc":""}])

    def _narrate(self, profile, sk, methods, rate, city, country, ind):
        city_n = profile.get("city","这个城市")
        country_n = profile.get("country","这个国家")
        mn = "、".join(m.name for m in methods[:2])
        cap = self._fmt(profile.get("capital",0))
        if rate>=50:
            o=f"在{country_n}{city_n}采用「{mn}」方式，有较大概率在{ind.get('avg_time_months',18)}个月内实现稳定盈利。{city_n}的产业链和人才池会给你的项目提供关键支撑。"
        elif rate>=30:
            o=f"在{country_n}{city_n}有中等概率存活，但需要在6-12个月窗口期完成至少一轮融资。{city_n}的竞争环境会加速淘汰弱者。建议准备至少{self._fmt(int(profile.get('capital',0)*3))}的备用资金。"
        elif rate>=15:
            o=f"在{country_n}{city_n}实现这个想法非常艰难。当前条件(资金{cap}/团队{profile.get('team_size',1)}人/经验{profile.get('experience','')})不足以支撑。建议：1)增加至少5倍资金 2)招募有经验的合伙人 3)考虑成本更低的城市。"
        else:
            o=f"在{country_n}{city_n}以当前条件几乎不可能实现。建议放弃这个方向，或者先在{ind.get('failure_reasons',{}).get(next(iter(ind.get('failure_reasons',{})),''),'该行业')}方面积累5年以上经验。"
        return o

    def _apply_profile(self, profile, baseline, city, country) -> float:
        r = baseline
        cap, team, exp = profile.get("capital",0), profile.get("team_size",1), profile.get("experience","")
        adj = self.bm.get("capital_adjustments",{})
        if cap<500000: r*=adj.get("0-500k",0.5)
        elif cap<2000000: r*=adj.get("500k-2m",0.7)
        elif cap<10000000: r*=adj.get("2m-10m",1.0)
        elif cap<50000000: r*=adj.get("10m-50m",1.3)
        else: r*=adj.get("50m+",1.6)
        adj2 = self.bm.get("team_adjustments",{})
        if team<=1: r*=adj2.get("solo",0.4)
        elif team<=5: r*=adj2.get("2-5人",0.65)
        elif team<=20: r*=adj2.get("5-20人",1.0)
        elif team<=50: r*=adj2.get("20-50人",1.25)
        else: r*=adj2.get("50人+",1.5)
        adj3 = self.bm.get("experience_adjustments",{})
        r*=adj3.get(exp,1.0)
        em = {"高中及以下":0.85,"大专":0.9,"本科":1.0,"硕士":1.1,"博士":1.15}
        r*=em.get(profile.get("education","本科"),1.0)
        r*=city.get("success_mod",1.0)
        # 国家级调整
        if country=="美国": r*=1.08
        elif country=="英国": r*=1.02
        elif country=="日本": r*=0.92
        return round(r,1)

    def _match_industry(self, name: str) -> dict:
        ind = self.bm.get("industries",{})
        for k,v in ind.items():
            if name in k or k in name: return v
        kw = {"ai":"AI与大模型","人工":"AI与大模型","大模型":"AI与大模型","机器学习":"AI与大模型","saas":"企业服务SaaS","软件":"企业服务SaaS","企业服务":"企业服务SaaS","工具":"企业服务SaaS","电商":"电商与新零售","零售":"电商与新零售","交易":"电商与新零售","教育":"教育科技","培训":"教育科技","医疗":"医疗健康","健康":"医疗健康","药":"医疗健康","医院":"医疗健康","金融":"金融科技","支付":"金融科技","理财":"金融科技","游戏":"游戏娱乐","娱乐":"游戏娱乐","本地":"本地生活服务","生活":"本地生活服务","外卖":"本地生活服务","硬件":"硬件制造","制造":"硬件制造","设备":"硬件制造","新能源":"环保新能源","环保":"环保新能源","电池":"环保新能源","光伏":"环保新能源","自媒体":"自媒体与内容创作","短视频":"自媒体与内容创作","内容":"自媒体与内容创作","直播":"自媒体与内容创作","半导体":"半导体与芯片","芯片":"半导体与芯片","自动驾驶":"自动驾驶与出行","无人驾驶":"自动驾驶与出行","生物":"生物科技","基因":"个性化医疗/基因检测","航天":"航天与卫星","卫星":"航天与卫星","量子":"量子计算","vr":"虚拟现实VR/AR","ar":"虚拟现实VR/AR","虚拟现实":"虚拟现实VR/AR","区块链":"区块链与Web3","web3":"区块链与Web3","加密":"区块链与Web3","安全":"网络安全","网安":"网络安全","物流":"物流与供应链","供应链":"物流与供应链","农业":"农业科技","种植":"农业科技","宠物":"宠物经济","猫":"宠物经济","狗":"宠物经济","养老":"银发经济/养老","老年":"银发经济/养老","银发":"银发经济/养老","二手":"二手/循环经济","循环":"二手/循环经济","心理":"心理健康","抑郁":"心理健康","数字人":"数字人/虚拟偶像","虚拟人":"数字人/虚拟偶像","vtuber":"数字人/虚拟偶像","无人机":"低空经济/无人机","低空":"低空经济/无人机","氢":"氢能与储能","储能":"氢能与储能","机器人":"人形机器人","人形":"人形机器人","vision":"空间计算/苹果VisionPro生态","空间计算":"空间计算/苹果VisionPro生态","合成":"合成生物学","脑机":"脑机接口","碳":"碳交易/ESG咨询","esg":"碳交易/ESG咨询","在线教育":"在线教育/知识付费","知识付费":"在线教育/知识付费","智能家居":"智能家居/IoT","iot":"智能家居/IoT","充电桩":"新能源车/充电桩","新能源车":"新能源车/充电桩","电车":"新能源车/充电桩","跨境支付":"跨境支付/汇款","跨境":"跨境支付/汇款","数字孪生":"数字孪生/工业元宇宙","工业互联网":"数字孪生/工业元宇宙","元宇宙":"数字孪生/工业元宇宙"}
        for k,v in kw.items():
            if k in name.lower(): return ind.get(v,ind.get("企业服务SaaS",{}))
        return ind.get("企业服务SaaS",{})

    def _match_city(self, country: str, city: str) -> dict:
        cc = self.cd.get("countries", {}).get(country, {})
        if not cc: return {"success_mod": 0.8}
        # 搜索所有层级
        for region_key in ["provinces", "states", "regions"]:
            for region_name, region_data in cc.get(region_key, {}).items():
                cities = region_data.get("cities", {})
                if city in cities:
                    c = cities[city]
                    # 如果是紧凑格式(只有t,w,s),用省级平均值补全
                    if "sa" not in c:
                        avg = {k:v for k,v in region_data.items() if not k.startswith("_") and k not in ("cities","capital")}
                        c = {**c, "salary":avg.get("avg_sa",8000),"rent":avg.get("avg_r",50),
                             "talent":avg.get("avg_ta",0.3),"vc":avg.get("avg_vc",0.15),
                             "policy":avg.get("avg_po",0.6),"living":avg.get("avg_li",0.35),
                             "competition":avg.get("avg_co",0.3),
                             "advantages":c.get("ad",avg.get("ad",[])),
                             "disadvantages":c.get("da",avg.get("da",[])),
                             "best_industries":c.get("bi",avg.get("bi",[])),
                             "risks":c.get("ri",avg.get("ri",[]))}
                    return c
        return {"success_mod": 0.8}

    def _verdict(self, mr, rc):
        if mr>=50 and rc>0: return {"level":"recommended","text":f"可行。最优路径成功率 {mr:.1f}%。下方有跨国对比——可能有更适合的城市。","color":"green"}
        if mr>=35: return {"level":"risky","text":f"所有路径<50%。最优仅 {mr:.1f}%。建议调整(增资/扩团队/换城市)。下方有跨国对比参考。","color":"yellow"}
        if mr>=20: return {"level":"difficult","text":f"很难实现（最高 {mr:.1f}%）。建议增加5倍资金+10年经验合伙人+考虑成本更低的城市。","color":"orange"}
        return {"level":"not_recommended","text":f"几乎不可能（最高 {mr:.1f}%）。建议放弃或先在行业内积累5年以上。","color":"red"}

    def _fmt(self, n): return f"{n/10000:.0f}万" if n>=10000 else str(n)

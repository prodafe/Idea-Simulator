"""v10 千亿级推演引擎 — 精度优化版"""

import json, logging, random, time, re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)
from core.accuracy_engine import AccuracyEngine
from core.constraint_engine import ConstraintEngine

DATA = Path(__file__).parent.parent / "data"

def _load(f): return json.loads((DATA/f).read_text(encoding="utf-8")) if (DATA/f).exists() else {}

_SC = _load("scenarios.json")
_BM = _load("benchmarks.json")
_CD = _load("city_data.json")
_PL = _load("policies.json")
_BR = _load("burn_rates.json")
_HC = _load("historical_cases.json")
_ST = _load("seasonal_talent.json")

MACRO = {m["name"]:m for m in _SC.get("macro_scenarios",[])}
SHIFTS = _SC.get("industry_shifts",[])
TRAITS = _SC.get("personality_traits",[])
PERSONAS = _SC.get("personas",[])
FRINGE = _SC.get("fringe_methods",[])
BUTTERFLY = _SC.get("butterfly_effects",[])

@dataclass
class SimRun:
    iteration:int; base_rate:float; macro_events:list; persona:str; trait:str
    luck:float; timing:float; shift:str; fringe_method:str; butterfly:str
    final_rate:float; outcome:str; narrative:str

class DeepSimulator:
    def __init__(self, iterations=20000):
        self.iterations=iterations; self.history=[]

    def simulate(self, idea:str, profile:dict)->dict:
        t0=time.perf_counter(); self.history=[]
        industry=profile.get("industry","")
        fringe_mode=profile.get("fringe_mode",False)
        butterfly_on=profile.get("butterfly_on",True)
        country=profile.get("country","中国"); city_name=profile.get("city","北京")
        city=self._city(country,city_name)
        ind=self._industry(industry)
        base=ind.get("baseline_success_rate",10)
        base=self._adjust(base,profile,city)
        extreme_mod=profile.get("extreme_mod",0)
        if extreme_mod:base=max(1,base*(1+extreme_mod))
        extreme_events=profile.get("extreme_events",[])

        # ── 纯偏锋模式 ──
        if fringe_mode:
            base=max(2,base*0.4)
            personas=[p for p in PERSONAS if p.get("fringe") or p.get("cat")=="冷门"]
            traits=[t for t in TRAITS if t.get("fringe") or t.get("cat")in("特殊","运气","心理")]
            fringe_list=FRINGE[:]; fringe_prob=0.35
            relevant_shifts=[s for s in SHIFTS if s.get("bonus",0)<0 or s.get("absurd")]or SHIFTS
            relevant_macro=[]
            for m in MACRO.values():
                if m.get("absurd")or abs(m.get("impact",0))>0.3:
                    mc=dict(m);mc["prob"]=min(0.65,m.get("prob",0.05)*10)
                    relevant_macro.append(mc)
                else:
                    relevant_macro.append(m)
            if not relevant_macro:relevant_macro=list(MACRO.values())
        else:
            personas=[p for p in PERSONAS if not p.get("fringe")]
            traits=[t for t in TRAITS if not t.get("fringe")]
            fringe_list,fringe_prob=[],0
            relevant_shifts=[s for s in SHIFTS if industry in s.get("industries",[])]or SHIFTS[:5]
            # ✅ 行业事件优先+模糊匹配+排除荒谬/投影事件（标准模式不需要科幻场景）
            industry_macros=[]
            for m in MACRO.values():
                inds=m.get("industries",[])
                if not inds:continue
                if m.get("absurd"):continue          # 排除荒谬事件(平行宇宙等)
                if "[投影]" in m.get("name",""):continue  # 排除投影事件(保留真实锚定)
                if industry in inds or any(industry in i or i in industry for i in inds):
                    industry_macros.append(m)
            generic_macros=[m for m in MACRO.values() if not m.get("industries") and not m.get("absurd") and "[投影]" not in m.get("name","")]
            generic_macros.sort(key=lambda x:abs(x.get("impact",0)),reverse=True)
            relevant_macro=industry_macros+generic_macros[:30]
            if not relevant_macro:relevant_macro=[m for m in MACRO.values() if not m.get("absurd")][:20]

        # ✅ 行业事件名集合(用于概率加成+排序)
        industry_event_names={m["name"] for m in industry_macros} if not fringe_mode else set()

        # ── 新增预计算 ──
        burn_data=self._calc_burn(profile,industry,country,city_name)
        historical_match=self._match_historical(idea,industry)
        seasonal_mod=self._seasonal_modifier(industry)
        exit_scenarios=self._exit_scenarios(industry,base)
        sensitivity=self._sensitivity(profile,industry,base,city)

        # ── 蒙特卡洛 v10: 幂律分布+相关性 ──
        ae=AccuracyEngine();ce=ConstraintEngine();fact=ae.fact_anchor(profile)
        constraint=ce.analyze(profile);cmod=constraint.get("total_constraint_modifier",0)
        base=base*(1+cmod*0.4)
        buckets={"success":0,"failure":0,"struggle":0}
        all_rates=[]; event_impact={}
        for i in range(self.iterations):
            rate=base*(0.5+0.5*ae.power_law_sample(base/100))
            active_macro=[]
            for m in relevant_macro:
                prob=m.get("prob",0.1)
                if fringe_mode and m.get("absurd"):prob=min(0.65,prob*10)
                # 行业相关事件概率加成30%
                if m["name"] in industry_event_names:prob=min(0.55,prob*1.3)
                if random.random()<prob:
                    rate*=(1+m.get("impact",0))
                    active_macro.append(m["name"])
                    event_impact.setdefault(m["name"],[]).append(m.get("impact",0))
                    rate=ae.apply_correlation(m["name"],rate)

            shift=random.choice(relevant_shifts) if random.random()<0.22 else None
            sn=shift["name"] if shift else ""
            if shift:rate*=(1+shift.get("bonus",0))

            p=random.choice(personas)if personas else{"name":"标准","boost":0}
            t=random.choice(traits)if traits else{"name":"正常","boost":0}
            luck=random.gauss(0,0.22 if fringe_mode else 0.15)

            fm_name=""
            if fringe_list and random.random()<fringe_prob:
                fm=random.choice(fringe_list)
                rate*=(1+fm.get("boost",0)); fm_name=fm["name"]
                if random.random()<fm.get("fail_boost",0.3):rate*=(1-fm.get("fail_boost",0.3))

            rate*=(1+t.get("boost",0)+p.get("boost",0)+luck)
            rate*=(1+random.gauss(0,0.15 if fringe_mode else 0.12))
            rate*=(1+random.gauss(0,0.12 if fringe_mode else 0.08))
            rate*=(1+random.gauss(0,city.get("competition",0.5)*0.15))

            # 政策
            rate*=(1+self._policy_impact(country,city_name,industry))

            # 季节/时机效应
            rate*=(1+seasonal_mod+random.gauss(0,0.02))

            # 人才市场压力
            talent_pressure=self._talent_pressure(industry,country,city_name)
            rate*=(1-random.uniform(0,talent_pressure*0.05))

            # 蝴蝶
            bf_name=""
            if butterfly_on and BUTTERFLY and random.random()<0.06:
                bf=random.choice(BUTTERFLY)
                rate*=(1+bf.get("boost",0)); bf_name=bf.get("name","")
                if bf.get("fringe")and not fringe_mode:rate=max(0.02,rate*0.35)

            rate=max(0.02,min(99.98,rate))
            outcome="success"if rate>=50 else"struggle"if rate>=25 else"failure"
            buckets[outcome]+=1; all_rates.append(rate)

            narrative=""
            if i%150==0 or rate>=60 or rate<2:
                narrative=self._narrate(profile,active_macro,sn,p,t,fm_name,bf_name,rate,outcome)

            self.history.append(SimRun(i,base,active_macro,p.get("name",""),t.get("name",""),round(luck,3),0,sn,fm_name,bf_name,round(rate,1),outcome,narrative))

        # ── 统计 ──
        all_rates.sort();n=len(all_rates)
        spct=buckets["success"]/n*100
        cond=[];
        for ev,imps in event_impact.items():
            if len(imps)<5:continue
            cr=base*(1+sum(imps)/len(imps))
            is_industry=ev in industry_event_names
            cond.append({"event":ev,"base_rate":round(base,1),"conditional_rate":round(max(0.02,min(99.98,cr)),1),"change":round(cr-base,1),"probability":round(len(imps)/n*100,1),"industry_relevant":is_industry})
        # ✅ 排序: 行业相关事件优先，再按影响度降序
        cond.sort(key=lambda x:(not x.get("industry_relevant",False), -abs(x["change"])))

        best=max(self.history,key=lambda r:r.final_rate)
        worst=min(self.history,key=lambda r:r.final_rate)

        return{
            "iterations":n,"base_rate":round(base,1),"success_probability":round(spct,1),
            "mode":"偏锋"if fringe_mode else"标准","butterfly_on":butterfly_on,
            "total_scenarios":{"macro":len(relevant_macro),"shifts":len(relevant_shifts),"traits":len(traits),"personas":len(personas),"butterfly":len(BUTTERFLY)if butterfly_on else 0,"total_combos":min(len(relevant_macro)*len(relevant_shifts)*len(traits)*len(personas)*n, 2_000_000_000)},
            "stats":{"p10":round(all_rates[n//10],1),"p50":round(all_rates[n//2],1),"p90":round(all_rates[int(n*0.9)],1),"mean":round(sum(all_rates)/n,1),"min":round(all_rates[0],1),"max":round(all_rates[-1],1),"success":buckets["success"],"struggle":buckets["struggle"],"failure":buckets["failure"]},
            "conditional_probabilities":cond[:15],
            "best_case":{"rate":best.final_rate,"persona":best.persona,"trait":best.trait,"events":best.macro_events[:3],"butterfly":best.butterfly,"fringe":best.fringe_method},
            "worst_case":{"rate":worst.final_rate,"persona":worst.persona,"trait":worst.trait,"events":worst.macro_events[:3],"butterfly":worst.butterfly,"fringe":worst.fringe_method},
            "sample_narratives":[r.narrative for r in self.history if r.narrative and r.outcome in("success","failure")][:8],
            "butterfly_samples":[r.butterfly for r in self.history if r.butterfly][:10],
            # New engines
            "burn_rate":burn_data,
            "historical_match":historical_match,
            "seasonal_modifier":round(seasonal_mod,3),
            "exit_scenarios":exit_scenarios,
            "talent_pressure":round(talent_pressure,3),
            "sensitivity":sensitivity,
            "back_test":ae.back_test(spct,industry,profile),
            "fact_anchors":fact.get("anchors",[]),
            "suggested_range":fact.get("suggested_range",{}),
            "constraint_analysis":constraint,
            "constraint_modifier":round(cmod,3),
            "extreme_events":extreme_events,
            "extreme_mod":extreme_mod,
            "total_time_ms":round((time.perf_counter()-t0)*1000),
        }

    # ── 新引擎1: 烧钱计算器 ──
    def _calc_burn(self,profile,industry,country,city_name)->dict:
        team=profile.get("team_size",5)
        capital=profile.get("capital",1000000)
        cb=_BR.get("city_burn",{}).get(city_name,_BR["city_burn"].get("default",{}))
        tm=_BR.get("team_size_multipliers",{})
        mult=1.0
        def _team_sort_key(k):
            digits=''.join(filter(str.isdigit,str(k)))
            return int(digits) if digits else 99
        for k in sorted(tm.keys(),key=_team_sort_key):
            digits=''.join(filter(str.isdigit,str(k)))
            threshold=int(digits) if digits else 0
            if team>=threshold:
                mult=tm[k]
        monthly_burn=int((cb.get("burn_5p_team",70000)/5*team)*mult)
        extra=_BR.get("extra_costs",{}).get(industry,_BR["extra_costs"].get("default",{}))
        extra_cost=sum(v for k,v in extra.items() if isinstance(v,(int,float)))
        monthly_burn+=int(extra_cost)
        runway_months=int(capital/monthly_burn)if monthly_burn>0 else 99
        death_date=f"{runway_months}个月后资金断裂"if runway_months<24 else"资金充足"
        return{"monthly_burn":monthly_burn,"runway_months":runway_months,"death_date":death_date,"extra_costs":{k:v for k,v in extra.items() if isinstance(v,(int,float))}}

    # ── 新引擎2: 历史对标 ──
    def _match_historical(self,idea,industry)->list:
        cases=_HC.get("cases",[])
        matches=[]
        idea_lower=idea.lower()
        for c in cases:
            score=0
            if industry and industry in c.get("industry",""):score+=3
            for kw in c.get("lesson","").split("。"):
                if any(w in idea_lower for w in kw[:6]):score+=2
            if c.get("outcome")=="失败"and any(w in idea_lower for w in["轻资产","平台","共享","社区"]):score+=1
            if score>=2:matches.append({"company":c["company"],"year":c["year"],"outcome":c["outcome"],"lesson":c["lesson"],"relevance":score})
        matches.sort(key=lambda x:-x["relevance"])
        return matches[:5]

    # ── 新引擎3: 退出场景 ──
    def _exit_scenarios(self,industry,base_rate)->dict:
        if base_rate>=20:ipo=random.uniform(0.03,0.12)
        elif base_rate>=10:ipo=random.uniform(0.01,0.05)
        else:ipo=random.uniform(0,0.02)
        acquire=min(0.35,ipo*3+random.uniform(0.05,0.15))
        liquidate=1-ipo-acquire
        return{"ipo_prob":round(ipo*100,1),"acquire_prob":round(acquire*100,1),"liquidate_prob":round(liquidate*100,1),"typical_valuation_if_ipo":f"{int(base_rate*50)}M-{int(base_rate*200)}M USD","typical_acquisition_price":f"{int(base_rate*8)}M-{int(base_rate*30)}M USD"}

    # ── 新引擎4: 季节效应 ──
    def _seasonal_modifier(self,industry)->float:
        se=_ST.get("seasonal_effects",{})
        m=0
        for k,v in se.items():
            if not v.get("industries")or industry in v["industries"]:
                if random.random()<0.5:m+=v.get("modifier",0)*0.5
        return max(-0.08,min(0.08,m))

    # ── 新引擎5: 人才市场 ──
    def _talent_pressure(self,industry,country,city_name)->float:
        tm=_ST.get("talent_market",{})
        roles=tm.get("roles",{})
        pressure=0;count=0
        for role,data in roles.items():
            if industry in["AI与大模型","自动驾驶","量子计算"]and"AI"in role:pressure+=data.get("hire_difficulty",0.5);count+=1
            if industry in["SaaS","电商","自媒体"]and role in["全栈开发","产品经理"]:pressure+=data.get("hire_difficulty",0.5);count+=1
        if count==0:pressure,count=0.5,1
        city_prem=tm.get("city_premium",{}).get(city_name,0.8)
        return(pressure/count)*city_prem

    # ── 新引擎6: 敏感度分析 ──
    def _sensitivity(self,profile,industry,base,city)->list:
        results=[]
        cap=profile.get("capital",1000000)
        for multiplier,label in[(0.5,"资金减半"),(2,"资金翻倍"),(5,"5倍资金"),(10,"10倍资金")]:
            new_cap=int(cap*multiplier)
            p2=dict(profile);p2["capital"]=new_cap
            new_rate=self._adjust(base,p2,city)
            results.append({"scenario":label,"capital":new_cap,"rate":round(new_rate,1),"change":round(new_rate-base,1)})
        # 时间敏感度
        for delay,label in[(3,"晚3个月"),(6,"晚6个月"),(12,"晚1年")]:
            decay=0.92**(delay/3)
            results.append({"scenario":label,"rate":round(base*decay,1),"change":round(base*decay-base,1)})
        for advance,label in[(-3,"早3个月"),(-6,"早6个月")]:
            boost=1.08**(-advance/3)
            results.append({"scenario":label,"rate":round(base*boost,1),"change":round(base*boost-base,1)})
        # 城市变化
        for cname,crate in[("旧金山/硅谷",1.25),("深圳",1.18),("成都",0.95),("东京",0.92)]:
            p3=dict(profile);p3["city"]=cname
            c2=self._city("美国"if cname=="旧金山/硅谷"else"日本"if cname=="东京"else"中国",cname)
            nr=self._adjust(base,p3,c2)
            results.append({"scenario":f"搬到{cname}","rate":round(nr,1),"change":round(nr-base,1)})
        return results[:12]

    def _narrate(self,profile,macros,shift,persona,trait,fringe,butterfly,rate,outcome):
        loc=f"{profile.get('country','')}{profile.get('city','')}"
        m="、".join(macros[:2])or"平稳"
        bf=f"，蝴蝶: {butterfly}"if butterfly else""
        fr=f"，手段: {fringe}"if fringe else""
        sh=f"，变革: {shift}"if shift else""
        who=f"{persona.get('name','你')}({trait.get('name','')})"if isinstance(persona,dict)else"你"
        if outcome=="success":return f"{loc}，{m}{sh},{who}{fr}{bf}→成功({rate:.1f}%)"
        if outcome=="failure":return f"{loc}，{m}{sh},{who}{fr}{bf}→失败({rate:.1f}%)"
        return f"{loc}，{m}{sh},{who}{fr}{bf}→挣扎({rate:.1f}%)"

    def _policy_impact(self,country,city,industry):
        impact=0.0
        cd=_PL.get("countries",{}).get(country,{})
        if not cd:return 0.0
        for p in cd.get("national_policies",[]):
            af=p.get("affected",[])
            if not af or industry in af or"所有行业"in af:
                pi=p.get("impact","")
                if any(w in pi for w in["受益","加速","改善","支持"]):impact+=0.01
                elif any(w in pi for w in["受限","增加","门槛","合规"]):impact-=0.01
                elif any(w in pi for w in["禁止","严格"]):impact-=0.02
        for p in cd.get("city_specific",{}).get(city,[]):
            if any(w in p.get("impact","")for w in["受益","补贴","试点","先行"]):impact+=0.02
        ir=_PL.get("industry_regulations",{}).get(industry,{})
        cr=ir.get(country,"")
        if any(w in cr for w in["禁止","严格"]):impact-=0.03
        elif any(w in cr for w in["宽松","灵活"]):impact+=0.01
        return max(-0.15,min(0.15,impact))

    def _adjust(self,base,profile,city):
        r=base;cap=profile.get("capital",0);team=profile.get("team_size",1)
        ca=_BM.get("capital_adjustments",{})
        if cap<500000:r*=ca.get("0-500k",0.5)
        elif cap<2000000:r*=ca.get("500k-2m",0.7)
        elif cap<10000000:r*=ca.get("2m-10m",1.0)
        elif cap<50000000:r*=ca.get("10m-50m",1.3)
        else:r*=ca.get("50m+",1.6)
        ta=_BM.get("team_adjustments",{})
        if team<=1:r*=ta.get("solo",0.4)
        elif team<=5:r*=ta.get("2-5人",0.65)
        elif team<=20:r*=ta.get("5-20人",1.0)
        elif team<=50:r*=ta.get("20-50人",1.25)
        else:r*=ta.get("50人+",1.5)
        r*=_BM.get("experience_adjustments",{}).get(profile.get("experience",""),1.0)
        r*={"高中及以下":0.85,"大专":0.9,"本科":1.0,"硕士":1.1,"博士":1.15}.get(profile.get("education","本科"),1.0)
        r*=city.get("success_mod",1.0)
        if profile.get("country")=="美国":r*=1.08
        elif profile.get("country")=="英国":r*=1.02
        elif profile.get("country")=="日本":r*=0.92
        return r

    def _industry(self,name):
        ind=_BM.get("industries",{})
        for k,v in ind.items():
            if name in k or k in name:return v
        logger.debug(f"Industry '{name}' not found, using default")
        return ind.get("企业服务SaaS",{"baseline_success_rate":10})

    def _city(self,country,city):
        cc=_CD.get("countries",{}).get(country,{})
        for rk in["provinces","states","regions"]:
            for rn,rd in cc.get(rk,{}).items():
                if city in rd.get("cities",{}):
                    c=rd["cities"][city]
                    return{"success_mod":c.get("s",c.get("success_mod",0.8)),"competition":c.get("co",c.get("competition",0.5))}
        return{"success_mod":0.8,"competition":0.5}

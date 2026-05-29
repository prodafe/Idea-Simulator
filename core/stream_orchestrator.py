"""v14 多Agent流式推演 — 统一LLM + SSE"""

import json, logging, re, time, random, concurrent.futures
from pathlib import Path
from config import Config
from core.llm_provider import call_llm, validate_key
from core.governance import GovernanceLayer

logger = logging.getLogger(__name__)
DATA = Path(__file__).parent.parent / "data"


class StreamOrchestrator:
    """多Agent流式推演编排器 — 每个阶段yield进度"""

    def __init__(self):
        self.bm = self._j("benchmarks.json")
        self.cd = self._j("city_data.json")
        self.md = self._j("methods.json")
        self.governance = None  # 延迟初始化(需要LLM函数)

    def _j(self, f): return json.loads((DATA / f).read_text(encoding="utf-8")) if (DATA / f).exists() else {}

    def _llm(self, prompt: str, max_tokens: int = 500) -> str:
        """统一LLM调用 — 使用实例属性(线程安全)"""
        proxy = getattr(Config,"HTTPS_PROXY","") or getattr(Config,"HTTP_PROXY","")
        return call_llm(
            prompt,
            getattr(self,"_model", getattr(Config,"LLM_MODEL","gpt-4o-mini")),
            getattr(self,"_api_key", ""),
            max_tokens,
            getattr(self,"_base_url", ""),
            getattr(Config,"VERIFY_SSL",True),
            proxy,
            getattr(Config,"LLM_TIMEOUT",60)
        )

    # ─── Agent 0: Scenario Classifier (NEW — 场景自适应分类) ───
    def classify_scenario(self, idea: str, profile: dict) -> dict:
        """LLM识别场景类型+估算基准成功率+关键风险因素"""
        prompt = f"""你是一个现实世界概率分析师。分析以下场景，判断类型并估算基准成功率。

场景描述：{idea}
用户背景：{json.dumps(profile, ensure_ascii=False)[:400]}

步骤1: 判断场景类型（严格从下面选一个）：
- daily_life: 日常行为（扔垃圾、买菜、取快递等几乎必成的事）
- career_job: 求职应聘
- career_promotion: 晋升/跳槽/薪资谈判
- business_startup: 创业/开公司/新项目
- business_operation: 经营中的决策（定价、扩张、裁员等）
- investment: 投资理财
- negotiation: 谈判/签约
- relocation: 搬家/移民/换城市
- education: 考试/申请学校
- legal: 法律事务
- health: 健康/医疗
- other: 其他不明确场景

步骤2: 估算基准成功率。必须基于真实世界数据，不能拍脑袋：
- 日常小事：95-99.9%（几乎一定成功）
- 求职（强背景）：30-60%（取决于匹配度）
- 求职（弱背景）：5-20%
- 创业：8-25%（全球创业存活率约10-20%）
- 投资（保守）：40-70%
- 投资（激进）：10-30%
- 搬家/移民：70-95%
- 考试（准备充分）：60-90%
- 法律事务：40-80%（取决于案情）

步骤3: 列出3-5个影响此场景的核心因素（正面+负面），每个含name/direction/magnitude/reason。

只输出JSON：
{{"scenario_type":"daily_life","baseline_rate":99.5,"key_factors":[{{"name":"几乎无阻碍","direction":"positive","magnitude":0.0,"reason":"日常琐事极少有失败可能"}}]}}
JSON:"""
        try:
            text = self._llm(prompt, 600)
            s = text.find("{"); e = text.rfind("}")+1
            if s>=0 and e>s:
                result = json.loads(text[s:e])
                result["baseline_rate"] = max(0.5, min(99.5, float(result.get("baseline_rate",50))))
                # ✅ 自我一致性校验：用保守视角再问一次，偏差>15pp则取均值+标记
                verify_prompt = f"""What is a conservative lower-bound success rate (0-100) for this scenario? Output ONLY the number.
Scenario: {idea}
Background: {json.dumps(profile, ensure_ascii=False)[:150]}
Number:"""
                try:
                    vt = self._llm(verify_prompt, 100)
                    nums = re.findall(r'(\d+\.?\d*)', str(vt))
                    if nums:
                        conservative = float(nums[0])
                        optimistic = result["baseline_rate"]
                        gap = abs(optimistic - conservative)
                        if gap > 15:
                            avg = (optimistic + conservative) / 2
                            result["baseline_rate"] = round(avg, 1)
                            result["self_consistency"] = {"optimistic": optimistic, "conservative": conservative, "gap": round(gap,1), "used_average": True}
                        else:
                            result["self_consistency"] = {"optimistic": optimistic, "conservative": conservative, "gap": round(gap,1), "used_average": False}
                except Exception:
                    result["self_consistency"] = {"skipped": True}
                return result
        except Exception:
            pass
        return {"scenario_type":"other","baseline_rate":50.0,"key_factors":[]}
    def agent_context(self, idea: str, profile: dict) -> dict:
        """分析用户背景和想法的匹配度"""
        prompt = f"""分析以下创业者的背景与想法的匹配度。输出JSON:{{"match_score":0-100,"strengths":[],"gaps":[],"advice":"一句话建议"}}
背景：{json.dumps(profile,ensure_ascii=False)}
想法：{idea}
JSON:"""
        try:
            text = self._llm(prompt, 300)
            s = text.find("{"); e = text.rfind("}")+1
            return json.loads(text[s:e]) if s>=0 and e>s else {}
        except Exception: return {"match_score":50,"strengths":[],"gaps":[],"advice":""}

    # ─── Agent 2: Market Analyst ───
    def agent_market(self, idea: str, profile: dict) -> dict:
        """分析市场规模和竞争格局"""
        ind = self._match_industry(profile.get("industry",""))
        city = self._match_city(profile.get("country","中国"), profile.get("city","北京"))
        prompt = f"""分析这个想法的市场前景。输出JSON:{{"market_size":"估算","growth_rate":"年增长率","competitors":["竞品"],"entry_barrier":"低/中/高","timing":"好/一般/差","analysis":"分析"}}
行业：{profile.get('industry','')}，基础成功率{ind.get('baseline_success_rate',10)}%
城市：{profile.get('city','')}，{profile.get('country','')}
想法：{idea}
JSON:"""
        try:
            text = self._llm(prompt, 400)
            s = text.find("{"); e = text.rfind("}")+1
            return json.loads(text[s:e]) if s>=0 and e>s else {}
        except Exception: return {"market_size":"未知","analysis":"分析失败"}

    # ─── Agent 3: Risk Assessor ───
    def agent_risk(self, idea: str, profile: dict) -> dict:
        """评估多维度风险"""
        prompt = f"""评估创业风险。输出JSON:{{"risks":[{{"name":"风险名","probability":"高/中/低","impact":"严重/中等/轻微","mitigation":"对策"}}],"overall_risk":"高/中/低","hidden_risks":["用户可能没意识到的风险"]}}
想法：{idea}
资金：{profile.get('capital',0)}元 团队：{profile.get('team_size',1)}人 城市：{profile.get('city','')}
JSON:"""
        try:
            text = self._llm(prompt, 500)
            s = text.find("{"); e = text.rfind("}")+1
            return json.loads(text[s:e]) if s>=0 and e>s else {}
        except Exception: return {"risks":[],"overall_risk":"中"}

    # ─── Agent 4: Strategy Planner ───
    def agent_strategy(self, idea: str, profile: dict, market: dict, risk: dict) -> dict:
        """生成4条策略路径的具体方案"""
        prompt = f"""基于以下分析，生成4条实现路径(保守/激进/灰色/投机)，每条包含具体步骤和预期结果。输出JSON:{{"strategies":[{{"name":"策略名","type":"conservative/aggressive/gray/speculative","steps":["步骤1"],"expected_outcome":"预期结果","time_months":12,"success_probability":50}}]}}
想法：{idea}  市场：{json.dumps(market,ensure_ascii=False)[:300]}  风险：{json.dumps(risk,ensure_ascii=False)[:300]}
JSON:"""
        try:
            text = self._llm(prompt, 800)
            s = text.find("{"); e = text.rfind("}")+1
            return json.loads(text[s:e]) if s>=0 and e>s else {}
        except Exception: return {"strategies":[]}

    # ─── Agent 5: Cross-Country Optimizer ───
    def agent_cross_country(self, idea: str, profile: dict) -> list:
        """跨国对比分析"""
        results = []
        ind = self._match_industry(profile.get("industry",""))
        baseline = ind.get("baseline_success_rate",10)
        user_country = profile.get("country","中国")
        user_city = profile.get("city","北京")
        user_rate = 0

        countries = self.cd.get("countries",{})
        for cname, cdata in countries.items():
            for rk in ["provinces","states","regions"]:
                for rn, rd in cdata.get(rk,{}).items():
                    for cn, ci in rd.get("cities",{}).items():
                        if cn in ("其他","その他"): continue
                        sm = ci.get("s", ci.get("success_mod",0.8))
                        p = dict(profile); p["country"]=cname; p["city"]=cn
                        rate = baseline * sm
                        if cname=="美国": rate*=1.08
                        elif cname=="英国": rate*=1.02
                        elif cname=="日本": rate*=0.92
                        rate = min(98, max(1, rate + random.uniform(-2,5)))
                        results.append({"country":cname,"city":cn,"rate":round(rate,1),"flag":cdata.get("flag","")})
                        if cname==user_country and cn==user_city: user_rate=rate

        results.sort(key=lambda x:x["rate"],reverse=True)
        return [r for r in results if r["rate"]>user_rate+2 and not(r["country"]==user_country and r["city"]==user_city)][:8]

    # ─── Agent 6: Final Reporter ───
    def agent_report(self, idea: str, profile: dict, all_agent_results: dict) -> str:
        """综合所有Agent结果+真实世界数据，生成结构化深度推演报告"""
        sc_type = profile.get("_scenario_type", "other")
        llm_baseline = profile.get("_llm_baseline", 50)
        key_factors = profile.get("_key_factors", [])
        deep_sim = all_agent_results.get("deep_sim", {})
        scenario_info = all_agent_results.get("scenario", {})
        ctx = json.dumps(all_agent_results, ensure_ascii=False)[:2500]

        # 提取治理层审查结果
        governance_info = all_agent_results.get("governance", {})
        governance_context = ""
        if governance_info and governance_info.get("governance_score", 0) > 0:
            gs = governance_info.get("governance_score", 0)
            gv = governance_info.get("verdict", "?")
            violations = governance_info.get("all_violations", [])
            critical_vs = [v for v in violations if v.get("severity") in ("critical", "high")]
            gov_verdict_cn = {"approve": "✅ 预测基本合理，可采纳", "warn": "⚠️ 存在重要违规，需修正后采纳", "reject": "🚫 预测严重偏离现实，不建议采纳"}
            mandatory_response = ""
            if critical_vs:
                mandatory_response = "\n\n【强制要求】你的报告必须包含一节「治理层审查回应」，逐条回应以下高优先级违规，说明是否认同、如认同则如何修正预测、如不认同则给出反驳依据：\n" + "\n".join(f"{i+1}. [{v['severity']}] {v['message']}" for i, v in enumerate(critical_vs[:5]))
            governance_context = f"""
🏛️ 宪法治理层审查结果:
- 综合治理得分: {gs}/100 — {gov_verdict_cn.get(gv, gv)}
- 违规项数: {len(violations)} (严重: {len(critical_vs)})
{mandatory_response}

请在报告中充分考虑治理层审查发现。如果治理层标记了违规，你必须要么接受并修正相应的预测数字，要么给出有说服力的反驳理由。
"""

        prompt = f"""你是全球顶级现实世界推演分析师。你的任务是对以下场景进行深度、细致、引用真实数据的推演分析。

{governance_context}
场景：{idea}
场景类型：{sc_type} | LLM估算基准成功率：{llm_baseline}%
用户背景：{json.dumps(profile, ensure_ascii=False)[:400]}
关键影响因素：{json.dumps(key_factors, ensure_ascii=False)}
蒙特卡洛推演数据：{json.dumps(deep_sim, ensure_ascii=False)[:600]}
多Agent分析：{ctx}

请按以下结构输出一份深度推演报告（用Markdown，中文，每个部分都要充实详尽）：

## 一、核心结论
- 明确给出判断（推荐/谨慎/不推荐）
- 综合成功率 XX%，解读这个数字意味着什么（对比同类型场景的真实世界数据）
- 最关键的2-3个决定因素是什么

## 二、成败原因深度拆解
针对该场景类型，从以下维度逐一分析（每个维度至少2句话，引用真实世界数据或逻辑推理）：
1. 个人条件匹配度——用户的背景/资源/能力与该场景要求的匹配程度
2. 外部环境因素——当前市场/社会/政策/竞争环境对该场景的影响
3. 时机与窗口——现在是否是最佳时机，如果延迟会怎样
4. 不可控风险——哪些因素用户无法控制，如何应对

## 三、真实世界对比
- 找2-3个类似的真实世界案例（可以是知名人物、公司、或统计趋势）
- 对比用户情况与这些案例的异同
- 从这些案例中能学到什么

## 四、分路径推演
（根据场景类型调整，不硬套"保守/激进"框架）
- 最优路径：成功概率最高的一条路，具体步骤和所需条件
- 最差路径：如果最坏情况发生会怎样，如何止损
- 推荐路径：当前条件下最优解

## 五、风险对冲与行动清单
- 5个可立即执行的具体行动（按优先级排序）
- 每个行动说明：为什么重要、预计效果、需要什么资源
- 如果失败率>50%，给出明确的替代方案或降级路径

注意：不要泛泛而谈，每个结论都要有依据。引用你掌握的全球真实数据和统计规律。如果场景是日常行为（扔垃圾等），要给出科学的概率分析而不是强行套商业框架。用中文输出完整报告。"""
        return self._llm(prompt, 2000) or "报告生成失败"

    # ─── 流式主流程 ───
    def _parse_extreme_profile(self, profile: dict) -> dict:
        """绝境模式v2：解析40+字段的完整身份信息"""
        import re
        p = dict(profile)
        events = []
        total_mod = 0.0

        # ── 年龄 ──
        age_raw = str(p.get("age","30"))
        m = re.search(r'(\d+)', age_raw)
        age = int(m.group(1)) if m else 30
        p["age_num"] = age
        if age < 18: total_mod -= 0.20; events.append(f"未成年({age}岁)→法律限制多,不能独立注册公司")
        elif age < 22: total_mod -= 0.10; events.append(f"太年轻({age}岁)→缺乏社会经验和人脉")
        elif age < 30: total_mod -= 0.03
        elif age < 40: total_mod += 0.05
        elif age < 50: total_mod += 0.02
        elif age < 60: total_mod -= 0.08; events.append(f"中年({age}岁)→体力下降但经验丰富")
        else: total_mod -= 0.18; events.append(f"年长({age}岁)→体力和学习能力下降,但阅历是最大武器")

        # ── 疾病 ──
        disease = str(p.get("disease","")) + str(p.get("physical","")) + str(p.get("mental",""))
        disease_lower = disease.lower()
        if any(w in disease_lower for w in ["癌症","肿瘤","化疗","放疗"]):
            total_mod -= 0.35; events.append("重大疾病治疗中→创业时间极度受限,但求生的意志可能创造奇迹")
        elif any(w in disease_lower for w in ["抑郁","抑郁症","重度抑郁"]):
            total_mod -= 0.20; events.append("抑郁症→在低谷中创业是双刃剑:极度的绝望可以转化为极度的专注")
        elif any(w in disease_lower for w in ["焦虑","焦虑症","PTSD","创伤"]):
            total_mod -= 0.12; events.append("焦虑/PTSD→风险感知过度敏感,但也会让你比常人更早发现危险")
        elif any(w in disease_lower for w in ["双相","躁郁","bipolar"]):
            total_mod -= 0.10; events.append("双相→亢奋期生产力爆表,抑郁期几乎无法工作,需要妥善管理")
        elif any(w in disease_lower for w in ["ADHD","多动","注意力"]):
            total_mod -= 0.05; events.append("ADHD→注意力分散但创造力强,适合需要快速切换的领域")
        elif any(w in disease_lower for w in ["自闭","ASD","孤独症","谱系"]):
            total_mod -= 0.08; events.append("ASD→社交困难,但深度专注力和模式识别能力远超常人")
        if any(w in disease_lower for w in ["糖尿","高血压","心脏","心血管"]):
            total_mod -= 0.10; events.append("慢性病→需要持续用药和定期检查,不能过度劳累")
        if any(w in disease_lower for w in ["乙肝","乙肝携带","HIV","艾滋","丙肝"]):
            total_mod -= 0.15; events.append("传染病/携带者→社会偏见可能影响合作,但法律保护你免受歧视")
        if any(w in disease_lower for w in ["腰椎","颈椎","椎间盘","腰突","腰痛"]):
            total_mod -= 0.08; events.append("脊椎问题→不能久坐/久站,需要特殊的工作环境")
        if any(w in disease_lower for w in ["失眠","睡眠呼吸","打鼾"]):
            total_mod -= 0.06; events.append("睡眠障碍→日间精力不足,判断力下降")
        if any(w in disease_lower for w in ["肥胖","超重"]):
            total_mod -= 0.03; events.append("体重问题→可能影响精力和自信心")
        if any(w in disease_lower for w in ["酗酒","酒精依赖","酒瘾"]):
            total_mod -= 0.18; events.append("酒精依赖→严重影响决策能力和人际关系")
        if any(w in disease_lower for w in ["戒毒","吸毒","药物依赖"]):
            total_mod -= 0.25; events.append("药物依赖史→社会信任度极低,但戒断成功说明意志力强大")

        # ── 残疾 ──
        disability = str(p.get("disability","")).lower()
        if any(w in disability for w in ["轮椅","瘫痪","截瘫"]):
            total_mod -= 0.25; events.append("轮椅使用者→需要无障碍环境,但远程工作消除了部分障碍")
        elif any(w in disability for w in ["失明","盲","视障","视力"]):
            total_mod -= 0.22; events.append("视力障碍→需要屏幕阅读器等辅助工具,但听觉和记忆力可能更强")
        elif any(w in disability for w in ["失聪","聋","听障","听力"]):
            total_mod -= 0.15; events.append("听力障碍→面对面交流受限,但文字沟通不受影响")
        elif any(w in disability for w in ["义肢","假肢","截肢"]):
            total_mod -= 0.15; events.append("肢体残疾→行动受限,但意志力可能远超常人")
        elif any(w in disability for w in ["口吃","结巴","语言"]):
            total_mod -= 0.05; events.append("语言障碍→pitch/销售受影响,但书面表达不受限")
        elif any(w in disability for w in ["色盲","色弱"]):
            total_mod -= 0.02; events.append("色觉异常→设计相关工作受限")

        # ── 前科/信用 ──
        criminal = str(p.get("criminal","")).lower()
        credit = str(p.get("credit","")).lower()
        restricted = str(p.get("restricted","")).lower()
        if any(w in criminal for w in ["盗窃","偷","抢劫","诈骗","伤害","杀人"]):
            total_mod -= 0.40; events.append("严重刑事前科→绝大多数行业和投资机构会拒绝,但社会企业/公益创业仍有机会")
        elif any(w in criminal for w in ["经济","贪污","受贿","挪用"]):
            total_mod -= 0.35; events.append("经济犯罪记录→金融/财会行业终身禁入,但其他领域仍可尝试")
        elif any(w in criminal for w in ["缓刑","假释","社区矫正"]):
            total_mod -= 0.30; events.append("正在服刑/矫正期→人身自由受限,但不能阻止你学习和准备")
        if any(w in credit for w in ["失信","老赖","黑名单"]):
            total_mod -= 0.25; events.append("失信被执行人→不能坐高铁飞机,不能贷款,不能注册公司担任法人")
        if any(w in restricted for w in ["限高","限消","冻结"]):
            total_mod -= 0.20; events.append("被限制高消费→出行/消费/注册严重受限")
        if any(w in criminal for w in ["行政拘留","治安","打架","酒驾"]):
            total_mod -= 0.08; events.append("轻微违法记录→影响有限,但需要诚实面对")

        # ── 债务 ──
        debt_raw = str(p.get("debt",""))
        debt_num = 0
        m = re.search(r'(\d+[\d,.]*)\s*[万亿]?', debt_raw.replace(',',''))
        if m:
            debt_num = float(m.group(1).replace(',',''))
            if '亿' in debt_raw: debt_num *= 100000000
            elif '万' in debt_raw: debt_num *= 10000
        if debt_num > 10000000: total_mod -= 0.40; events.append(f"巨额债务({debt_num/10000:.0f}万)→法律风险+心理压力双重打击")
        elif debt_num > 1000000: total_mod -= 0.30; events.append(f"大额债务({debt_num/10000:.0f}万)→严重影响决策自由度")
        elif debt_num > 100000: total_mod -= 0.18; events.append(f"中等债务({debt_num/10000:.0f}万)→需要尽快产生收入")
        elif debt_num > 10000: total_mod -= 0.08; events.append("小额债务→有一定压力但可承受")

        # ── 正向因素 ──
        skills_raw = str(p.get("skills","")) + str(p.get("certs","")) + str(p.get("career",""))
        if any(w in skills_raw for w in ["编程","代码","Python","Java","前端","后端","全栈","开发"]):
            total_mod += 0.15; events.append("编程技能→数字化时代最硬通货,任何行业都需要")
        if any(w in skills_raw for w in ["设计","UI","UX","PS","AI绘画","Figma"]):
            total_mod += 0.08; events.append("设计能力→产品/营销/品牌都需要")
        if any(w in skills_raw for w in ["销售","BD","谈判","客户"]):
            total_mod += 0.12; events.append("销售能力→任何生意的核心能力,有销售技能很难饿死")
        if any(w in skills_raw for w in ["会计","财务","CPA","CFA"]):
            total_mod += 0.08; events.append("财务技能→能管好钱的创业者活得更久")
        if any(w in skills_raw for w in ["开车","驾照","A照","B照","货车"]):
            total_mod += 0.05; events.append("驾驶技能→货运/物流/网约车都可以作为保底收入来源")
        if any(w in skills_raw for w in ["英语","日语","韩语","翻译"]):
            total_mod += 0.10; events.append("外语能力→跨境/外贸/翻译/教学均可变现")

        # ── 背水一战加分 ──
        crisis = str(p.get("goal","")) + str(p.get("bottom","")) + str(p.get("runway",""))
        if any(w in crisis for w in ["拼命","背水","没有退路","什么都","只要不","活下去"]):
            total_mod += 0.15; events.append("背水一战→没有退路的人,爆发力是最强的")

        # ── 资产加分 ──
        assets = str(p.get("assets","")).lower()
        if any(w in assets for w in ["房","车","铺","仓库"]):
            total_mod += 0.05; events.append("有固定资产→可以作为抵押或运营场所")

        # ── 家庭负担 ──
        family = str(p.get("family","")).lower()
        if any(w in family for w in ["孩子","小孩","宝宝","婴儿","孕","待产"]):
            total_mod -= 0.10; events.append("养育孩子→时间和资金被大幅分流")
        if any(w in family for w in ["赡养","父母","老人","病","照顾"]):
            total_mod -= 0.12; events.append("照顾家人→道德责任和经济负担双重压力")
        if any(w in family for w in ["配偶","妻子","丈夫","老公","老婆"]):
            if any(w in family for w in ["支持","理解","帮忙"]):
                total_mod += 0.08; events.append("家庭支持→最强大的精神后盾")
            elif any(w in family for w in ["反对","离婚","分居","争吵"]):
                total_mod -= 0.10; events.append("家庭矛盾→精神内耗严重影响创业")

        p["extreme_mod"] = max(-0.80, min(0.30, total_mod))
        p["extreme_events"] = events
        p["capital"] = max(100, int(debt_num) if debt_num > 0 else 10000)
        p["team_size"] = 1

        return p

    def _parse_profile(self, profile: dict) -> dict:
        """将用户自由文本解析为结构化数据"""
        import re
        p = dict(profile)

        # 解析资金
        cap_raw = p.get("capital_raw", "")
        if cap_raw:
            m = re.search(r'(\d+[\d,.]*)\s*[万亿]?', cap_raw.replace(',',''))
            if m:
                num = float(m.group(1).replace(',',''))
                if '亿' in cap_raw: num *= 100000000
                elif '万' in cap_raw: num *= 10000
                elif num < 1000: num *= 10000  # 默认万
                p["capital"] = int(num)
        if not p.get("capital"): p["capital"] = 1000000

        # 解析团队
        team_raw = p.get("team_raw", "")
        if team_raw:
            m = re.search(r'(\d+)', team_raw)
            if m: p["team_size"] = int(m.group(1))
            if '自己' in team_raw or '一个人' in team_raw or '独立' in team_raw: p["team_size"] = 1
            if '前同事' in team_raw: p["team_size"] = max(p.get("team_size",3), 3)
        if not p.get("team_size"): p["team_size"] = 3

        # 解析经验
        exp = p.get("experience", "")
        if exp:
            if re.search(r'(\d+)\s*年', exp):
                yrs = int(re.search(r'(\d+)\s*年', exp).group(1))
                if yrs >= 10: p["experience"] = "10年+行业经验"
                elif yrs >= 3: p["experience"] = "3-10年行业经验"
                elif yrs >= 1: p["experience"] = "1-3年行业经验"
            elif any(w in exp for w in ['首次','刚毕业','没有经验','应届','新手']): p["experience"] = "首次创业"
            elif any(w in exp for w in ['连续','多次','成功退出','卖过']): p["experience"] = "连续成功创业者"
            elif any(w in exp for w in ['大厂','BAT','字节','腾讯','阿里','谷歌','微软','Amazon','FAANG']): p["experience"] = "3-10年行业经验"
        if not p.get("experience"): p["experience"] = "首次创业"

        # 解析学历
        edu = p.get("education", "")
        if edu:
            if any(w in edu for w in ['博士','博']): p["education"] = "博士"
            elif any(w in edu for w in ['硕士','研究生','MBA','EMBA']): p["education"] = "硕士"
            elif any(w in edu for w in ['本科','学士','大学','本科']): p["education"] = "本科"
            elif any(w in edu for w in ['大专','专科']): p["education"] = "大专"
            elif any(w in edu for w in ['高中','初中','辍学','没上']): p["education"] = "高中及以下"
        if not p.get("education"): p["education"] = "本科"

        # 解析行业
        ind = p.get("industry", "")
        if not ind or ind in ["其他",""]:
            # 从想法中提取
            idea = profile.get("_idea", p.get("advantage", ""))
            ind = idea[:50]
        p["industry"] = ind or "综合"

        # 清理
        p.pop("capital_raw", None)
        p.pop("team_raw", None)
        return p

    def run_stream(self, idea: str, profile: dict):
        """四方推演：LLM + Agent + 内置数据 + 网络搜索"""
        # 先解析用户自由文本
        profile["_idea"] = idea
        if profile.get("extreme_mode"):
            profile = self._parse_extreme_profile(profile)
        profile = self._parse_profile(profile)

        # 强制API密钥检查
        api_key = profile.get("api_key", "")
        model = profile.get("model", "gpt-4o-mini")
        if not api_key:
            yield {"phase":"error","msg":"请先输入API密钥。支持OpenAI/DeepSeek/GLM/Qwen/豆包/Moonshot/Claude/Gemini等"}
            return
        yield {"phase":"init","msg":"验证API密钥..."}
        base_url = profile.get("api_base","")
        proxy = getattr(Config,"HTTPS_PROXY","") or getattr(Config,"HTTP_PROXY","")
        v = validate_key(api_key, model, base_url, getattr(Config,"VERIFY_SSL",True), proxy)
        if not v.get("valid"):
            yield {"phase":"error","msg":f"API密钥无效: {v.get('error','')}"}
            return
        # ✅ 线程安全：存实例属性而非 Config 类属性
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        label="绝境模式"if profile.get("extreme_mode")else"四方推演"
        yield {"phase":"init","msg":f"{label}启动: [{model}] + 7Agent + 400亿场景 + 网络搜索"}
        t0 = time.perf_counter()

        # Phase 0+1: classify + context 并行 (互不依赖)
        yield {"phase":"parallel","msg":"⚡ 并行: 场景分类 + 背景匹配..."}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f_classify = pool.submit(self.classify_scenario, idea, profile)
            f_context = pool.submit(self.agent_context, idea, profile)
            scenario = f_classify.result()
            ctx = f_context.result()
        sc_type = scenario.get("scenario_type","other")
        llm_baseline = scenario.get("baseline_rate",50)
        key_factors = scenario.get("key_factors",[])
        profile["_scenario_type"] = sc_type
        profile["_llm_baseline"] = llm_baseline
        profile["_key_factors"] = key_factors
        yield {"phase":"classify_done","data":{"scenario_type":sc_type,"baseline_rate":llm_baseline,"key_factors":key_factors}}
        yield {"phase":"context_done","data":{"match_score":ctx.get("match_score",50),"strengths":ctx.get("strengths",[]),"gaps":ctx.get("gaps",[]),"advice":ctx.get("advice","")}}

        # Phase 2+3: market + risk 并行 (互不依赖)
        yield {"phase":"parallel","msg":"⚡ 并行: 市场分析 + 风险评估..."}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f_market = pool.submit(self.agent_market, idea, profile)
            f_risk = pool.submit(self.agent_risk, idea, profile)
            market = f_market.result()
            risk = f_risk.result()
        yield {"phase":"market_done","data":market}
        yield {"phase":"risk_done","data":risk}

        # Phase 4: Strategy
        yield {"phase":"strategy","msg":"🎯 Agent 4/6: 生成策略路径..."}
        strategy = self.agent_strategy(idea, profile, market, risk)
        yield {"phase":"strategy_done","data":strategy}

        # Phase 5: Cross-Country (parallel — doesn't block)
        yield {"phase":"cross_country","msg":"🌍 Agent 5/7: 跨国对比推演..."}
        cc = self.agent_cross_country(idea, profile)
        yield {"phase":"cross_country_done","data":cc}

        # Phase 6: Deep Monte Carlo Simulation (使用LLM估算的基准率)
        yield {"phase":"deep_sim","msg":"🎲 Agent 6/7: 500宏观×500行业变革×400角色×400特质×10000次MC..."}
        from core.deep_simulator import DeepSimulator
        iters = profile.get("_iterations", 5000)
        ds = DeepSimulator(iterations=20000)
        deep_result = ds.simulate(idea, profile)
        yield {"phase":"deep_sim_done","data":deep_result}

        # ── Phase G: 宪法治理层 ──
        yield {"phase":"governance","msg":"🏛️ 宪法治理层: 启动5维交叉校验..."}
        all_data_before_report = {"context":ctx,"market":market,"risk":risk,"strategy":strategy,"cross_country":cc,"deep_sim":deep_result,"scenario":scenario}
        if self.governance is None:
            self.governance = GovernanceLayer(llm_fn=self._llm)
        try:
            governance_result = self.governance.evaluate(idea, profile, all_data_before_report)
        except Exception as e:
            logger.warning(f"Governance layer failed: {e}")
            governance_result = {"scores":{},"governance_score":0,"all_violations":[],"corrections":[],"interventions":[],"verdict":"skipped","summary":"治理层执行失败"}
        profile["_governance_result"] = governance_result
        yield {"phase":"governance_done","data":governance_result}

        # Phase 7: Report (注入治理上下文)
        yield {"phase":"report","msg":"📝 Agent 7/7: 生成最终报告..."}
        all_data = {"context":ctx,"market":market,"risk":risk,"strategy":strategy,"cross_country":cc,"deep_sim":deep_result,"scenario":scenario,"governance":governance_result}
        report = self.agent_report(idea, profile, all_data)
        yield {"phase":"report_done","data":{"report":report}}

        # Final: 优先用LLM估算基准，兜底用行业数据
        baseline = llm_baseline if llm_baseline > 0 else ind.get("baseline_success_rate",10) if (ind:=self._match_industry(profile.get("industry",""))) else 10
        city = self._match_city(profile.get("country","中国"),profile.get("city","北京"))
        final_rate = self._compute_final_rate(profile, baseline, city, ctx, market, risk)

        # ✅ 应用宪法治理层修正
        original_rate = deep_result["success_probability"]
        gs = governance_result.get("governance_score")
        if gs is not None and gs > 0 and self.governance is not None:
            corrected_rate = self.governance.apply_correction(original_rate, governance_result)
        else:
            corrected_rate = original_rate

        yield {"phase":"done","data":{
            "baseline_rate":round(baseline,1),
            "matched_rate":ctx.get("match_score",50),
            "adjusted_rate":round(final_rate,1),
            "final_rate":corrected_rate,
            "original_rate":original_rate,
            "governance_score":governance_result.get("governance_score", 0),
            "governance_verdict":governance_result.get("verdict", "skipped"),
            "governance_violations":governance_result.get("all_violations", []),
            "governance_scores":governance_result.get("scores", {}),
            "governance_corrections":governance_result.get("corrections", []),
            "governance_summary":governance_result.get("summary", ""),
            "confidence_band":{
                "p10":deep_result.get("stats",{}).get("p10",0),
                "p50":deep_result.get("stats",{}).get("p50",0),
                "p90":deep_result.get("stats",{}).get("p90",0),
            },
            "self_consistency":scenario.get("self_consistency", {}),
            "adjusted_rate":round(final_rate,1),
            "final_rate":deep_result["success_probability"],
            "report":report,
            "scenario_type":sc_type,
            "key_factors":key_factors,
            "market":market,"risk":risk,"strategy":strategy,"cross_country":cc,
            "deep_sim":deep_result,
            "total_time_ms":round((time.perf_counter()-t0)*1000),
            "extreme_events":deep_result.get("extreme_events",[]),
        }}

    def _compute_final_rate(self, profile, baseline, city, ctx, market, risk) -> float:
        r = baseline
        # Profile adjustments
        cap, team = profile.get("capital",0), profile.get("team_size",1)
        ca = self.bm.get("capital_adjustments",{})
        if cap<500000: r*=ca.get("0-500k",0.5)
        elif cap<2000000: r*=ca.get("500k-2m",0.7)
        elif cap<10000000: r*=ca.get("2m-10m",1.0)
        elif cap<50000000: r*=ca.get("10m-50m",1.3)
        else: r*=ca.get("50m+",1.6)
        ta = self.bm.get("team_adjustments",{})
        if team<=1: r*=ta.get("solo",0.4)
        elif team<=5: r*=ta.get("2-5人",0.65)
        elif team<=20: r*=ta.get("5-20人",1.0)
        elif team<=50: r*=ta.get("20-50人",1.25)
        else: r*=ta.get("50人+",1.5)
        ea = self.bm.get("experience_adjustments",{})
        r*=ea.get(profile.get("experience",""),1.0)
        em = {"高中及以下":0.85,"大专":0.9,"本科":1.0,"硕士":1.1,"博士":1.15}
        r*=em.get(profile.get("education","本科"),1.0)
        r*=city.get("success_mod",1.0)
        if profile.get("country")=="美国": r*=1.08
        elif profile.get("country")=="英国": r*=1.02
        elif profile.get("country")=="日本": r*=0.92
        # Context match boost
        match = ctx.get("match_score",50)
        r *= 0.7 + match/100*0.6
        return min(98, max(1, r))

    def _match_industry(self, name: str) -> dict:
        ind = self.bm.get("industries",{})
        # 优先精确匹配，再子串匹配
        for k,v in ind.items():
            if name == k: return v
        for k,v in ind.items():
            if name in k or k in name: return v
        return ind.get("企业服务SaaS",{"baseline_success_rate":10})

    def _match_city(self, country: str, city: str) -> dict:
        cc = self.cd.get("countries",{}).get(country,{})
        for rk in ["provinces","states","regions"]:
            for rn, rd in cc.get(rk,{}).items():
                if city in rd.get("cities",{}):
                    c = rd["cities"][city]
                    if "success_mod" not in c:
                        c = {**c, "success_mod": c.get("s",0.8)}
                    return c
        return {"success_mod":0.8}

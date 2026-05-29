"""Orchestrator v4 — 全球跨国推演"""

import logging, time, concurrent.futures
from agents.planner import decompose_idea
from agents.researcher import research_variable
from agents.reporter import generate_report
from core.simulator import GlobalSimulator
from config import Config

logger = logging.getLogger(__name__)

class IdeaSimulator:
    def __init__(self):
        self.sim = GlobalSimulator()

    def run(self, idea: str, profile: dict) -> dict:
        t0 = time.perf_counter()
        phases = {}
        fallback_plan = {"steps":[],"variables":[],"constraints":[]}
        fallback_result = {"verdict":"error","baseline_rate":10,"adjusted_rate":10,"final_rate":10,"all_paths":[],"recommended_paths":[],"has_recommendation":False}

        t1 = time.perf_counter()
        try:
            self.plan = decompose_idea(idea, profile) or fallback_plan
        except Exception as e:
            logger.warning(f"decompose_idea failed: {e}")
            self.plan = fallback_plan
        phases["plan"] = round((time.perf_counter()-t1)*1000)

        t2 = time.perf_counter()
        self.research = self._research(idea) if Config.ENABLE_NEWS else []
        phases["research"] = round((time.perf_counter()-t2)*1000)

        t3 = time.perf_counter()
        try:
            self.result = self.sim.simulate(profile, self.plan, self.research)
        except Exception as e:
            logger.error(f"simulate failed: {e}")
            self.result = fallback_result
        phases["simulation"] = round((time.perf_counter()-t3)*1000)

        t4 = time.perf_counter()
        try:
            report = generate_report(idea, profile, self.result)
        except Exception as e:
            logger.warning(f"generate_report failed: {e}")
            report = "报告生成失败，请重试"
        phases["report"] = round((time.perf_counter()-t4)*1000)

        return {
            "idea": idea, "profile": profile, "plan": self.plan,
            "verdict": self.result.get("verdict","unknown"),
            "baseline_rate": self.result.get("baseline_rate",10),
            "adjusted_rate": self.result.get("adjusted_rate",10),
            "final_rate": self.result.get("final_rate",10),
            "all_paths": self.result.get("all_paths",[]),
            "recommended_paths": self.result.get("recommended_paths",[]),
            "has_recommendation": self.result.get("has_recommendation",False),
            "industry": self.result.get("industry",{}),
            "city_info": self.result.get("city_info",{}),
            "cross_country": self.result.get("cross_country",[]),
            "methods_count": self.result.get("methods_count",0),
            "report": report, "phases": phases,
            "total_time_ms": round((time.perf_counter()-t0)*1000),
        }

    def _research(self, idea):
        queries = [f"{idea} 市场规模 报告",f"{idea} 竞争格局",f"{idea} 创业率 失败案例",f"{idea} 最新政策 法规"]
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            fs = [pool.submit(research_variable,{"name":q},idea) for q in queries]
            for f in concurrent.futures.as_completed(fs):
                try: results.append(f.result())
                except Exception as e: logger.debug(f"Research: {e}")
        return results

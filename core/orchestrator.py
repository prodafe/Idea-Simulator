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

        t1 = time.perf_counter()
        self.plan = decompose_idea(idea, profile)
        phases["plan"] = round((time.perf_counter()-t1)*1000)

        t2 = time.perf_counter()
        self.research = self._research(idea) if Config.ENABLE_NEWS else []
        phases["research"] = round((time.perf_counter()-t2)*1000)

        t3 = time.perf_counter()
        self.result = self.sim.simulate(profile, self.plan, self.research)
        phases["simulation"] = round((time.perf_counter()-t3)*1000)

        t4 = time.perf_counter()
        report = generate_report(idea, profile, self.result)
        phases["report"] = round((time.perf_counter()-t4)*1000)

        return {
            "idea": idea, "profile": profile, "plan": self.plan,
            "verdict": self.result["verdict"],
            "baseline_rate": self.result["baseline_rate"],
            "adjusted_rate": self.result["adjusted_rate"],
            "final_rate": self.result["final_rate"],
            "all_paths": self.result["all_paths"],
            "recommended_paths": self.result["recommended_paths"],
            "has_recommendation": self.result["has_recommendation"],
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

"""Core module tests"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_config():
    from config import Config
    assert Config.PORT == 8001
    assert Config.HOST == "0.0.0.0"

def test_data_loading():
    for f in ["scenarios.json","benchmarks.json","city_data.json"]:
        d = json.loads((Path(__file__).parent.parent/"data"/f).read_text(encoding="utf-8"))
        assert d, f"{f} is empty"

def test_scenario_counts():
    d = json.loads((Path(__file__).parent.parent/"data"/"scenarios.json").read_text(encoding="utf-8"))
    assert len(d["macro_scenarios"]) >= 800
    assert len(d["industry_shifts"]) >= 800
    assert len(d["personas"]) >= 600
    assert len(d["personality_traits"]) >= 600

def test_benchmarks():
    d = json.loads((Path(__file__).parent.parent/"data"/"benchmarks.json").read_text(encoding="utf-8"))
    assert len(d["industries"]) >= 500

def test_cities():
    d = json.loads((Path(__file__).parent.parent/"data"/"city_data.json").read_text(encoding="utf-8"))
    total = 0
    for cname in d["countries"]:
        for rk in ["provinces","states","regions"]:
            for rn, rd in d["countries"][cname].get(rk, {}).items():
                for cn in rd.get("cities", {}):
                    if cn not in ("其他", "その他"):
                        total += 1
    assert total >= 300

def test_accuracy_engine():
    from core.accuracy_engine import AccuracyEngine
    ae = AccuracyEngine()
    result = ae.back_test(50, "AI与大模型", {"capital": 1000000})
    assert result.get("anchored") is not None

def test_constraint_engine():
    from core.constraint_engine import ConstraintEngine
    ce = ConstraintEngine()
    result = ce.analyze({"city": "北京", "country": "中国", "capital": 2000000, "experience": "大厂5年", "education": "硕士"})
    assert "cultural_layer" in result
    assert "total_constraint_modifier" in result

def test_llm_models():
    from core.llm_provider import list_models, MODELS
    models = list_models()
    assert len(models) >= 30

def test_deep_simulator_init():
    from core.deep_simulator import DeepSimulator
    ds = DeepSimulator(iterations=100)
    assert ds.iterations == 100

def test_api_app():
    from api.server import app
    assert app.title == "Idea Simulator API"

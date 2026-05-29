"""API server — 用户画像驱动的推演"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from config import Config
from core.orchestrator import IdeaSimulator

logger = logging.getLogger(__name__)

app = FastAPI(title="Idea Simulator API", version="5.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── API Key Auth Middleware ──
import time as _time
_request_count: dict = {}
_rate_limit = 60  # max requests per minute per IP

# 不需要 API key 的公开路径 (防止随着端点增多遗漏)
_PUBLIC_PATHS = {
    "/", "/extreme", "/docs", "/openapi.json",
    "/api/health", "/api/metrics", "/api/models", "/api/benchmarks", "/api/cities",
    "/api/simulate", "/api/simulate/stream",
}
_PUBLIC_PREFIXES = ("/api/health",)  # 预留

@app.middleware("http")
async def auth_middleware(request, call_next):
    path = request.url.path
    if path in _PUBLIC_PATHS or path.endswith((".js",".css",".ico",".png")):
        return await call_next(request)
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key") or ""
    if not api_key:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error":"Missing X-API-Key header. Get your key from your LLM provider."}, status_code=401)
    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    now = _time.time()
    if client_ip not in _request_count:
        _request_count[client_ip] = []
    _request_count[client_ip] = [t for t in _request_count[client_ip] if now - t < 60]
    # 定期清理1小时无活动的IP条目，防止内存泄漏
    if len(_request_count) > 10000:
        _request_count.clear()
        _request_count[client_ip] = []
    if len(_request_count[client_ip]) >= _rate_limit:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error":"请求频率超限，请稍后重试"}, status_code=429)
    _request_count[client_ip].append(now)
    return await call_next(request)

@app.get("/cities.js")
async def cities_js():
    from fastapi.responses import FileResponse
    return FileResponse(frontend_dir / "cities.js", media_type="application/javascript")

simulator = IdeaSimulator()

@app.get("/api/health")
async def health():
    return {"status":"ok","version":"5.0.0"}

@app.get("/api/metrics")
async def metrics():
    import time, os
    pid = os.getpid()
    try:
        import psutil
        p = psutil.Process(pid)
        mem = round(p.memory_info().rss/1024/1024,1)
        cpu = p.cpu_percent()
    except ImportError:
        mem, cpu = 0, 0
    return {
        "version":"5.0.0",
        "memory_mb":mem,
        "cpu_percent":cpu,
        "active_ips":len(_request_count),
        "endpoints":len(app.routes),
    }


class SimulateRequest(BaseModel):
    idea: str
    profile: dict = {}


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    return html_path.read_text(encoding="utf-8") if html_path.exists() else "Not found"

@app.get("/extreme", response_class=HTMLResponse)
async def extreme():
    html_path = Path(__file__).parent.parent / "frontend" / "extreme.html"
    return html_path.read_text(encoding="utf-8") if html_path.exists() else "Not found"


@app.post("/api/simulate")
async def simulate(req: SimulateRequest):
    if not req.idea.strip():
        raise HTTPException(400, "想法不能为空")
    profile = req.profile or {}
    # 设置 Config (非流式路径需要)
    api_key = profile.get("api_key", "")
    model = profile.get("model", "gpt-4o-mini")
    if api_key:
        Config.LLM_API_KEY = api_key
        Config.LLM_MODEL = model
        base_url = profile.get("api_base", "")
        if base_url:
            Config.LLM_BASE_URL = base_url
    result = simulator.run(req.idea.strip(), profile)
    return result


@app.post("/api/simulate/stream")
async def simulate_stream(req: SimulateRequest):
    """多Agent流式推演 — SSE实时输出6个Agent的进度"""
    if not req.idea.strip():
        raise HTTPException(400, "想法不能为空")

    from core.stream_orchestrator import StreamOrchestrator
    orch = StreamOrchestrator()

    async def generate():
        for event in orch.run_stream(req.idea.strip(), req.profile or {}):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})


@app.get("/api/cities")
async def cities():
    cp = Path(__file__).parent.parent / "data" / "city_data.json"
    if not cp.exists(): return {}
    data = json.loads(cp.read_text(encoding="utf-8"))
    result = {}
    for country, cdata in data.get("countries", {}).items():
        result[country] = {"flag": cdata.get("flag", ""), "cities": []}
        for region_key in ["provinces", "states", "regions"]:
            for region_name, region_data in cdata.get(region_key, {}).items():
                for city_name in region_data.get("cities", {}):
                    if city_name not in ("其他", "その他") and city_name not in result[country]["cities"]:
                        result[country]["cities"].append(city_name)
        result[country]["cities"].sort()
    return result


@app.get("/api/models")
async def list_models():
    from core.llm_provider import list_models
    return list_models()

@app.get("/api/benchmarks")
async def benchmarks():
    bp = Path(__file__).parent.parent / "data" / "benchmarks.json"
    if bp.exists():
        return json.loads(bp.read_text(encoding="utf-8"))
    return {}


def start():
    import uvicorn
    try:
        uvicorn.run(app, host=Config.HOST, port=Config.PORT, log_level="info")
    except OSError as e:
        import sys
        print(f"[FATAL] 端口 {Config.PORT} 被占用或无法绑定: {e}", file=sys.stderr)
        print(f"[FATAL] 请尝试: python run.py --port {Config.PORT+1}", file=sys.stderr)
        sys.exit(1)

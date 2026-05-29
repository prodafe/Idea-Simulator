"""Idea Simulator — 配置"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # 模型
    LLM_MODEL: str = "qwen2.5:7b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # 推演参数
    MAX_DEPTH: int = 4               # 决策树最大深度
    MAX_BRANCHES: int = 3            # 每层最大分支数
    MONTE_CARLO_SAMPLES: int = 100   # 蒙特卡洛采样数
    TOP_PATHS: int = 3               # 输出的最优路径数
    MAX_SEARCH_RESULTS: int = 8      # 每个研究任务搜索条数

    # 搜索源
    ENABLE_NEWS: bool = True
    ENABLE_RESEARCH: bool = True
    ENABLE_STATISTICS: bool = True

    # Agent
    MAX_RESEARCH_ROUNDS: int = 2     # 研究轮数
    SEARCH_TIMEOUT: int = 15         # 搜索超时(秒)

    # 路径
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    CACHE_DIR: str = os.path.join(BASE_DIR, "data", "cache")

    # 网络
    VERIFY_SSL: bool = os.environ.get("IDEA_VERIFY_SSL", "true").lower() != "false"
    HTTP_PROXY: str = os.environ.get("HTTP_PROXY", "")
    HTTPS_PROXY: str = os.environ.get("HTTPS_PROXY", "")
    LLM_TIMEOUT: int = int(os.environ.get("IDEA_LLM_TIMEOUT", "60"))

    # UI
    HOST: str = "0.0.0.0"
    PORT: int = 8001

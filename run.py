"""Idea Simulator — 想法成功率推演引擎

用法:
    python run.py                        # API + WebUI
    python run.py --idea "你的想法"       # CLI 模式
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("idea_simulator")


def run_cli(idea: str):
    """命令行模式"""
    from core.stream_orchestrator import StreamOrchestrator

    print(f"\n{'='*60}")
    print(f"  Idea Simulator v17 — 千级数据推演引擎")
    print(f"  场景: {idea}")
    print(f"{'='*60}\n")

    orch = StreamOrchestrator()
    result = {}
    for event in orch.run_stream(idea, {"api_key":"demo","model":"gpt-4o-mini"}):
        if event.get("phase") == "done":
            result = event.get("data", {})
        elif event.get("msg"):
            print(f"  {event['msg']}")

    if "error" in result:
        print(f"错误: {result['error']}")
        return

    print(f"\n{'='*60}")
    print(f"  总体成功率: {result['success_rate']}%")
    print(f"  推演路径: {result['total_paths']} 条")
    print(f"  搜索数据: {result['research_data_count']} 个变量")
    print(f"  总耗时: {result['total_time_ms']}ms")
    print(f"{'='*60}\n")

    print("─" * 40)
    print("Top 3 最优路径:")
    for i, path in enumerate(result["top_paths"], 1):
        print(f"\n 路径 {i} (成功率: {path['success_rate']}%):")
        for step in path["steps"]:
            print(f"   {step}")

    print(f"\n{'─'*40}")
    print("分析报告:")
    print(result["report"])

    # 保存结果
    output_file = Path("data/results.json")
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {output_file}")


def run_api():
    """API + WebUI 模式"""
    from api.server import start

    start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Idea Simulator — 想法成功率推演引擎")
    parser.add_argument("--idea", type=str, help="你的想法描述")
    parser.add_argument("--port", type=int, default=8001, help="WebUI 端口 (默认 8001)")
    args = parser.parse_args()

    if args.idea:
        run_cli(args.idea)
    else:
        run_api()

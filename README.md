# Idea Simulator — 通用场景AI推演引擎

> 6354亿场景组合 · 1000维推演 · 20000次蒙特卡洛 · 37个主流模型

**输入任何场景，AI进行四方推演（LLM + Agent + 内置场景库 + 网络搜索），给你成功率 + 最优路径。**

---

## 快速开始

```bash
# 安装
pip install -e .

# 启动
python -c "from api.server import start; start()"
# 浏览器打开 http://localhost:8001
```

**必须提供API密钥** — 支持 GPT-5.5 / Claude Opus 4.7 / DeepSeek V4 / GLM-5.1 / Qwen3.5 / Gemini 等 37 个模型。

---

## 功能

### 三种模式
| 模式 | 说明 |
|------|------|
| 标准模式 | 输入场景 → 四方推演 → 成功率 + 路径 |
| 剑走偏锋 | 不择手段的极端策略推演 |
| 绝境模式 | 完整身份模拟（年龄/疾病/前科/债务/技能） |

### 推演引擎
- **7 Agent 协作**: 背景分析 → 市场分析 → 风险评估 → 策略生成 → 跨国对比 → 深度蒙特卡洛 → 综合报告
- **1000维场景库**: 1000宏观 × 1000变革 × 800角色 × 800特质 × 800蝴蝶效应
- **精度引擎**: 幂律分布采样 + 变量相关性矩阵 + 历史回测 + 事实锚定 + 约束交互
- **双轨数据**: 500真实锚定 + 500未来投影

### 数据规模
- 323个城市（中美英日） / 532个行业 / 172个历史案例
- 37个接入模型（OpenAI / Anthropic / Google / DeepSeek / 阿里 / 智谱 / 字节等）
- 10项核心测试 / GitHub Actions CI / API限流 / 监控

---

## 项目结构

```
idea_simulator/
├── api/server.py           # FastAPI 服务
├── core/
│   ├── deep_simulator.py   # 蒙特卡洛推演引擎
│   ├── stream_orchestrator.py  # 流式Agent编排
│   ├── accuracy_engine.py  # 精度引擎（幂律/回测/锚定）
│   ├── constraint_engine.py # 约束交互引擎
│   └── llm_provider.py     # 统一LLM（37模型）
├── agents/                 # Planner / Researcher / Reporter
├── data/                   # 场景库 / 行业基准 / 城市数据
├── frontend/               # WebUI (标准 + 绝境)
└── tests/                  # 测试套件
```

## 许可证

MIT License

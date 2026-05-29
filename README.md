# Idea Simulator — 通用场景 AI 推演引擎

> 6354 亿场景组合 · 1000 维推演 · 20000 次蒙特卡洛 · 37 个主流模型

**输入任何场景，AI 进行四方推演（LLM + Agent + 内置场景库 + 网络搜索），输出成功率 + 最优路径。**

---

## 快速开始

```bash
# 安装
git clone https://github.com/prodafe/Idea-Simulator.git
cd Idea-Simulator
pip install -e .

# 启动
idea-simulator
# 浏览器打开 http://localhost:8001
```

**必须提供 API 密钥** — 支持 GPT-5.5 / Claude Opus 4.7 / DeepSeek V4 / GLM-5.1 / Qwen3.5 / Gemini 等 37 个模型。国内用户推荐 DeepSeek 或 硅基流动(SiliconFlow)，直连速度快。

---

## 网络配置（国内用户 / 企业内网）

```bash
# SSL 证书问题
set IDEA_VERIFY_SSL=false

# 代理
set HTTPS_PROXY=http://127.0.0.1:7890

# 超时（秒）
set IDEA_LLM_TIMEOUT=120
```

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
- **1000 维场景库**: 1000 宏观 × 1000 变革 × 800 角色 × 800 特质 × 800 蝴蝶效应
- **精度引擎**: 幂律分布采样 + 变量相关性矩阵 + 历史回测 + 事实锚定 + 约束交互
- **双轨数据**: 500 真实锚定 + 500 未来投影

### 数据规模
- 323 个城市（中美英日） / 532 个行业 / 172 个历史案例
- 37 个接入模型（OpenAI / Anthropic / Google / DeepSeek / 阿里 / 智谱 / 字节等）
- 10 项核心测试 / GitHub Actions CI

---

## 项目结构

```
idea_simulator/
├── api/server.py               # FastAPI 服务
├── core/
│   ├── deep_simulator.py       # 蒙特卡洛推演引擎
│   ├── stream_orchestrator.py  # 流式 Agent 编排
│   ├── orchestrator.py         # 推演编排器
│   ├── accuracy_engine.py      # 精度引擎（幂律/回测/锚定）
│   ├── constraint_engine.py    # 约束交互引擎
│   ├── timeline.py             # 时间线生成
│   └── llm_provider.py         # 统一 LLM（37 模型 + SSL/代理）
├── agents/                     # Planner / Researcher / Reporter
├── data/                       # 场景库 / 行业基准 / 城市数据
├── frontend/                   # WebUI（标准 + 绝境）
└── tests/                      # 测试套件
```

---

## 命令行

```bash
# WebUI 模式（默认端口 8001）
idea-simulator

# 自定义端口
idea-simulator --port 8080

# CLI 模式
idea-simulator --idea "你的创业想法"

# 经典启动方式
python run.py
```

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 标准模式 WebUI |
| `/extreme` | GET | 绝境模式 WebUI |
| `/api/simulate` | POST | 推演（JSON 响应） |
| `/api/simulate/stream` | POST | 推演（SSE 流式） |
| `/api/health` | GET | 健康检查 |
| `/api/metrics` | GET | 运行时指标 |
| `/api/models` | GET | 可用模型列表 |
| `/api/cities` | GET | 城市数据 |
| `/api/benchmarks` | GET | 行业基准 |

---

## 社区

- 🐛 发现问题请提 [Issue](https://github.com/prodafe/Idea-Simulator/issues)
- 💡 有好的想法欢迎 [PR](https://github.com/prodafe/Idea-Simulator/pulls)
- ⭐ 如果觉得有用，给个 Star 支持一下

---

## Changelog

### v4.0.0 (2026-05-29) — 修复版

- 🔧 修复 24 个 Bug（4 致命 + 3 高危 + 7 中危 + 10 低危）
- 🛡️ 安全加固：XSS 防护、API 密钥校验、SSE 错误显示
- 🔌 SSL/代理/超时可配置：`IDEA_VERIFY_SSL` / `HTTP_PROXY` / `IDEA_LLM_TIMEOUT`
- 🧵 线程安全：多用户并发不再串 key
- 📦 一键部署：`pip install -e .` + `idea-simulator` CLI
- 🚀 10/10 测试通过

---

## 许可证

MIT License

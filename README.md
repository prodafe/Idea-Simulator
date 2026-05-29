# Idea Simulator — 通用场景 AI 推演引擎

> 12 场景类型自适应 · 6 维宪法治理 · 20000 次蒙特卡洛 · 37 个主流模型 · 综合现实锚定数据库

**输入任何场景——求职、创业、投资、搬家、考试、甚至扔垃圾——AI 进行四方推演 + 宪法治理校验，输出真实可信的成功率 + 置信区间 + 深度分析报告。**

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
| 标准模式 | 输入场景 → 四方推演 → 宪法治理校验 → 成功率 + 置信带 + 深度报告 |
| 剑走偏锋 | 不择手段的极端策略推演 |
| 绝境模式 | 完整身份模拟（年龄/疾病/前科/债务/技能） |

### 场景自适应推演引擎
- **12 场景类型**: 日常/求职/晋升/创业/经营/投资/谈判/搬家/教育/法律/健康/其他
- **LLM 自动分类**: 扔垃圾 → daily_life(99.5%)、应聘特斯拉 → career_job(30-50%)、创业 → business_startup(10-25%)
- **非商业场景自动适配**: 不会用"市场规模"、"团队资金"框架去分析"扔垃圾"
- **自我一致性**: 乐观+保守双次估算，偏差过大自动取均值

### 宪法治理层 (Constitutional Governance)
- **6 维交叉校验**: 真实性锚定 + 可行性检查 + 一致性校验 + 回测对标 + 幻觉检测 + 社会规范
- **治理分修正**: 0-100 分 → 成功率乘数 0.70-1.00
- **违规分级**: critical / high / medium / low，前端卡片展示
- **报告强制回应**: 严重违规必须在报告中逐条回应

### 深度结构化报告
- 5 段分析：核心结论 → 成败拆解（4 维度）→ 真实世界对比 → 路径推演 → 行动清单
- 强制引用真实数据，场景自适应分析维度
- 置信带 P10/P50/P90 + 治理层审查结果

### 综合现实锚定数据库
- 12 场景类型真实基准 / 10 城市生活数据 / 9 求职行业录取率
- 6 投资资产类别 / 教育录取率 / 健康恢复率 / 社会传播模型
- 4 国监管时限表 / 186 历史对标案例
- 37 个接入模型（OpenAI / Anthropic / Google / DeepSeek / 阿里 / 智谱 / 字节等）

---

## 项目结构

```
idea_simulator/
├── api/server.py                    # FastAPI 服务
├── core/
│   ├── deep_simulator.py            # 蒙特卡洛推演引擎
│   ├── stream_orchestrator.py       # 流式 Agent 编排（含场景分类+自我一致性）
│   ├── orchestrator.py              # 非流式编排器
│   ├── accuracy_engine.py           # 精度引擎（幂律/回测/锚定）
│   ├── constraint_engine.py         # 约束交互引擎
│   ├── timeline.py                  # 时间线生成
│   ├── llm_provider.py              # 统一 LLM（37 模型 + SSL/代理）
│   └── governance/                  # 🏛️ 宪法治理层
│       ├── __init__.py              # 治理编排器（评分、修正、聚合）
│       ├── reality_anchor.py        # 真实性锚定
│       ├── social_norm.py           # 社会规范校验
│       ├── feasibility_check.py     # 可行性检查
│       ├── consistency_crosscheck.py # 一致性交叉校验
│       └── anti_hallucination.py    # 幻觉检测
├── agents/                          # Planner / Researcher / Reporter
├── data/                            # 场景库 / 行业基准 / 城市数据 / 锚定库
├── frontend/                        # WebUI（标准 + 绝境）
└── tests/                           # 测试套件
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

### v5.0.0 (2026-05-29) — 修订稳定版

- 🧠 **场景自适应引擎**: 12 种场景类型自动识别，LLM 估算基准率 + 自我一致性校验
- 🏛️ **宪法治理层**: 6 维交叉校验（真实性/规范/可行性/一致性/幻觉/回测），治理分修正成功率
- 📊 **综合现实锚定库**: 12 场景基准 + 10 城市 + 9 求职行业 + 6 投资类别 + 教育/健康/传播数据
- ⚡ **LLM 并行化**: 4 次串行→2 轮并行，省 ~40% 时间
- 📝 **深度结构化报告**: 5 段分析 + 强制引用数据 + 治理审查回应
- 🐛 **修复**: power_law 双除 100、timeline int 崩溃、Anthropic ThinkingBlock、DeepSeek 模型名等 10+ 项
- 🚀 10/10 测试通过

### v4.0.0 (2026-05-29) — 修复版

- 🔧 修复 24 个 Bug（4 致命 + 3 高危 + 7 中危 + 10 低危）
- 🛡️ 安全加固：XSS 防护、API 密钥校验
- 🔌 SSL/代理/超时可配置
- 📦 `pip install -e .` + `idea-simulator` CLI

---

## 许可证

MIT License

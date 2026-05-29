# Changelog

## [4.0.0] — 2026-05-29

### Bug 修复（24项）
- **致命**: 表单 async submit 刷新页面清空输入 → `event.preventDefault()`
- **致命**: 中间件 401 拦截推演请求 → `/api/simulate/stream` 加入豁免
- **致命**: `#f-opponent`/`#f-deadline` 引用空元素 JS 崩溃 → 移除失效引用
- **致命**: 绝境模式无 API key 输入框 → 添加密钥+模型选择器
- **高危**: LLM Provider 无 SSL/代理/超时配置 → 3 个环境变量 + httpx 客户端
- **高危**: Config 类属性并发覆盖 → StreamOrchestrator 实例属性隔离
- **中危**: 偏锋模式全局数据损坏 → dict() 拷贝后再修改
- **中危**: `pip install -e .` 打包失败 → 修复 license/py_modules/packages.find
- **中危**: CLI 入口 `run:main` 不可用 → 添加 main() 函数
- **中危**: `_load_city()` 城市数据永远返回 `{}` → 修复 JSON 键路径
- **中危**: agents 死 import ollama → 移除
- **低危**: 裸 `except:` → `except Exception:`, XSS 防护, 整数溢出截断, 静默 fallback 日志, 孤儿字符串, 速率限制泄漏等 10 项

### 安全
- XSS 防护：报告输出使用 `esc()` 转义 HTML
- API 密钥校验：前端拦截空密钥，后端 validate_key 增强错误信息
- 速率限制：定期清理不活跃 IP，防止内存泄漏

### 部署
- `pip install -e .` ✅ 一行安装
- `idea-simulator` CLI ✅ 全局命令
- Windows/Linux/macOS 通用

---

## [3.0.0] — 2026-05-29

### 工程化
- 10 tests, GitHub Actions CI/CD
- API鉴权中间件 + 请求限流
- pip install 一键部署 (pyproject.toml)
- 监控端点 (/api/health, /api/metrics)
- CONTRIBUTING.md / SECURITY.md / CHANGELOG.md

### 模型接入
- 37个2026年5月最新模型
- GPT-5.5 / Claude Opus 4.7 / DeepSeek V4 / GLM-5.1 / Qwen3.5 等
- 自定义API地址支持

### 数据规模
- 6354亿基础组合
- 1000宏观 × 1000变革 × 800角色 × 800特质 × 800蝴蝶
- 323城市 × 532行业 × 172历史对标

### 推演引擎
- 7Agent流式协作
- 双轨引擎（真实锚定 + 未来投影）
- 幂律分布精度引擎（变量相关性、历史回测、事实锚定）
- 约束交互引擎（文化圈层 × 资源可及性 × 认知偏差）
- 绝境模式（完整身份模拟）

### 前端
- 通用推演框 + 详细模式
- 绝境模式独立页面
- 37模型下拉选择器
- API密钥醒目提示

---

## [1.0.0] — 2026-05-29

### 初始版本
- 创业想法推演
- 4策略路径对比
- 国家/城市选择
- 基础蒙特卡洛模拟
- Ollama本地模型支持

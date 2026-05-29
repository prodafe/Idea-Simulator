# 参与贡献

欢迎任何形式的贡献！无论是代码、数据、文档还是反馈。

## 贡献方式

- 🐛 **报告Bug**: 在 [Issues](https://github.com/prodafe/Idea-Simulator/issues) 中描述问题
- 💡 **建议功能**: 在 Issues 中提出新想法
- 📊 **贡献数据**: 提交新的场景数据、行业基准、历史案例
- 🔀 **提交代码**: Fork → Feature Branch → Pull Request

## 开发环境

```bash
git clone https://github.com/prodafe/Idea-Simulator.git
cd Idea-Simulator
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## 数据贡献指南

数据文件位于 `data/` 目录，JSON格式。新增数据请确保：
- 基于可验证的真实来源
- 添加 `projected: true` 标记如果是未来预测
- 通过 `python -m pytest tests/` 测试

## 提交规范

- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `data:` 数据更新
- `test:` 测试
- `perf:` 性能优化

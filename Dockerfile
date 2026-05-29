# Idea Simulator v5.0.0 — Docker 部署
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Idea Simulator"
LABEL org.opencontainers.image.description="通用场景 AI 推演引擎 — 12 场景类型 × 6 维宪法治理"
LABEL org.opencontainers.image.version="5.0.0"
LABEL org.opencontainers.image.url="https://github.com/prodafe/Idea-Simulator"

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目
COPY . .

# 安装项目
RUN pip install -e . --no-deps

EXPOSE 8001

# 默认启动 WebUI
CMD ["python", "run.py"]

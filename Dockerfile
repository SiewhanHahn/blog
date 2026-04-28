# Dockerfile
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，防止 Python 生成 .pyc 文件，并强制即时输出日志
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 复制依赖文件并安装
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制整个项目代码
COPY . /app/

# 暴露 Flask 默认端口
EXPOSE 5000

# 启动应用
CMD ["python", "run.py"]
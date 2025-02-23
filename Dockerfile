# 使用官方 Python 运行时作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件到容器中
COPY . /app

# 安装 Python 依赖
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 设置环境变量，避免缓存带来的警告
ENV PYTHONUNBUFFERED=1

# 暴露端口（如果需要）
EXPOSE 8081

# 运行脚本，支持传入命令行参数
ENTRYPOINT ["python", "main.py"]

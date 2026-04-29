# app.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    # 必须指定 host='0.0.0.0'，否则在 Docker 容器外部无法访问暴露的 5000 端口
    app.run(host='0.0.0.0', port=5000)
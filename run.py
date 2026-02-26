#!/usr/bin/env python
"""启动 WebCare 应用"""
from app import app, init_db
from config import Config
import os

if __name__ == '__main__':
    # 初始化数据库
    if not os.path.exists(Config.DATABASE_PATH):
        init_db()
        print("数据库已初始化")

    print("启动 WebCare 应用...")
    print("访问 http://localhost:5000 开始使用")
    app.run(host='0.0.0.0', port=5000)

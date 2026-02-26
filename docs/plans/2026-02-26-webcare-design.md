# WebCare 签到打卡应用实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现一个 Flask + SQLite 的签到打卡应用，支持用户首次设置姓名和紧急联系人邮箱，之后每日签到，系统自动发送预警邮件。

**Architecture:** 单文件 Flask 应用 + SQLite 数据库，内置定时检查线程，每分钟检查是否需要发送预警邮件，前端用简单的 HTML + Jinja2 模板。

**Tech Stack:** Flask, SQLite, SMTPlib (QQ邮箱)

---

### Task 1: 项目基础结构搭建

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `app.py`

**Step 1: 创建 requirements.txt**

```txt
Flask>=2.0.0
APScheduler>=3.10.0
```

**Step 2: 创建 config.py**

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'webcare.db')

    # QQ邮箱 SMTP 配置
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')  # QQ邮箱授权码

    # 默认预警间隔（小时）
    DEFAULT_WARNING_INTERVAL_HOURS = 24 * 2  # 2天
```

**Step 3: 创建 app.py 基础框架**

```python
from flask import Flask
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

@app.route('/')
def index():
    return 'WebCare App'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**Step 4: 运行验证**

Run: `cd D:/tech/ai/github/webcare/.worktrees/feature-webcare && pip install -r requirements.txt && python app.py`
Expected: Flask 服务启动成功

**Step 5: Commit**

```bash
git add requirements.txt config.py app.py
git commit -m "chore: add project structure and dependencies"
```

---

### Task 2: 数据库模型设计

**Files:**
- Create: `models.py`
- Modify: `app.py`

**Step 1: 写入失败的测试**

```python
# tests/test_models.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import User, CheckIn, init_db

def test_user_creation():
    user = User(name='张三', emergency_email='test@example.com')
    assert user.name == '张三'
    assert user.emergency_email == 'test@example.com'

def test_checkin_creation():
    checkin = CheckIn(user_id=1)
    assert checkin.user_id == 1
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_models.py -v`
Expected: FAIL - models 模块不存在

**Step 3: 实现 models.py**

```python
import sqlite3
import os
from datetime import datetime
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            emergency_email TEXT NOT NULL,
            warning_interval_hours INTEGER DEFAULT 48,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_checkin TIMESTAMP,
            last_warning_sent TIMESTAMP,
            unique_user_token TEXT UNIQUE
        )
    ''')

    # 签到记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            checkin_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()

class User:
    def __init__(self, id=None, name=None, emergency_email=None,
                 warning_interval_hours=48, created_at=None, last_checkin=None,
                 last_warning_sent=None, unique_user_token=None):
        self.id = id
        self.name = name
        self.emergency_email = emergency_email
        self.warning_interval_hours = warning_interval_hours
        self.created_at = created_at
        self.last_checkin = last_checkin
        self.last_warning_sent = last_warning_sent
        self.unique_user_token = unique_user_token

    @staticmethod
    def create(name, emergency_email):
        import uuid
        token = str(uuid.uuid4())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (name, emergency_email, unique_user_token) VALUES (?, ?, ?)',
            (name, emergency_email, token)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return User.get_by_id(user_id)

    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return User(
                id=row['id'], name=row['name'],
                emergency_email=row['emergency_email'],
                warning_interval_hours=row['warning_interval_hours'],
                created_at=row['created_at'], last_checkin=row['last_checkin'],
                last_warning_sent=row['last_warning_sent'],
                unique_user_token=row['unique_user_token']
            )
        return None

    @staticmethod
    def get_by_token(token):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE unique_user_token = ?', (token,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return User(
                id=row['id'], name=row['name'],
                emergency_email=row['emergency_email'],
                warning_interval_hours=row['warning_interval_hours'],
                created_at=row['created_at'], last_checkin=row['last_checkin'],
                last_warning_sent=row['last_warning_sent'],
                unique_user_token=row['unique_user_token']
            )
        return None

    def update_last_checkin(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET last_checkin = CURRENT_TIMESTAMP WHERE id = ?',
            (self.id,)
        )
        conn.commit()
        conn.close()

    def update_warning_interval(self, hours):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET warning_interval_hours = ? WHERE id = ?',
            (hours, self.id)
        )
        conn.commit()
        conn.close()

    def update_last_warning_sent(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET last_warning_sent = CURRENT_TIMESTAMP WHERE id = ?',
            (self.id,)
        )
        conn.commit()
        conn.close()

class CheckIn:
    def __init__(self, id=None, user_id=None, checkin_time=None):
        self.id = id
        self.user_id = user_id
        self.checkin_time = checkin_time

    @staticmethod
    def create(user_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO checkins (user_id) VALUES (?)', (user_id,))
        conn.commit()
        checkin_id = cursor.lastrowid
        conn.close()

        # 更新用户的最后签到时间
        user = User.get_by_id(user_id)
        user.update_last_checkin()

        return CheckIn(id=checkin_id, user_id=user_id, checkin_time=datetime.now())

    @staticmethod
    def get_by_user(user_id, limit=30):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM checkins WHERE user_id = ? ORDER BY checkin_time DESC LIMIT ?',
            (user_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return [CheckIn(id=row['id'], user_id=row['user_id'],
                       checkin_time=row['checkin_time']) for row in rows]
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add models.py tests/test_models.py
git commit -m "feat: add database models for User and CheckIn"
```

---

### Task 3: 邮件发送模块

**Files:**
- Create: `utils/email.py`
- Test: `tests/test_email.py`

**Step 1: 写入失败的测试**

```python
# tests/test_email.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.email import send_warning_email

def test_send_warning_email():
    # 这个测试会因为函数不存在而失败
    result = send_warning_email('test@example.com', '张三')
    assert result == True
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_email.py -v`
Expected: FAIL - send_warning_email 不存在

**Step 3: 实现邮件发送模块**

```python
# utils/email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def send_warning_email(to_email, user_name):
    """
    发送预警邮件到紧急联系人
    """
    from config import Config

    msg = MIMEMultipart()
    msg['From'] = Config.MAIL_USERNAME
    msg['To'] = to_email
    msg['Subject'] = f'【紧急】{user_name} 已多天未活动'

    body = f'''
亲爱的紧急联系人：

您好！我是 {user_name}。

我已连续多天没有活动了，请检查下我的状态。

如果看到这条消息，请尽快与我联系确认安全。

---
此邮件由 WebCare 自动发送
'''

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP_SSL(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.sendmail(Config.MAIL_USERNAME, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"发送邮件失败: {e}")
        return False
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_email.py -v`
Expected: PASS (实际会尝试发送邮件，可以通过 mock 测试)

**Step 5: Commit**

```bash
git add utils/email.py tests/test_email.py
git commit -m "feat: add email sending functionality"
```

---

### Task 4: 前端模板

**Files:**
- Create: `templates/base.html`
- Create: `templates/index.html`
- Create: `templates/register.html`
- Create: `templates/checkin.html`
- Create: `templates/settings.html`

**Step 1: 创建 base
<!.html**

```htmlDOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebCare 签到打卡</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .btn { display: block; width: 100%; padding: 15px; margin: 10px 0;
               background: #4CAF50; color: white; border: none; border-radius: 8px;
               font-size: 18px; cursor: pointer; text-align: center; text-decoration: none; }
        .btn:hover { background: #45a049; }
        .btn-secondary { background: #2196F3; }
        .btn-secondary:hover { background: #1976D2; }
        .btn-danger { background: #f44336; }
        .btn-danger:hover { background: #da190b; }
        input { width: 100%; padding: 12px; margin: 8px 0;
                border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
        .info { background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .success { background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .warning { background: #fff3e0; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .error { background: #ffebee; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .user-info { text-align: center; margin-bottom: 20px; color: #666; }
        .token-link { word-break: break-all; background: #f5f5f5; padding: 10px;
                      border-radius: 4px; font-size: 12px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

**Step 2: 创建 index.html**

```html
{% extends "base.html" %}

{% block content %}
<h1>WebCare 签到打卡</h1>

{% if user %}
<div class="user-info">
    <p>欢迎，<strong>{{ user.name }}</strong></p>
    <p>上次签到: {{ user.last_checkin if user.last_checkin else '从未签到' }}</p>
</div>

<a href="/checkin" class="btn">签到</a>
<a href="/settings" class="btn btn-secondary">设置</a>

<div class="info">
    <p>紧急联系人: {{ user.emergency_email }}</p>
    <p>预警间隔: {{ user.warning_interval_hours }} 小时</p>
</div>

<div class="token-link">
    <p>您的专属链接（请保存）:</p>
    <p>{{ request.url_root }}?token={{ user.unique_user_token }}</p>
</div>

{% else %}
<div class="info">
    <p>欢迎使用 WebCare！请先注册，设置您的姓名和紧急联系人邮箱。</p>
</div>

<a href="/register" class="btn">立即注册</a>
{% endif %}
{% endblock %}
```

**Step 3: 创建 register.html**

```html
{% extends "base.html" %}

{% block content %}
<h1>用户注册</h1>

<form method="POST" action="/register">
    <label>您的姓名:</label>
    <input type="text" name="name" required placeholder="请输入姓名">

    <label>紧急联系人邮箱:</label>
    <input type="email" name="emergency_email" required placeholder="请输入紧急联系人邮箱">

    <button type="submit" class="btn">注册</button>
</form>

<a href="/" class="btn btn-secondary">返回</a>
{% endblock %}
```

**Step 4: 创建 checkin.html**

```html
{% extends "base.html" %}

{% block content %}
<h1>签到</h1>

{% if success %}
<div class="success">
    <p>签到成功！</p>
    <p>签到时间: {{ checkin_time }}</p>
</div>
{% endif %}

{% if last_checkin %}
<div class="info">
    <p>上次签到: {{ last_checkin }}</p>
</div>
{% endif %}

<a href="/" class="btn">返回首页</a>
{% endblock %}
```

**Step 5: 创建 settings.html**

```html
{% extends "base.html" %}

{% block content %}
<h1>设置</h1>

<form method="POST" action="/settings">
    <label>预警时间间隔:</label>
    <select name="warning_interval" required>
        <option value="2" {% if user.warning_interval_hours == 2 %}selected{% endif %}>2 小时</option>
        <option value="24" {% if user.warning_interval_hours == 24 %}selected{% endif %}>1 天</option>
        <option value="48" {% if user.warning_interval_hours == 48 %}selected{% endif %}>2 天</option>
        <option value="72" {% if user.warning_interval_hours == 72 %}selected{% endif %}>3 天</option>
    </select>

    <button type="submit" class="btn">保存设置</button>
</form>

<div class="token-link">
    <p>您的专属链接（请保存）:</p>
    <p>{{ request.url_root }}?token={{ user.unique_user_token }}</p>
</div>

<a href="/" class="btn btn-secondary">返回首页</a>
{% endblock %}
```

**Step 6: Commit**

```bash
git add templates/
git commit -m "feat: add frontend templates"
```

---

### Task 5: 路由和业务逻辑

**Files:**
- Modify: `app.py`

**Step 1: 写入失败的测试**

```python
# tests/test_routes.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_index_route_requires_token():
    from app import app
    client = app.test_client()
    response = client.get('/')
    # 首页应该需要 token 参数
    assert response.status_code in [200, 302]
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_routes.py -v`
Expected: FAIL - app 没有这些路由

**Step 3: 实现完整路由**

```python
from flask import Flask, render_template, request, redirect, url_for, flash
from config import Config
from models import User, CheckIn, init_db
import os

app = Flask(__name__)
app.config.from_object(Config)

# 确保数据库存在
if not os.path.exists(Config.DATABASE_PATH):
    init_db()

@app.route('/')
def index():
    token = request.args.get('token')
    if not token:
        return render_template('index.html', user=None)

    user = User.get_by_token(token)
    return render_template('index.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        emergency_email = request.form.get('emergency_email')

        if not name or not emergency_email:
            return render_template('register.html', error='请填写所有字段')

        user = User.create(name, emergency_email)
        return redirect(url_for('index', token=user.unique_user_token))

    return render_template('register.html')

@app.route('/checkin')
def checkin():
    token = request.args.get('token')
    if not token:
        return redirect(url_for('index'))

    user = User.get_by_token(token)
    if not user:
        return redirect(url_for('index'))

    # 执行签到
    checkin = CheckIn.create(user.id)

    return render_template('checkin.html',
                           success=True,
                           checkin_time=checkin.checkin_time,
                           last_checkin=user.last_checkin)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    token = request.args.get('token')
    if not token:
        return redirect(url_for('index'))

    user = User.get_by_token(token)
    if not user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        warning_interval = int(request.form.get('warning_interval', 48))
        user.update_warning_interval(warning_interval)
        return render_template('settings.html', user=user, success=True)

    return render_template('settings.html', user=user)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_routes.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py
git commit -m "feat: add routes and business logic"
```

---

### Task 6: 定时预警任务

**Files:**
- Modify: `app.py`

**Step 1: 实现定时任务**

```python
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import atexit

def check_and_send_warnings():
    """检查所有用户并发送预警邮件"""
    from models import User, get_db

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    conn.close()

    now = datetime.now()

    for user_row in users:
        user = User.get_by_id(user_row['id'])

        if not user.last_checkin:
            # 从未签到，不发送预警
            continue

        # 计算距离上次签到的小时数
        last_checkin_time = datetime.strptime(user.last_checkin, '%Y-%m-%d %H:%M:%S')
        hours_since_checkin = (now - last_checkin_time).total_seconds() / 3600

        # 检查是否超过预警间隔
        if hours_since_checkin >= user.warning_interval_hours:
            # 检查是否已经发送过预警（24小时内不重复发送）
            if user.last_warning_sent:
                last_warning_time = datetime.strptime(user.last_warning_sent, '%Y-%m-%d %H:%M:%S')
                hours_since_warning = (now - last_warning_time).total_seconds() / 3600
                if hours_since_warning < 24:
                    continue

            # 发送预警邮件
            from utils.email import send_warning_email
            success = send_warning_email(user.emergency_email, user.name)

            if success:
                user.update_last_warning_sent()
                print(f"已向 {user.emergency_email} 发送预警邮件 (用户: {user.name})")

# 启动定时任务
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_and_send_warnings, trigger="interval", minutes=1)
scheduler.start()

# 程序退出时关闭调度器
atexit.register(lambda: scheduler.shutdown())
```

**Step 2: 测试定时任务**

启动应用后，可以在另一个进程中测试：
```python
from app import check_and_send_warnings
check_and_send_warnings()
```

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add scheduled warning task"
```

---

### Task 7: 集成测试和启动脚本

**Files:**
- Create: `run.py`

**Step 1: 创建启动脚本**

```python
#!/usr/bin/env python
"""启动 WebCare 应用"""
from app import app, init_db
import os

if __name__ == '__main__':
    # 初始化数据库
    if not os.path.exists('webcare.db'):
        init_db()
        print("数据库已初始化")

    print("启动 WebCare 应用...")
    print("访问 http://localhost:5000 开始使用")
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**Step 2: 运行完整测试**

Run: `pytest tests/ -v`
Expected: 所有测试通过

**Step 3: Commit**

```bash
git add run.py
git commit -m "chore: add run script and final integration test"
```

---

### Task 8: 环境变量配置说明

**Files:**
- Create: `.env.example`

**Step 1: 创建环境变量示例**

```bash
# Flask 配置
SECRET_KEY=your-secret-key-here

# QQ邮箱 SMTP 配置
MAIL_USERNAME=your-qq-email@qq.com
MAIL_PASSWORD=your-qq-authorization-code
```

**Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add environment variables example"
```

---

## 执行选项

**计划完成并保存到 `docs/plans/2026-02-26-webcare-design.md`。两个执行选项：**

**1. Subagent-Driven (本会话)** - 我为每个任务分派一个新的子代理，任务之间进行审查，快速迭代

**2. Parallel Session (单独会话)** - 在新会话中打开 executing-plans，批量执行并设置检查点

**你选择哪种方式？**

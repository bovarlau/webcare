from flask import Flask, render_template, request, redirect, url_for
from config import Config
from models import User, CheckIn, init_db, get_db
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import atexit
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
                           last_checkin=user.last_checkin,
                           token=token)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    token = request.args.get('token')
    if not token:
        return redirect(url_for('index'))

    user = User.get_by_token(token)
    if not user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            warning_interval = int(request.form.get('warning_interval', 48))
        except ValueError:
            warning_interval = 48  # 默认值，如果转换失败使用默认值
        user.update_warning_interval(warning_interval)
        return render_template('settings.html', user=user, success=True, token=token)

    return render_template('settings.html', user=user, token=token)


def check_and_send_warnings():
    """检查所有用户并发送预警邮件"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
    finally:
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


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)

from flask import Flask, render_template, request, redirect, url_for
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


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)

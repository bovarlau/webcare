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

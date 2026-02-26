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

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock
from utils.email import send_warning_email

@patch('utils.email.smtplib.SMTP_SSL')
def test_send_warning_email(mock_smtp):
    # Mock SMTP_SSL 返回的上下文管理器
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

    result = send_warning_email('test@example.com', '张三')

    assert result == True
    mock_server.login.assert_called_once()
    mock_server.sendmail.assert_called_once()

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.email import send_warning_email

def test_send_warning_email():
    # 这个测试会因为函数不存在而失败
    result = send_warning_email('test@example.com', '张三')
    assert result == True

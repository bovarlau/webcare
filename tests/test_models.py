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

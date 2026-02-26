"""
数据库模型模块
包含 User 和 CheckIn 模型
"""
import sqlite3
import secrets
from datetime import datetime
from config import Config


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_db()
    try:
        cursor = conn.cursor()

        # 创建 users 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                emergency_email TEXT NOT NULL,
                warning_interval_hours INTEGER DEFAULT 48,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checkin TIMESTAMP,
                last_warning_sent TIMESTAMP,
                unique_user_token TEXT UNIQUE NOT NULL
            )
        ''')

        # 创建 checkins 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                checkin_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        conn.commit()
    finally:
        conn.close()


class User:
    """用户模型类"""

    def __init__(self, id=None, name=None, emergency_email=None,
                 warning_interval_hours=48, created_at=None,
                 last_checkin=None, last_warning_sent=None,
                 unique_user_token=None):
        """初始化用户属性"""
        self.id = id
        self.name = name
        self.emergency_email = emergency_email
        self.warning_interval_hours = warning_interval_hours
        self.created_at = created_at
        self.last_checkin = last_checkin
        self.last_warning_sent = last_warning_sent
        self.unique_user_token = unique_user_token

    @classmethod
    def _from_row(cls, row):
        """从数据库行创建用户对象"""
        if row is None:
            return None
        return cls(
            id=row['id'],
            name=row['name'],
            emergency_email=row['emergency_email'],
            warning_interval_hours=row['warning_interval_hours'],
            created_at=row['created_at'],
            last_checkin=row['last_checkin'],
            last_warning_sent=row['last_warning_sent'],
            unique_user_token=row['unique_user_token']
        )

    @classmethod
    def create(cls, name, emergency_email):
        """创建新用户，生成唯一 token"""
        unique_token = secrets.token_urlsafe(32)

        conn = get_db()
        try:
            cursor = conn.cursor()

            cursor.execute(
                '''
                INSERT INTO users (name, emergency_email, unique_user_token)
                VALUES (?, ?, ?)
                ''',
                (name, emergency_email, unique_token)
            )

            conn.commit()
            user_id = cursor.lastrowid
        finally:
            conn.close()

        return cls.get_by_id(user_id)

    @classmethod
    def get_by_id(cls, user_id):
        """通过 ID 获取用户"""
        conn = get_db()
        try:
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()

            return cls._from_row(row)
        finally:
            conn.close()

    @classmethod
    def get_by_token(cls, token):
        """通过 token 获取用户"""
        conn = get_db()
        try:
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM users WHERE unique_user_token = ?', (token,))
            row = cursor.fetchone()

            return cls._from_row(row)
        finally:
            conn.close()

    def update_last_checkin(self):
        """更新最后签到时间"""
        conn = get_db()
        try:
            cursor = conn.cursor()

            cursor.execute(
                'UPDATE users SET last_checkin = CURRENT_TIMESTAMP WHERE id = ?',
                (self.id,)
            )

            conn.commit()
        finally:
            conn.close()

        self.last_checkin = datetime.now()

    def update_warning_interval(self, hours):
        """更新预警间隔"""
        conn = get_db()
        try:
            cursor = conn.cursor()

            cursor.execute(
                'UPDATE users SET warning_interval_hours = ? WHERE id = ?',
                (hours, self.id)
            )

            conn.commit()
        finally:
            conn.close()

        self.warning_interval_hours = hours

    def update_last_warning_sent(self):
        """更新最后发送预警时间"""
        conn = get_db()
        try:
            cursor = conn.cursor()

            cursor.execute(
                'UPDATE users SET last_warning_sent = CURRENT_TIMESTAMP WHERE id = ?',
                (self.id,)
            )

            conn.commit()
        finally:
            conn.close()

        self.last_warning_sent = datetime.now()


class CheckIn:
    """签到记录模型类"""

    def __init__(self, id=None, user_id=None, checkin_time=None):
        """初始化签到记录"""
        self.id = id
        self.user_id = user_id
        self.checkin_time = checkin_time

    @classmethod
    def _from_row(cls, row):
        """从数据库行创建签到对象"""
        if row is None:
            return None
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            checkin_time=row['checkin_time']
        )

    @classmethod
    def create(cls, user_id):
        """创建签到记录"""
        conn = get_db()
        try:
            cursor = conn.cursor()

            cursor.execute(
                'INSERT INTO checkins (user_id) VALUES (?)',
                (user_id,)
            )

            conn.commit()
            checkin_id = cursor.lastrowid
        finally:
            conn.close()

        # 更新用户的最后签到时间
        user = User.get_by_id(user_id)
        user.update_last_checkin()

        return cls.get_by_id(checkin_id)

    @classmethod
    def get_by_id(cls, checkin_id):
        """通过 ID 获取签到记录"""
        conn = get_db()
        try:
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM checkins WHERE id = ?', (checkin_id,))
            row = cursor.fetchone()

            return cls._from_row(row)
        finally:
            conn.close()

    @classmethod
    def get_by_user(cls, user_id, limit=10):
        """获取用户的签到记录"""
        conn = get_db()
        try:
            cursor = conn.cursor()

            cursor.execute(
                'SELECT * FROM checkins WHERE user_id = ? ORDER BY checkin_time DESC LIMIT ?',
                (user_id, limit)
            )
            rows = cursor.fetchall()

            return [cls._from_row(row) for row in rows]
        finally:
            conn.close()

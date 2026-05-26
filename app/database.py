# app/database.py
import pymysql
from contextlib import contextmanager
from flask import g
from app.config import Config
import hashlib
from datetime import date, timedelta


class SimpleDatabaseManager:
    """简单的数据库管理器（使用pymysql）"""

    def __init__(self):
        # 过滤掉连接池专用参数
        self.config = {
            'host': Config.DB_CONFIG.get('host', 'localhost'),
            'port': Config.DB_CONFIG.get('port', 3306),
            'user': Config.DB_CONFIG.get('user', 'root'),
            'password': Config.DB_CONFIG.get('password', '123456'),
            'database': Config.DB_CONFIG.get('database', 'library_system'),
            'charset': Config.DB_CONFIG.get('charset', 'utf8mb4'),
            'autocommit': False
        }

    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = None
        try:
            conn = pymysql.connect(**self.config)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_cursor(self, dictionary=True):
        """获取游标"""
        with self.get_connection() as conn:
            if dictionary:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
            else:
                cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    def fetch_one(self, sql, params=None):
        """查询单条记录"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchone()

    def fetch_all(self, sql, params=None):
        """查询多条记录"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()

    def execute(self, sql, params=None):
        """执行SQL（INSERT/UPDATE/DELETE）"""
        with self.get_cursor(dictionary=False) as cursor:
            affected = cursor.execute(sql, params or ())
            return affected

    def insert(self, table, data):
        """插入数据"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute(sql, list(data.values()))

    def update(self, table, data, where, where_params=None):
        """更新数据"""
        set_clause = ', '.join([f"{k}=%s" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = list(data.values()) + (where_params or [])
        return self.execute(sql, params)

    def delete(self, table, where, params=None):
        """删除数据"""
        sql = f"DELETE FROM {table} WHERE {where}"
        return self.execute(sql, params)

    def count(self, table, where=None, params=None):
        """统计记录数"""
        sql = f"SELECT COUNT(*) as count FROM {table}"
        if where:
            sql += f" WHERE {where}"
        result = self.fetch_one(sql, params)
        return result['count'] if result else 0


# 创建全局数据库管理器实例
db_manager = SimpleDatabaseManager()


# 图书相关的数据库操作函数
class BookModel:
    """图书模型"""

    @staticmethod
    def get_all(page=1, per_page=20, keyword=None):
        """获取所有图书（分页）"""
        offset = (page - 1) * per_page

        # 分别获取数据和总数（使用不同的cursor）
        if keyword:
            # 获取数据
            books = db_manager.fetch_all("""
                SELECT id, title, author, publisher, call_number, 
                       total_copies, available_copies, borrow_count
                FROM books 
                WHERE title LIKE %s OR author LIKE %s OR isbn LIKE %s
                ORDER BY id
                LIMIT %s OFFSET %s
            """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', per_page, offset))

            # 获取总数
            total_result = db_manager.fetch_one("""
                SELECT COUNT(*) as total FROM books 
                WHERE title LIKE %s OR author LIKE %s OR isbn LIKE %s
            """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
        else:
            # 获取数据
            books = db_manager.fetch_all("""
                SELECT id, title, author, publisher, call_number, 
                       total_copies, available_copies, borrow_count
                FROM books 
                ORDER BY id
                LIMIT %s OFFSET %s
            """, (per_page, offset))

            # 获取总数
            total_result = db_manager.fetch_one("SELECT COUNT(*) as total FROM books")

        total = total_result['total'] if total_result else 0
        return books, total

    @staticmethod
    def get_by_id(book_id):
        """根据ID获取图书详情"""
        return db_manager.fetch_one("""
            SELECT id, original_id, title, author, publisher, isbn,
                   publish_year, category_code, call_number, 
                   total_copies, available_copies, location, 
                   description, borrow_count
            FROM books WHERE id = %s
        """, (book_id,))

    @staticmethod
    def count():
        """获取图书总数"""
        result = db_manager.fetch_one("SELECT COUNT(*) as total FROM books")
        return result['total'] if result else 0


    @staticmethod
    def create(book_data):
        """创建新图书"""
        return db_manager.insert('books', {
            'title': book_data.get('title'),
            'author': book_data.get('author'),
            'publisher': book_data.get('publisher'),
            'isbn': book_data.get('isbn'),
            'publish_year': book_data.get('publish_year'),
            'category_code': book_data.get('category_code'),
            'call_number': book_data.get('call_number'),
            'total_copies': book_data.get('total_copies', 1),
            'available_copies': book_data.get('total_copies', 1)
        })

    @staticmethod
    def update(book_id, book_data):
        """更新图书信息"""
        # 过滤掉None值
        update_data = {k: v for k, v in book_data.items() if v is not None}
        if not update_data:
            return 0

        set_clause = ', '.join([f"{k}=%s" for k in update_data.keys()])
        sql = f"UPDATE books SET {set_clause} WHERE id = %s"
        params = list(update_data.values()) + [book_id]
        return db_manager.execute(sql, params)

    @staticmethod
    def delete(book_id):
        """删除图书"""
        return db_manager.execute("DELETE FROM books WHERE id = %s", (book_id,))

    @staticmethod
    def search(keyword, page=1, per_page=20):
        """搜索图书"""
        offset = (page - 1) * per_page
        books = db_manager.fetch_all("""
            SELECT id, title, author, publisher, call_number, 
                   total_copies, available_copies
            FROM books 
            WHERE title LIKE %s OR author LIKE %s OR isbn LIKE %s
            LIMIT %s OFFSET %s
        """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', per_page, offset))

        total_result = db_manager.fetch_one("""
            SELECT COUNT(*) as total FROM books 
            WHERE title LIKE %s OR author LIKE %s OR isbn LIKE %s
        """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))

        total = total_result['total'] if total_result else 0
        return books, total


class UserModel:
    """用户模型"""

    @staticmethod
    def get_by_id(user_id):
        """根据ID获取用户"""
        return db_manager.fetch_one("""
            SELECT id, username, real_name, email, phone, role, status, 
                   borrow_count, total_borrow, created_at
            FROM users WHERE id = %s
        """, (user_id,))

    @staticmethod
    def get_by_username(username):
        """根据用户名获取用户"""
        return db_manager.fetch_one("""
            SELECT id, username, real_name, email, phone, role, status, 
                   borrow_count, total_borrow
            FROM users WHERE username = %s
        """, (username,))

    @staticmethod
    def count_students():
        """获取学生总数"""
        result = db_manager.fetch_one("SELECT COUNT(*) as total FROM users WHERE role = 'student'")
        return result['total'] if result else 0


    @staticmethod
    def authenticate(username, password):
        """用户认证"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return db_manager.fetch_one("""
            SELECT id, username, real_name, role, status 
            FROM users 
            WHERE username = %s AND password_hash = SHA2(%s, 256)
        """, (username, password))

    @staticmethod
    def create(user_data):
        """创建新用户"""
        password_hash = hashlib.sha256(user_data.get('password', '123456').encode()).hexdigest()
        return db_manager.insert('users', {
            'username': user_data.get('username'),
            'password_hash': password_hash,
            'real_name': user_data.get('real_name'),
            'email': user_data.get('email'),
            'phone': user_data.get('phone'),
            'role': user_data.get('role', 'student')
        })

    @staticmethod
    def get_all_students(page=1, per_page=20):
        """获取所有学生"""
        offset = (page - 1) * per_page
        users = db_manager.fetch_all("""
            SELECT id, username, real_name, email, phone, status, 
                   borrow_count, total_borrow, created_at
            FROM users 
            WHERE role = 'student'
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (per_page, offset))

        total_result = db_manager.fetch_one("SELECT COUNT(*) as total FROM users WHERE role = 'student'")
        total = total_result['total'] if total_result else 0
        return users, total


# app/database.py 中的 BorrowModel 类

# app/database.py 中的 BorrowModel 类（完整版）

class BorrowModel:
    """借阅模型"""

    @staticmethod
    def get_user_borrowings(user_id, status=None):
        """获取用户的借阅记录"""
        if status:
            return db_manager.fetch_all("""
                SELECT br.*, b.title, b.author, b.call_number, b.publisher, b.id as book_id
                FROM borrow_records br
                JOIN books b ON br.book_id = b.id
                WHERE br.user_id = %s AND br.status = %s
                ORDER BY br.borrow_date DESC
            """, (user_id, status))
        else:
            return db_manager.fetch_all("""
                SELECT br.*, b.title, b.author, b.call_number, b.publisher, b.id as book_id
                FROM borrow_records br
                JOIN books b ON br.book_id = b.id
                WHERE br.user_id = %s
                ORDER BY br.borrow_date DESC
            """, (user_id,))

    @staticmethod
    def get_all_borrowings(page=1, per_page=20, status=None):
        """获取所有借阅记录（管理员）"""
        offset = (page - 1) * per_page

        if status:
            records = db_manager.fetch_all("""
                SELECT br.*, b.title, b.author, b.call_number,
                       u.username, u.real_name
                FROM borrow_records br
                JOIN books b ON br.book_id = b.id
                JOIN users u ON br.user_id = u.id
                WHERE br.status = %s
                ORDER BY br.borrow_date DESC
                LIMIT %s OFFSET %s
            """, (status, per_page, offset))

            total_result = db_manager.fetch_one("""
                SELECT COUNT(*) as total FROM borrow_records WHERE status = %s
            """, (status,))
        else:
            records = db_manager.fetch_all("""
                SELECT br.*, b.title, b.author, b.call_number,
                       u.username, u.real_name
                FROM borrow_records br
                JOIN books b ON br.book_id = b.id
                JOIN users u ON br.user_id = u.id
                ORDER BY br.borrow_date DESC
                LIMIT %s OFFSET %s
            """, (per_page, offset))

            total_result = db_manager.fetch_one("SELECT COUNT(*) as total FROM borrow_records")

        total = total_result['total'] if total_result else 0
        return records, total

    @staticmethod
    def borrow_book(user_id, book_id, days=30):
        """借书"""
        # 检查库存
        book = db_manager.fetch_one("SELECT available_copies FROM books WHERE id = %s", (book_id,))
        if not book:
            raise Exception("图书不存在")
        if book['available_copies'] <= 0:
            raise Exception("图书库存不足")

        # 检查用户借阅数量
        user = db_manager.fetch_one("SELECT borrow_count, status FROM users WHERE id = %s", (user_id,))
        if not user:
            raise Exception("用户不存在")
        if user['status'] == 1:
            raise Exception("用户已被冻结")
        if user['borrow_count'] >= Config.MAX_BORROW_PER_USER:
            raise Exception(f"最多只能借阅{Config.MAX_BORROW_PER_USER}本书")

        # 检查是否重复借阅
        existing = db_manager.fetch_one("""
            SELECT id FROM borrow_records 
            WHERE user_id = %s AND book_id = %s AND status IN ('borrowed', 'overdue')
        """, (user_id, book_id))
        if existing:
            raise Exception("您已经借阅了这本书，请先归还")

        # 更新库存
        db_manager.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = %s", (book_id,))

        # 创建借阅记录
        borrow_date = date.today()
        due_date = borrow_date + timedelta(days=days)

        record_id = db_manager.insert('borrow_records', {
            'user_id': user_id,
            'book_id': book_id,
            'borrow_date': borrow_date,
            'due_date': due_date,
            'status': 'borrowed'
        })

        # 更新用户借阅计数
        db_manager.execute("UPDATE users SET borrow_count = borrow_count + 1 WHERE id = %s", (user_id,))

        # 更新图书借阅次数
        db_manager.execute("UPDATE books SET borrow_count = borrow_count + 1 WHERE id = %s", (book_id,))

        return record_id

    @staticmethod
    def return_book(record_id):
        """还书"""
        # 获取借阅记录
        record = db_manager.fetch_one("""
            SELECT user_id, book_id, due_date, status FROM borrow_records 
            WHERE id = %s
        """, (record_id,))

        if not record:
            raise Exception("借阅记录不存在")

        if record['status'] == 'returned':
            raise Exception("该书已经归还过了")

        user_id, book_id, due_date = record['user_id'], record['book_id'], record['due_date']

        # 计算罚款
        fine = 0
        if date.today() > due_date:
            days_overdue = (date.today() - due_date).days
            fine = days_overdue * Config.FINE_PER_DAY

        # 更新借阅记录
        db_manager.execute("""
            UPDATE borrow_records 
            SET return_date = %s, status = 'returned', fine = %s
            WHERE id = %s
        """, (date.today(), fine, record_id))

        # 增加库存
        db_manager.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = %s", (book_id,))

        # 更新用户借阅计数（减少）
        db_manager.execute("UPDATE users SET borrow_count = borrow_count - 1 WHERE id = %s", (user_id,))

        return fine

    @staticmethod
    def get_statistics():
        """获取借阅统计"""
        # 总借阅数
        total_result = db_manager.fetch_one("SELECT COUNT(*) as count FROM borrow_records")
        total_borrow = total_result['count'] if total_result else 0

        # 当前借阅数
        current_result = db_manager.fetch_one(
            "SELECT COUNT(*) as count FROM borrow_records WHERE status IN ('borrowed', 'overdue')")
        current_borrow = current_result['count'] if current_result else 0

        # 逾期数
        overdue_result = db_manager.fetch_one("SELECT COUNT(*) as count FROM borrow_records WHERE status = 'overdue'")
        overdue_borrow = overdue_result['count'] if overdue_result else 0

        # 热门图书
        hot_books = db_manager.fetch_all("""
            SELECT b.id, b.title, b.author, COUNT(br.id) as borrow_times
            FROM books b
            JOIN borrow_records br ON b.id = br.book_id
            GROUP BY b.id, b.title, b.author
            ORDER BY borrow_times DESC
            LIMIT 10
        """)

        return {
            'total_borrow': total_borrow,
            'current_borrow': current_borrow,
            'overdue_borrow': overdue_borrow,
            'hot_books': hot_books
        }

# 创建全局实例
book_model = BookModel()
user_model = UserModel()
borrow_model = BorrowModel()


# Flask上下文管理
def get_db():
    """获取数据库管理器（用于Flask上下文）"""
    if 'db' not in g:
        g.db = SimpleDatabaseManager()
    return g.db


def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        pass  # SimpleDatabaseManager会自动关闭连接
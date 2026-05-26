# app/config.py
import os
class Config:
    """应用配置类"""

    # ============================================
    # Flask基础配置
    # ============================================
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'library-management-system-secret-key-2025'
    DEBUG = True

    # ============================================
    # 数据库配置（使用PyMySQL）
    # ============================================
    # MySQL连接配置
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '123456')  # 请修改为您的数据库密码
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'library_system')


    # ============================================
    # 原生MySQL连接池配置（不使用ORM时）
    # ============================================
    DB_CONFIG = {
        'host': MYSQL_HOST,
        'port': MYSQL_PORT,
        'user': MYSQL_USER,
        'password': MYSQL_PASSWORD,
        'database': MYSQL_DATABASE,
        'charset': 'utf8mb4',
        'use_unicode': True,
        'autocommit': False,
        'pool_name': 'library_pool',
        'pool_size': 10
    }

    # ============================================
    # 业务配置
    # ============================================
    # 分页配置
    BOOKS_PER_PAGE = 20
    MAX_BORROW_PER_USER = 5  # 每人最多借阅数量
    BORROW_DAYS = 30  # 默认借阅天数

    # 罚款配置（元/天）
    FINE_PER_DAY = 0.1

    # ============================================
    # 文件上传配置
    # ============================================
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'jpg', 'png', 'gif'}

    # ============================================
    # 会话配置
    # ============================================
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1小时

    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 确保上传目录存在
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    DB_CONFIG = {**Config.DB_CONFIG, 'database': 'library_system_dev'}


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')  # 必须从环境变量获取
    SQLALCHEMY_ECHO = False

    # 生产环境使用更强的密码
    DB_CONFIG = {**Config.DB_CONFIG, 'password': os.environ.get('DB_PASSWORD')}


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@localhost:3306/library_system_test'
    DB_CONFIG = {**Config.DB_CONFIG, 'database': 'library_system_test'}


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


# 创建Flask应用时使用的配置
def get_config():
    """获取当前配置"""
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, DevelopmentConfig)
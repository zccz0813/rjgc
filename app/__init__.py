# app/__init__.py
from flask import Flask
from app.config import Config

app = Flask(__name__)
app.config.from_object(Config)

# 导入并注册蓝图
from app.auth import auth_bp
from app.books import books_bp
from app.borrow import borrow_bp
from app.admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(books_bp)
app.register_blueprint(borrow_bp)
app.register_blueprint(admin_bp)

# 首页重定向
@app.route('/')
def index():
    from flask import redirect, url_for
    return redirect(url_for('auth.login'))
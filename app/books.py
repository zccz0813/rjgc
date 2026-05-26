# app/books.py- 图书模块
from flask import Blueprint, render_template, request, session, flash, redirect, url_for
from app.database import book_model

books_bp = Blueprint('books', __name__, url_prefix='/books')


@books_bp.route('/')
def list():
    """图书列表"""
    if 'user_id' not in session:
        flash('请先登录', 'warning')
        return redirect(url_for('auth.login'))

    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '')

    if keyword:
        books, total = book_model.search(keyword, page=page)
    else:
        books, total = book_model.get_all(page=page)

    return render_template('books/list.html',
                           books=books,
                           keyword=keyword,
                           page=page,
                           total=total,
                           per_page=20)


@books_bp.route('/<int:book_id>')
def detail(book_id):
    """图书详情"""
    if 'user_id' not in session:
        flash('请先登录', 'warning')
        return redirect(url_for('auth.login'))

    book = book_model.get_by_id(book_id)
    if not book:
        flash('图书不存在', 'danger')
        return redirect(url_for('books.list'))

    return render_template('books/detail.html', book=book)
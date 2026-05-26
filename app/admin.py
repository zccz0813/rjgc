# app/admin.py - 管理员模块
from flask import Blueprint, render_template, request, session, flash, redirect, url_for
from app.database import book_model, user_model, borrow_model

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """管理员权限装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('无权限访问', 'danger')
            return redirect(url_for('books.list'))
        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route('/')
@admin_required
def dashboard():
    """管理员后台首页"""
    stats = borrow_model.get_statistics()
    user_count = user_model.count_students()
    book_count = book_model.count()

    return render_template('admin/dashboard.html',
                           stats=stats,
                           user_count=user_count,
                           book_count=book_count)


@admin_bp.route('/books')
@admin_required
def manage_books():
    """图书管理"""
    page = request.args.get('page', 1, type=int)
    books, total = book_model.get_all(page=page)

    return render_template('admin/books.html', books=books, total=total, page=page)


@admin_bp.route('/books/add', methods=['GET', 'POST'])
@admin_required
def add_book():
    """添加图书"""
    if request.method == 'POST':
        book_data = {
            'title': request.form.get('title'),
            'author': request.form.get('author'),
            'publisher': request.form.get('publisher'),
            'isbn': request.form.get('isbn'),
            'publish_year': request.form.get('publish_year'),
            'category_code': request.form.get('category_code'),
            'call_number': request.form.get('call_number'),
            'total_copies': int(request.form.get('total_copies', 1))
        }

        book_model.create(book_data)
        flash('图书添加成功', 'success')
        return redirect(url_for('admin.manage_books'))

    return render_template('admin/book_form.html')


@admin_bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@admin_required
def edit_book(book_id):
    """编辑图书"""
    book = book_model.get_by_id(book_id)
    if not book:
        flash('图书不存在', 'danger')
        return redirect(url_for('admin.manage_books'))

    if request.method == 'POST':
        book_data = {
            'title': request.form.get('title'),
            'author': request.form.get('author'),
            'publisher': request.form.get('publisher'),
            'isbn': request.form.get('isbn'),
            'publish_year': request.form.get('publish_year'),
            'category_code': request.form.get('category_code'),
            'call_number': request.form.get('call_number'),
            'total_copies': int(request.form.get('total_copies', 1))
        }

        book_model.update(book_id, book_data)
        flash('图书更新成功', 'success')
        return redirect(url_for('admin.manage_books'))

    return render_template('admin/book_form.html', book=book)


@admin_bp.route('/books/delete/<int:book_id>', methods=['POST'])
@admin_required
def delete_book(book_id):
    """删除图书"""
    book_model.delete(book_id)
    flash('图书删除成功', 'success')
    return redirect(url_for('admin.manage_books'))


@admin_bp.route('/users')
@admin_required
def manage_users():
    """用户管理"""
    page = request.args.get('page', 1, type=int)
    users, total = user_model.get_all_students(page=page)

    return render_template('admin/users.html', users=users, total=total, page=page)


@admin_bp.route('/borrowings')
@admin_required
def manage_borrowings():
    """借阅管理"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')

    records, total = borrow_model.get_all_borrowings(page=page, status=status if status else None)

    return render_template('admin/borrowings.html', records=records, total=total, page=page, status=status)
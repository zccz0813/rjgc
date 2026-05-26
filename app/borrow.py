# app/borrow.py- 借阅模块
from flask import Blueprint, render_template, request, session, flash, redirect, url_for
from app.database import borrow_model, book_model

borrow_bp = Blueprint('borrow', __name__, url_prefix='/borrow')


@borrow_bp.route('/my')
def my_borrowings():
    """我的借阅"""
    if 'user_id' not in session:
        flash('请先登录', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    borrowings = borrow_model.get_user_borrowings(user_id)

    return render_template('borrow/my.html', borrowings=borrowings)


@borrow_bp.route('/book/<int:book_id>', methods=['POST'])
def borrow_book(book_id):
    """借书"""
    if 'user_id' not in session:
        flash('请先登录', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    try:
        # 检查用户当前借阅数量
        from app.database import db_manager
        user = db_manager.fetch_one("SELECT borrow_count, status FROM users WHERE id = %s", (user_id,))

        if not user:
            flash('用户不存在', 'danger')
            return redirect(url_for('books.list'))

        if user['status'] == 1:
            flash('账号已被冻结，无法借书', 'danger')
            return redirect(url_for('books.list'))

        if user['borrow_count'] >= 5:
            flash('您已达到最大借阅数量（5本），请先归还部分图书', 'warning')
            return redirect(url_for('borrow.my_borrowings'))

        # 执行借书
        from app.database import borrow_model
        borrow_model.borrow_book(user_id, book_id)

        flash('借书成功！请按时归还', 'success')
    except Exception as e:
        flash(str(e), 'danger')

    return redirect(url_for('books.detail', book_id=book_id))


@borrow_bp.route('/return/<int:record_id>', methods=['POST'])
def return_book(record_id):
    """还书"""
    if 'user_id' not in session:
        flash('请先登录', 'warning')
        return redirect(url_for('auth.login'))

    try:
        from app.database import db_manager, borrow_model

        # 先检查记录是否存在且状态正确
        record = db_manager.fetch_one(
            "SELECT id, status FROM borrow_records WHERE id = %s AND user_id = %s",
            (record_id, session['user_id'])
        )

        if not record:
            flash('借阅记录不存在', 'danger')
            return redirect(url_for('borrow.my_borrowings'))

        if record['status'] == 'returned':
            flash('该书已归还过', 'info')
            return redirect(url_for('borrow.my_borrowings'))

        # 执行还书
        fine = borrow_model.return_book(record_id)

        if fine > 0:
            flash(f'还书成功！逾期罚款：{fine}元', 'warning')
        else:
            flash('还书成功！', 'success')

    except Exception as e:
        flash(f'还书失败: {str(e)}', 'danger')

    return redirect(url_for('borrow.my_borrowings'))
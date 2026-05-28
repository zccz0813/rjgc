# app/books.py- 图书模块
# app/books.py
from flask import Blueprint, render_template, request, session, flash, redirect, url_for
from app.database import db_manager, book_model

books_bp = Blueprint('books', __name__, url_prefix='/books')


@books_bp.route('/')
def list():
    """图书列表（带分类筛选）"""
    if 'user_id' not in session:
        flash('请先登录', 'warning')
        return redirect(url_for('auth.login'))

    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '')
    category = request.args.get('category', '')
    sort = request.args.get('sort', 'id')  # id, borrow_count, title

    # 获取所有分类
    categories = db_manager.fetch_all("""
        SELECT id, code, name, icon, sort_order 
        FROM categories 
        ORDER BY sort_order
    """)

    # 获取热门分类（图书数量最多的前6个）
    hot_categories = db_manager.fetch_all("""
        SELECT c.id, c.code, c.name, c.icon, COUNT(b.id) as book_count
        FROM categories c
        LEFT JOIN books b ON b.category_id = c.id
        GROUP BY c.id
        ORDER BY book_count DESC
        LIMIT 6
    """)

    # 构建查询条件
    conditions = []
    params = []

    if keyword:
        conditions.append("(b.title LIKE %s OR b.author LIKE %s OR b.isbn LIKE %s)")
        params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

    if category:
        conditions.append("b.category_id = %s")
        params.append(category)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # 排序
    sort_map = {
        'id': 'b.id DESC',
        'borrow_count': 'b.borrow_count DESC',
        'title': 'b.title ASC'
    }
    order_by = sort_map.get(sort, 'b.id DESC')

    # 分页
    per_page = 12
    offset = (page - 1) * per_page

    # 获取图书数据
    books = db_manager.fetch_all(f"""
        SELECT b.*, c.name as category_name, c.icon as category_icon
        FROM books b
        LEFT JOIN categories c ON b.category_id = c.id
        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
    """, params + [per_page, offset])

    # 获取总数
    total_result = db_manager.fetch_one(f"""
        SELECT COUNT(*) as total FROM books b
        WHERE {where_clause}
    """, params)
    total = total_result['total'] if total_result else 0

    # 获取当前分类名称
    current_category = None
    if category:
        current_category = db_manager.fetch_one(
            "SELECT id, name FROM categories WHERE id = %s", (category,)
        )

    return render_template('books/list.html',
                           books=books,
                           categories=categories,
                           hot_categories=hot_categories,
                           current_category=current_category,
                           keyword=keyword,
                           category=category,
                           sort=sort,
                           page=page,
                           total=total,
                           per_page=per_page)


@books_bp.route('/category/<int:category_id>')
def by_category(category_id):
    """按分类浏览图书"""
    if 'user_id' not in session:
        flash('请先登录', 'warning')
        return redirect(url_for('auth.login'))

    # 重定向到图书列表并带上分类参数
    return redirect(url_for('books.list', category=category_id))


@books_bp.route('/<int:book_id>')
def detail(book_id):
    """图书详情"""
    if 'user_id' not in session:
        flash('请先登录', 'warning')
        return redirect(url_for('auth.login'))

    book = db_manager.fetch_one("""
        SELECT b.*, c.name as category_name, c.icon as category_icon
        FROM books b
        LEFT JOIN categories c ON b.category_id = c.id
        WHERE b.id = %s
    """, (book_id,))

    if not book:
        flash('图书不存在', 'danger')
        return redirect(url_for('books.list'))

    # 获取同分类推荐图书
    similar_books = []
    if book.get('category_id'):
        similar_books = db_manager.fetch_all("""
            SELECT id, title, author, available_copies
            FROM books 
            WHERE category_id = %s AND id != %s
            LIMIT 4
        """, (book['category_id'], book_id))

    return render_template('books/detail.html', book=book, similar_books=similar_books)

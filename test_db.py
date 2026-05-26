#!/usr/bin/env python
# test_db.py
import sys
from app.config import Config
from app.database import db_manager, book_model, user_model, borrow_model


def test_connection():
    """测试数据库连接"""
    print("=" * 50)
    print("测试数据库连接")
    print("=" * 50)

    print("\n1. 测试数据库连接...")
    try:
        result = db_manager.fetch_one("SELECT VERSION() as version")
        print(f"   ✓ 连接成功，MySQL版本: {result['version']}")
    except Exception as e:
        print(f"   ✗ 连接失败: {e}")
        return False

    return True


def test_operations():
    """测试基本操作"""
    print("\n" + "=" * 50)
    print("测试数据库操作")
    print("=" * 50)

    # 测试查询用户表
    print("\n1. 查询用户表...")
    try:
        users = db_manager.fetch_all("SELECT id, username, real_name, role FROM users LIMIT 5")
        if users:
            for user in users:
                print(f"   [{user['id']}] {user['username']} - {user['real_name']} ({user['role']})")
        else:
            print("   暂无用户数据")
    except Exception as e:
        print(f"   查询失败: {e}")

    # 测试图书统计
    print("\n2. 查询图书统计...")
    try:
        book_count = db_manager.count('books')
        print(f"   图书总数: {book_count}")
    except Exception as e:
        print(f"   查询失败: {e}")

    # 测试借阅统计
    print("\n3. 查询借阅统计...")
    try:
        borrow_count = db_manager.count('borrow_records')
        print(f"   借阅记录: {borrow_count}")

        if borrow_count > 0:
            overdue_count = db_manager.count('borrow_records', "status='overdue'")
            print(f"   逾期未还: {overdue_count}")
    except Exception as e:
        print(f"   查询失败: {e}")


def test_models():
    """测试模型层"""
    print("\n" + "=" * 50)
    print("测试模型层")
    print("=" * 50)

    # 测试图书模型
    print("\n1. 测试图书模型...")
    try:
        books, total = book_model.get_all(page=1, per_page=5)
        print(f"   共 {total} 本图书，显示前 {len(books)} 本:")
        for book in books:
            print(f"   - {book['title']} ({book.get('author', '未知')})")
    except Exception as e:
        print(f"   测试失败: {e}")

    # 测试用户模型
    print("\n2. 测试用户模型...")
    try:
        admin = user_model.get_by_username('admin')
        if admin:
            print(f"   找到管理员: {admin['real_name']}")
        else:
            print("   未找到管理员账户")
    except Exception as e:
        print(f"   测试失败: {e}")

    # 测试借阅统计
    print("\n3. 测试借阅统计...")
    try:
        stats = borrow_model.get_statistics()
        print(f"   总借阅: {stats['total_borrow']}")
        print(f"   当前借阅: {stats['current_borrow']}")
        print(f"   逾期数量: {stats['overdue_borrow']}")
    except Exception as e:
        print(f"   测试失败: {e}")


if __name__ == '__main__':
    if test_connection():
        test_operations()
        test_models()
        print("\n" + "=" * 50)
        print("✅ 数据库配置正确，可以使用！")
        print("=" * 50)
    else:
        print("\n❌ 数据库连接失败，请检查:")
        print("1. MySQL服务是否启动")
        print("2. app/config.py 中的数据库配置是否正确")
        print("3. 数据库 'library_system' 是否已创建")
        sys.exit(1)
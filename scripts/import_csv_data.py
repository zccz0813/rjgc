#!/usr/bin/env python
# scripts/import_csv_data.py
import sys
import os
import csv

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config
from app.database import db_manager


def import_books_from_csv(csv_path='library_books.csv'):
    """从CSV文件导入图书数据"""

    # 检查文件是否存在
    if not os.path.exists(csv_path):
        print(f"❌ 找不到文件: {csv_path}")
        print(f"   当前目录: {os.getcwd()}")
        return False

    # 统计信息
    total = 0
    inserted = 0
    skipped = 0
    errors = 0

    try:
        # 使用 utf-8-sig 编码自动处理 BOM 头
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            # 自动检测分隔符
            sample = f.read(1024)
            f.seek(0)
            delimiter = '\t' if '\t' in sample else ','

            reader = csv.DictReader(f, delimiter=delimiter)

            print(f"检测到分隔符: {'制表符' if delimiter == '\t' else '逗号'}")
            print(f"CSV列名: {list(reader.fieldnames)}")

            # 列名映射（支持中英文，现在不需要去除BOM了）
            col_map = {
                'title': ['书名', 'title', '名称', '图书名称', '图书名'],
                'author': ['作者', 'author'],
                'publisher': ['出版社', 'publisher', '出版单位'],
                'isbn': ['ISBN', 'isbn', 'ISBN号'],
                'publish_year': ['出版年', 'year', '出版年份', '出版日期'],
                'category_code': ['分类号', 'category_code', '分类'],
                'call_number': ['索书号', 'call_number', '索书号'],
                'original_id': ['记录ID', 'id', 'original_id', 'ID']
            }

            # 实际列名
            actual_map = {}
            for field, possible_names in col_map.items():
                for name in possible_names:
                    # 直接比较，因为 utf-8-sig 已经去除了 BOM
                    if name in reader.fieldnames:
                        actual_map[field] = name
                        break

            print(f"字段映射: {actual_map}")

            if 'title' not in actual_map:
                print("❌ 未找到书名字段，请检查CSV文件格式")
                print(f"   可用的列名: {reader.fieldnames}")
                return False

            for row_num, row in enumerate(reader, 1):
                total += 1

                # 提取数据
                title = row.get(actual_map.get('title'), '').strip()
                if not title:
                    print(f"  跳过第{row_num}行: 书名为空")
                    errors += 1
                    continue

                author = row.get(actual_map.get('author'), '').strip() if actual_map.get('author') else ''
                publisher = row.get(actual_map.get('publisher'), '').strip() if actual_map.get('publisher') else ''
                isbn = row.get(actual_map.get('isbn'), '').strip() if actual_map.get('isbn') else ''

                # 处理年份
                year_str = row.get(actual_map.get('publish_year'), '').strip() if actual_map.get('publish_year') else ''
                publish_year = None
                if year_str and year_str.isdigit():
                    publish_year = int(year_str)

                category_code = row.get(actual_map.get('category_code'), '').strip() if actual_map.get(
                    'category_code') else ''
                call_number = row.get(actual_map.get('call_number'), '').strip() if actual_map.get(
                    'call_number') else ''
                original_id = row.get(actual_map.get('original_id'), '').strip() if actual_map.get(
                    'original_id') else ''

                # 检查是否已存在（按original_id或ISBN或标题）
                if original_id:
                    existing = db_manager.fetch_one(
                        "SELECT id FROM books WHERE original_id = %s", (original_id,)
                    )
                elif isbn:
                    existing = db_manager.fetch_one(
                        "SELECT id FROM books WHERE isbn = %s", (isbn,)
                    )
                else:
                    existing = db_manager.fetch_one(
                        "SELECT id FROM books WHERE title = %s AND author = %s", (title, author)
                    )

                if existing:
                    print(f"  跳过: {title} (已存在)")
                    skipped += 1
                    continue

                # 插入图书
                try:
                    book_id = db_manager.insert('books', {
                        'original_id': original_id if original_id else None,
                        'title': title,
                        'author': author if author else None,
                        'publisher': publisher if publisher else None,
                        'isbn': isbn if isbn else None,
                        'publish_year': publish_year,
                        'category_code': category_code if category_code else None,
                        'call_number': call_number if call_number else None,
                        'total_copies': 1,
                        'available_copies': 1
                    })

                    inserted += 1
                    print(f"  ✓ 导入: {title} (ID: {book_id})")

                except Exception as e:
                    print(f"  ✗ 导入失败: {title} - {e}")
                    errors += 1

        print(f"\n{'=' * 50}")
        print(f"导入完成!")
        print(f"  总计: {total} 行")
        print(f"  新增: {inserted} 本")
        print(f"  跳过: {skipped} 本")
        print(f"  错误: {errors} 本")
        print(f"{'=' * 50}")

        return inserted > 0

    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_database():
    """检查数据库状态"""
    try:
        # 统计各表数据
        user_count = db_manager.count('users')
        book_count = db_manager.count('books')
        borrow_count = db_manager.count('borrow_records')

        print(f"\n📊 数据库统计:")
        print(f"  用户数: {user_count}")
        print(f"  图书数: {book_count}")
        print(f"  借阅记录: {borrow_count}")

        # 显示最新10本图书
        if book_count > 0:
            print(f"\n📚 最新图书:")
            books = db_manager.fetch_all(
                "SELECT id, title, author FROM books ORDER BY id DESC LIMIT 10"
            )
            for book in books:
                print(f"  [{book['id']}] {book['title']} - {book.get('author', '未知')}")

    except Exception as e:
        print(f"❌ 检查失败: {e}")


def clear_all_books():
    """清空所有图书数据（谨慎使用）"""
    confirm = input("⚠️ 确定要清空所有图书数据吗？(yes/no): ")
    if confirm.lower() == 'yes':
        count = db_manager.execute("DELETE FROM books")
        print(f"已删除 {count} 条图书记录")
        # 重置自增ID
        db_manager.execute("ALTER TABLE books AUTO_INCREMENT = 1")
        return True
    else:
        print("已取消")
        return False


if __name__ == '__main__':
    print("=" * 50)
    print("CSV图书数据导入工具")
    print("=" * 50)

    # 导入数据
    csv_file = 'library_books.csv'
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]

    # 可选：先清空数据
    if len(sys.argv) > 2 and sys.argv[2] == '--clear':
        clear_all_books()

    if import_books_from_csv(csv_file):
        check_database()
    else:
        print("\n请确保:")
        print("1. library_books.csv 文件在项目根目录")
        print("2. CSV文件编码为UTF-8")
        print("3. 数据库配置正确")
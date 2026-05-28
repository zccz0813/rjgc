#!/usr/bin/env python
# scripts/import_csv_data.py
import sys
import os
import csv
from collections import Counter

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config
from app.database import db_manager


def import_books_from_csv(csv_path='library_books.csv', show_progress=True):
    """从CSV文件导入图书数据"""

    # 检查文件是否存在
    if not os.path.exists(csv_path):
        print(f"❌ 找不到文件: {csv_path}")
        print(f"   当前目录: {os.getcwd()}")
        return False

    # 统计信息
    stats = {
        'total': 0,
        'inserted': 0,
        'skipped': 0,
        'errors': 0,
        'skipped_reasons': Counter()
    }

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

            # 列名映射（支持中英文）
            col_map = {
                'title': ['书名', 'title', '名称', '图书名称', '图书名', 'book_title'],
                'author': ['作者', 'author', '编著者', '著者'],
                'publisher': ['出版社', 'publisher', '出版单位', 'press'],
                'isbn': ['ISBN', 'isbn', 'ISBN号', 'isbn13', 'isbn10'],
                'publish_year': ['出版年', 'year', '出版年份', '出版日期', 'publish_year'],
                'category_code': ['分类号', 'category_code', '分类', 'class_no', '中图分类号'],
                'call_number': ['索书号', 'call_number', '索书号', 'call_no'],
                'original_id': ['记录ID', 'id', 'original_id', 'ID', 'record_id', 'recordId']
            }

            # 实际列名
            actual_map = {}
            for field, possible_names in col_map.items():
                for name in possible_names:
                    if name in reader.fieldnames:
                        actual_map[field] = name
                        break

            print(f"字段映射: {actual_map}")

            if 'title' not in actual_map:
                print("❌ 未找到书名字段，请检查CSV文件格式")
                print(f"   可用的列名: {reader.fieldnames}")
                return False

            # 批量插入优化
            batch_size = 100
            batch_data = []

            for row_num, row in enumerate(reader, 1):
                stats['total'] += 1

                # 显示进度
                if show_progress and stats['total'] % 100 == 0:
                    print(f"  处理进度: {stats['total']} 行 (新增: {stats['inserted']}, 跳过: {stats['skipped']})")

                # 提取数据
                title = row.get(actual_map.get('title'), '').strip()
                if not title:
                    stats['errors'] += 1
                    stats['skipped_reasons']['title_empty'] += 1
                    if show_progress:
                        print(f"  跳过第{row_num}行: 书名为空")
                    continue

                author = row.get(actual_map.get('author'), '').strip() if actual_map.get('author') else ''
                publisher = row.get(actual_map.get('publisher'), '').strip() if actual_map.get('publisher') else ''
                isbn = row.get(actual_map.get('isbn'), '').strip() if actual_map.get('isbn') else ''

                # 标准化ISBN（移除横线）
                if isbn:
                    isbn = isbn.replace('-', '').replace(' ', '').strip()

                # 处理年份
                year_str = row.get(actual_map.get('publish_year'), '').strip() if actual_map.get('publish_year') else ''
                publish_year = None
                if year_str:
                    # 尝试提取4位数字
                    import re
                    year_match = re.search(r'\b(19|20)\d{2}\b', year_str)
                    if year_match:
                        publish_year = int(year_match.group())

                category_code = row.get(actual_map.get('category_code'), '').strip() if actual_map.get(
                    'category_code') else ''
                call_number = row.get(actual_map.get('call_number'), '').strip() if actual_map.get(
                    'call_number') else ''
                original_id = row.get(actual_map.get('original_id'), '').strip() if actual_map.get(
                    'original_id') else ''

                # 检查是否已存在（优先级：original_id > isbn > 标题+作者）
                existing = None
                skip_reason = None

                if original_id:
                    existing = db_manager.fetch_one(
                        "SELECT id FROM books WHERE original_id = %s", (original_id,)
                    )
                    if existing:
                        skip_reason = 'original_id_exists'
                elif isbn:
                    existing = db_manager.fetch_one(
                        "SELECT id FROM books WHERE isbn = %s", (isbn,)
                    )
                    if existing:
                        skip_reason = 'isbn_exists'
                else:
                    # 更精确的去重：标题+作者+出版社
                    existing = db_manager.fetch_one(
                        """SELECT id FROM books 
                           WHERE title = %s AND author = %s AND publisher = %s""",
                        (title, author, publisher)
                    )
                    if existing:
                        skip_reason = 'title_author_exists'
                    else:
                        # 再检查相似标题（可选，防止重复导入不同版本）
                        similar = db_manager.fetch_one(
                            "SELECT id FROM books WHERE title = %s",
                            (title,)
                        )
                        if similar:
                            skip_reason = 'similar_title_exists'

                if existing:
                    stats['skipped'] += 1
                    stats['skipped_reasons'][skip_reason] += 1
                    if show_progress and stats['total'] % 500 == 0:
                        print(f"  跳过: {title[:50]} (已存在)")
                    continue

                # 准备插入数据
                book_data = {
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
                }

                # 批量插入或单条插入
                if batch_size > 1:
                    batch_data.append(book_data)
                    if len(batch_data) >= batch_size:
                        inserted_batch = insert_batch(batch_data)
                        stats['inserted'] += inserted_batch
                        if show_progress:
                            print(f"  ✓ 批量插入 {inserted_batch} 本图书")
                        batch_data = []
                else:
                    try:
                        book_id = db_manager.insert('books', book_data)
                        stats['inserted'] += 1
                        if show_progress and stats['inserted'] % 50 == 0:
                            print(f"  ✓ 已导入 {stats['inserted']} 本图书")
                    except Exception as e:
                        stats['errors'] += 1
                        stats['skipped_reasons'][f'insert_error_{str(e)[:20]}'] += 1
                        if show_progress:
                            print(f"  ✗ 导入失败: {title[:50]} - {e}")

            # 处理剩余的批量数据
            if batch_data:
                inserted_batch = insert_batch(batch_data)
                stats['inserted'] += inserted_batch
                if show_progress:
                    print(f"  ✓ 最后批量插入 {inserted_batch} 本图书")

        # 打印统计信息
        print(f"\n{'=' * 50}")
        print(f"导入完成!")
        print(f"  总计: {stats['total']} 行")
        print(f"  新增: {stats['inserted']} 本")
        print(f"  跳过: {stats['skipped']} 本")
        print(f"  错误: {stats['errors']} 本")

        if stats['skipped_reasons']:
            print(f"\n📊 跳过原因统计:")
            for reason, count in stats['skipped_reasons'].most_common(5):
                reason_name = {
                    'original_id_exists': '记录ID已存在',
                    'isbn_exists': 'ISBN已存在',
                    'title_author_exists': '书名+作者+出版社已存在',
                    'similar_title_exists': '相似书名已存在',
                    'title_empty': '书名为空'
                }.get(reason, reason)
                print(f"  {reason_name}: {count}本")

        print(f"{'=' * 50}")

        return stats['inserted'] > 0

    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def insert_batch(books_data):
    """批量插入图书数据"""
    if not books_data:
        return 0

    try:
        # 构建批量插入SQL
        placeholders = ', '.join(['(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'] * len(books_data))
        sql = f"""
            INSERT INTO books 
            (original_id, title, author, publisher, isbn, publish_year, 
             category_code, call_number, total_copies, available_copies)
            VALUES {placeholders}
        """

        # 准备参数
        params = []
        for book in books_data:
            params.extend([
                book['original_id'],
                book['title'],
                book['author'],
                book['publisher'],
                book['isbn'],
                book['publish_year'],
                book['category_code'],
                book['call_number'],
                book['total_copies'],
                book['available_copies']
            ])

        # 执行批量插入
        affected = db_manager.execute(sql, params)
        return len(books_data)

    except Exception as e:
        # 批量失败，回退到单条插入
        print(f"  批量插入失败，回退到单条插入: {e}")
        inserted = 0
        for book in books_data:
            try:
                db_manager.insert('books', book)
                inserted += 1
            except Exception as single_e:
                print(f"    单条插入失败: {book.get('title', '未知')[:30]} - {single_e}")
        return inserted


def check_database():
    """检查数据库状态"""
    try:
        # 统计各表数据
        user_count = db_manager.count('users')
        book_count = db_manager.count('books')
        borrow_count = db_manager.count('borrow_records')

        # 获取图书分类统计
        if book_count > 0:
            categories = db_manager.fetch_all(
                """SELECT category_code, COUNT(*) as count 
                   FROM books 
                   WHERE category_code IS NOT NULL AND category_code != ''
                   GROUP BY category_code 
                   ORDER BY count DESC 
                   LIMIT 10"""
            )
        else:
            categories = []

        print(f"\n📊 数据库统计:")
        print(f"  用户数: {user_count}")
        print(f"  图书数: {book_count}")
        print(f"  借阅记录: {borrow_count}")

        # 显示分类分布
        if categories:
            print(f"\n📚 图书分类分布（前10）:")
            for cat in categories:
                cat_name = get_category_name(cat['category_code'][0] if cat['category_code'] else '')
                print(f"  {cat['category_code']} {cat_name}: {cat['count']}本")

        # 显示最新10本图书
        if book_count > 0:
            print(f"\n📚 最新图书:")
            books = db_manager.fetch_all(
                "SELECT id, title, author FROM books ORDER BY id DESC LIMIT 10"
            )
            for book in books:
                author_str = f" - {book['author']}" if book.get('author') else ""
                print(f"  [{book['id']}] {book['title'][:50]}{author_str}")

    except Exception as e:
        print(f"❌ 检查失败: {e}")


def get_category_name(first_char):
    """根据分类号首字母获取大类名称"""
    categories = {
        'A': '马列主义', 'B': '哲学', 'C': '社科总论', 'D': '政治法律',
        'E': '军事', 'F': '经济', 'G': '文化教育', 'H': '语言文字',
        'I': '文学', 'J': '艺术', 'K': '历史地理', 'N': '自然科学',
        'O': '数理化', 'P': '天文地球', 'Q': '生物科学', 'R': '医药卫生',
        'S': '农业科学', 'T': '工业技术', 'U': '交通运输', 'V': '航空航天',
        'X': '环境科学', 'Z': '综合图书'
    }
    return categories.get(first_char, '其他')


def clear_all_books():
    """清空所有图书数据（谨慎使用）"""
    confirm = input("⚠️ 确定要清空所有图书数据吗？(yes/no): ")
    if confirm.lower() == 'yes':
        # 先删除借阅记录
        borrow_count = db_manager.execute("DELETE FROM borrow_records WHERE book_id IN (SELECT id FROM books)")
        print(f"已删除 {borrow_count} 条借阅记录")

        # 再删除图书
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
    print("CSV图书数据导入工具 v2.0")
    print("=" * 50)

    # 解析命令行参数
    csv_file = 'library_books.csv'
    clear_flag = False
    no_progress = False

    for arg in sys.argv[1:]:
        if arg == '--clear':
            clear_flag = True
        elif arg == '--quiet':
            no_progress = True
        elif not arg.startswith('--'):
            csv_file = arg

    # 可选：先清空数据
    if clear_flag:
        clear_all_books()

    # 导入数据
    if import_books_from_csv(csv_file, show_progress=not no_progress):
        check_database()

        # 显示导入后的操作建议
        print("\n💡 后续操作建议:")
        print("  1. 运行 'python app.py' 启动Web应用")
        print("  2. 或运行 'python scripts/import_csv_data.py <其他CSV文件>' 继续导入")
        print("  3. 或运行 'python scripts/generate_test_data.py' 生成测试借阅数据")
    else:
        print("\n❌ 导入失败，请检查:")
        print("  1. CSV文件是否存在且格式正确")
        print("  2. 数据库连接是否正常")
        print("  3. CSV文件编码是否为UTF-8")
        print("\n💡 提示: 可以先运行 'python scripts/generate_csv_samples.py' 生成示例CSV文件")
import requests
import csv
import time
import random
from typing import List, Dict
from collections import Counter


class LibrarySpider:
    def __init__(self, cookie_string: str, category_code: str = None):
        """
        初始化爬虫
        :param cookie_string: Cookie字符串
        :param category_code: 中图分类法大类代码，None表示全部，如"02"表示经济类
        """
        self.session = requests.Session()
        self.category_code = category_code

        # 从cookie中提取JWT token
        jwt_token = ""
        for item in cookie_string.split(';'):
            if 'jwt=' in item:
                jwt_token = item.split('=')[1].strip()
                break

        # 完整的请求头（基于成功的请求）
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json;charset=UTF-8',
            'Cookie': cookie_string,
            'groupCode': '200164',
            'jwtOpacAuth': jwt_token,
            'mappingPath': '',
            'Origin': 'https://mfindhniit.libsp.cn',
            'Referer': 'https://mfindhniit.libsp.cn/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0'
        }

        self.all_books = []

    def search_books(self, page: int = 1, rows: int = 20) -> Dict:
        """搜索图书 - 支持分类筛选"""
        url = "https://mfindhniit.libsp.cn/find/unify/search"

        # 基础参数
        payload = {
            "docCode": [],
            "searchFieldContent": "*",
            "searchField": "callNo",
            "resourceType": [],
            "subject": [],
            "author": [],
            "campusId": [],
            "categorySearchFlag": 1,
            "collectionName": [],
            "coreInclude": [],
            "countryCode": [],
            "ddType": [],
            "group": [],
            "langCode": [],
            "locationId": [],
            "onlyOnShelf": None,
            "page": page,
            "publisher": [],
            "resourceType": [],
            "rows": rows,
            "sortClause": "desc",
            "sortField": "relevance",
            "subject": [],
            "verifyStatus": []
        }

        # 如果指定了分类代码，添加分类筛选
        if self.category_code:
            payload["discode1"] = [self.category_code]
        else:
            payload["discode1"] = []  # 空数组表示全部类别

        try:
            response = self.session.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"请求失败 (页码:{page}): {e}")
            return {"success": False}

    def parse_book_info(self, book_item: Dict) -> Dict:
        """解析图书信息"""
        # 处理作者
        author = book_item.get('author', '')
        if author:
            author = author.replace('著', '').replace('编著', '').replace('编', '').strip()

        # 处理出版年份
        publish_year = book_item.get('publishYear', '')
        if publish_year and len(publish_year) >= 4:
            publish_year = publish_year[:4]

        # 处理分类号
        chi_class_no = book_item.get('chiClassNo', [])
        if isinstance(chi_class_no, list):
            chi_class_no = ', '.join(chi_class_no)

        return {
            '书名': book_item.get('title', '').strip(),
            '作者': author,
            '出版社': book_item.get('publisher', ''),
            'ISBN': book_item.get('isbn', ''),
            '出版年': publish_year,
            '分类号': chi_class_no,
            '索书号': book_item.get('callNoOne', ''),
            '记录ID': book_item.get('recordId', '')
        }

    def get_total_count(self) -> int:
        """获取当前分类下的总图书数量"""
        result = self.search_books(1, 1)
        if result.get('success'):
            return result.get('data', {}).get('numFound', 0)
        return 0

    def crawl_random_books(self, sample_size: int = 100, rows_per_page: int = 20):
        """
        随机爬取指定数量的图书（自动去重）
        :param sample_size: 要爬取的随机图书数量
        :param rows_per_page: 每页数量
        """
        print("=" * 60)
        if self.category_code:
            category_name = get_category_name(self.category_code)
            print(f"随机爬取图书数据 - {category_name}类")
        else:
            print("随机爬取图书数据 - 全部类别")
        print("=" * 60)

        # 获取总数
        total_count = self.get_total_count()
        if total_count == 0:
            print("无法获取总图书数量，请检查网络或Cookie")
            return

        print(f"📚 当前分类总藏书: {total_count:,} 本")
        print(f"🎯 目标随机爬取: {sample_size:,} 本")
        print()

        # 如果样本量大于总数，调整
        if sample_size > total_count:
            print(f"⚠️ 样本量超过总藏书量，将爬取全部 {total_count:,} 本")
            sample_size = total_count

        # 计算总页数
        total_pages = (total_count + rows_per_page - 1) // rows_per_page

        # 为了确保能凑够不重复的图书，多准备一些页面（多50%）
        pages_needed = max((sample_size + rows_per_page - 1) // rows_per_page, 10)
        extra_pages = min(int(pages_needed * 1.5), total_pages)  # 多50%的页码，但不超过总页数

        # 随机选择不重复的页码
        if extra_pages >= total_pages:
            selected_pages = list(range(1, total_pages + 1))
            random.shuffle(selected_pages)
        else:
            selected_pages = random.sample(range(1, total_pages + 1), extra_pages)

        # 按页码排序（可选，更有序）
        selected_pages.sort()

        print(f"📄 准备了 {len(selected_pages)} 个随机页码（含冗余，目标需要约 {pages_needed} 页）")
        if len(selected_pages) <= 20:
            print(f"   页码: {selected_pages}")
        else:
            print(f"   页码范围: {selected_pages[0]} ~ {selected_pages[-1]}")
        print()

        self.all_books = []
        seen_ids = set()  # 🔑 关键：记录已爬取的图书ID，用于去重
        books_collected = 0
        total_duplicates = 0  # 统计重复数量

        for idx, page in enumerate(selected_pages, 1):
            # 检查是否已达到目标
            if books_collected >= sample_size:
                break

            # 计算本次还需要多少本
            remaining = sample_size - books_collected
            books_per_page = min(rows_per_page, remaining)

            print(f"[{idx}/{len(selected_pages)}] 爬取第 {page} 页...", end=' ')

            result = self.search_books(page, rows_per_page)

            if not result.get('success'):
                print("请求失败，跳过")
                continue

            books = result.get('data', {}).get('searchResult', [])

            if not books:
                print("无数据，跳过")
                continue

            # 🔑 关键：过滤掉已经爬取过的图书
            new_books = []
            page_duplicates = 0
            for book in books:
                record_id = book.get('recordId', '')
                if record_id and record_id not in seen_ids:
                    seen_ids.add(record_id)
                    new_books.append(book)
                elif record_id:
                    page_duplicates += 1

            if not new_books:
                print(f"本页全部重复 ({page_duplicates}本)，跳过")
                total_duplicates += page_duplicates
                continue

            # 只取需要的数量
            books_to_add = new_books[:books_per_page]

            # 解析并保存
            for book in books_to_add:
                parsed_book = self.parse_book_info(book)
                self.all_books.append(parsed_book)

            books_collected += len(books_to_add)
            total_duplicates += page_duplicates

            # 显示详细信息
            print(
                f"获取 {len(books_to_add)} 本 (新增) | 本页重复: {page_duplicates} | 累计: {books_collected}/{sample_size}")

            # 显示一个样例
            if books_to_add:
                sample_book = books_to_add[0]
                sample_title = sample_book.get('title', '')[:40]
                print(f"   └─ 例如: 《{sample_title}》")

            # 随机延迟，避免请求过快
            delay = random.uniform(0.3, 0.8)
            time.sleep(delay)

        # 输出最终统计
        print(f"\n📊 爬取统计:")
        print(f"  目标数量: {sample_size} 本")
        print(f"  实际获取: {books_collected} 本")
        print(f"  遇到重复: {total_duplicates} 次")

        if books_collected < sample_size:
            print(f"\n⚠️ 注意: 只获取到 {books_collected} 本不重复图书（目标 {sample_size}）")
            print(f"   可能原因: 总藏书量有限或网络限制")
        else:
            print(f"\n✓ 成功获取 {books_collected} 本不重复图书")

        # 保存结果
        category_suffix = f"_{self.category_code}" if self.category_code else "_all"
        filename = f'library_books_random{category_suffix}_{sample_size}.csv'
        self.save_to_csv(filename)

        return self.all_books

    def crawl_books(self, rows_per_page: int = 20, max_books: int = None, max_pages: int = None):
        """
        顺序爬取图书
        :param rows_per_page: 每页数量
        :param max_books: 最大爬取数量
        :param max_pages: 最大爬取页数
        """
        print("=" * 60)
        if self.category_code:
            category_name = get_category_name(self.category_code)
            print(f"开始爬取图书数据 - {category_name}类")
        else:
            print("开始爬取图书数据 - 全部类别")
        print("=" * 60)
        print(f"每页数量: {rows_per_page}")
        if max_books:
            print(f"目标数量: {max_books:,} 本")
        else:
            print(f"目标数量: 全部图书")
        print()

        page = 1
        total_books = 0
        total_found = None

        while True:
            if max_pages and page > max_pages:
                print(f"\n已达到页数限制 ({max_pages} 页)，停止爬取")
                break

            print(f"\n正在抓取第 {page} 页...", end=' ')

            result = self.search_books(page, rows_per_page)

            if not result.get('success'):
                print("请求失败，停止爬取")
                break

            data = result.get('data', {})
            books = data.get('searchResult', [])

            if total_found is None:
                total_found = data.get('numFound', 0)
                print(f"\n📚 共找到 {total_found:,} 本图书")
                print("-" * 60)

                if max_books and max_books > total_found:
                    print(f"⚠️ 目标数量超过总书数，将爬取全部 {total_found:,} 本")
                    max_books = total_found

            if not books:
                print("无更多数据，爬取完成")
                break

            remaining = max_books - total_books if max_books else None
            if remaining is not None and remaining <= 0:
                break

            books_to_add = books
            if remaining is not None and len(books) > remaining:
                books_to_add = books[:remaining]

            for book in books_to_add:
                parsed_book = self.parse_book_info(book)
                self.all_books.append(parsed_book)

            total_books += len(books_to_add)

            if max_books:
                progress = (total_books / max_books * 100)
                print(f"获取 {len(books_to_add)} 本 (累计: {total_books:,}/{max_books:,}, 进度: {progress:.1f}%)")
            else:
                progress = (total_books / total_found * 100) if total_found > 0 else 0
                print(f"获取 {len(books_to_add)} 本 (累计: {total_books:,}/{total_found:,}, 进度: {progress:.1f}%)")

            if max_books and total_books >= max_books:
                print(f"\n✓ 已达到目标数量 {max_books:,} 本，停止爬取")
                break

            if len(books) < rows_per_page or total_books >= total_found:
                print("\n✓ 已爬取全部图书")
                break

            page += 1
            time.sleep(0.3)

        category_suffix = f"_{self.category_code}" if self.category_code else "_all"
        self.save_to_csv(f'library_books{category_suffix}.csv')

        print(f"\n🎉 爬取完成！共获取 {len(self.all_books):,} 本图书")

    def save_to_csv(self, filename: str = 'library_books.csv'):
        """保存图书信息到CSV"""
        if not self.all_books:
            print("没有数据可保存")
            return

        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['书名', '作者', '出版社', 'ISBN', '出版年', '分类号', '索书号',
                                                   '记录ID'])
            writer.writeheader()
            writer.writerows(self.all_books)

        print(f"\n✓ 数据已保存到 {filename}")
        print(f"✓ 文件大小: {len(self.all_books):,} 条记录")

        print("\n📖 数据预览（前5条）:")
        print("-" * 60)
        for i, book in enumerate(self.all_books[:5], 1):
            print(f"{i}. 《{book['书名']}》")
            print(f"   作者: {book['作者']}")
            print(f"   出版社: {book['出版社']}")
            print(f"   分类号: {book['分类号']}")
            print()

        # 统计信息
        print("📊 统计信息:")
        print(f"  总图书数: {len(self.all_books):,}")

        # 按分类统计（前10）
        category_counts = Counter()
        for book in self.all_books:
            class_no = book['分类号']
            if class_no and len(class_no) > 0:
                first_char = class_no[0]
                category_counts[first_char] += 1

        if category_counts:
            print(f"\n  分类分布（前10）:")
            for cat, count in category_counts.most_common(10):
                cat_name = get_category_by_first_char(cat)
                print(f"    {cat}类({cat_name}): {count}本")


def get_category_name(code: str) -> str:
    """获取中图分类法大类名称"""
    categories = {
        "01": "马列主义、毛泽东思想",
        "02": "哲学",
        "03": "社会科学总论",
        "04": "政治、法律",
        "05": "军事",
        "06": "经济",
        "07": "文化、科学、教育、体育",
        "08": "语言、文字",
        "09": "文学",
        "10": "艺术",
        "11": "历史、地理",
        "12": "自然科学总论",
        "13": "数理科学和化学",
        "14": "天文学、地球科学",
        "15": "生物科学",
        "16": "医药、卫生",
        "17": "农业科学",
        "18": "工业技术",
        "19": "交通运输",
        "20": "航空、航天",
        "21": "环境科学、劳动保护科学",
        "22": "综合性图书"
    }
    return categories.get(code, code)


def get_category_by_first_char(char: str) -> str:
    """根据分类号首字母获取大类名称"""
    categories = {
        'A': '马列主义',
        'B': '哲学、宗教',
        'C': '社会科学总论',
        'D': '政治、法律',
        'E': '军事',
        'F': '经济',
        'G': '文化、科学、教育',
        'H': '语言、文字',
        'I': '文学',
        'J': '艺术',
        'K': '历史、地理',
        'N': '自然科学总论',
        'O': '数理科学和化学',
        'P': '天文学、地球科学',
        'Q': '生物科学',
        'R': '医药、卫生',
        'S': '农业科学',
        'T': '工业技术',
        'U': '交通运输',
        'V': '航空、航天',
        'X': '环境科学',
        'Z': '综合性图书'
    }
    return categories.get(char, '其他')


# 主程序
if __name__ == '__main__':
    cookie = "SameSite=None; jwtHeader=jwtOpacAuth; route=fbb345105240e4e03f7b2fd9b6dde0f9; jwt=eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiI5MzU0MCIsImNyZWF0ZWQiOjE3NzY0Mzg1NzI0MDUsImV4cCI6MTc3NjUyNDk3MiwianRpIjoiYjcxY2RmODMtNTlmNi00ZmMyLTk4NGItMmFmN2MzNWUyMzdiIiwiZ3JvdXBDb2RlIjoiMjAwMTY0IiwibWFwcGluZ1BhdGgiOiJobmlpdCJ9.tR92FOPzay9aLZt-Y7UKUFJsacfhTCZPvrJXxx8iuhKiEO1843AiL1CfY7plQUkr9brw6yiY4TYMoflh9tPPvA; SESSION=ab8e91a0-9c1e-43b2-8507-26a463eb4194"

    print("=" * 60)
    print("图书馆图书爬虫")
    print("=" * 60)

    # 选择分类
    print("\n请选择图书分类：")
    print("0. 全部类别")
    print("1. 马列主义、毛泽东思想 (01)")
    print("2. 哲学 (02)")
    print("3. 社会科学总论 (03)")
    print("4. 政治、法律 (04)")
    print("5. 军事 (05)")
    print("6. 经济 (06)")
    print("7. 文化、科学、教育 (07)")
    print("8. 语言、文字 (08)")
    print("9. 文学 (09)")
    print("10. 艺术 (10)")
    print("11. 历史、地理 (11)")
    print("12. 自然科学总论 (12)")
    print("13. 数理科学和化学 (13)")
    print("14. 天文学、地球科学 (14)")
    print("15. 生物科学 (15)")
    print("16. 医药、卫生 (16)")
    print("17. 农业科学 (17)")
    print("18. 工业技术 (18)")
    print("19. 交通运输 (19)")
    print("20. 航空、航天 (20)")
    print("21. 环境科学 (21)")
    print("22. 综合性图书 (22)")

    category_choice = input("\n请输入分类编号 (0-22，默认为0全部): ").strip()

    category_map = {
        "0": None,
        "1": "01", "2": "02", "3": "03", "4": "04", "5": "05",
        "6": "06", "7": "07", "8": "08", "9": "09", "10": "10",
        "11": "11", "12": "12", "13": "13", "14": "14", "15": "15",
        "16": "16", "17": "17", "18": "18", "19": "19", "20": "20",
        "21": "21", "22": "22"
    }

    category_code = category_map.get(category_choice, None)

    if category_code:
        print(f"\n已选择: {get_category_name(category_code)}")
    else:
        print("\n已选择: 全部类别")

    # 创建爬虫实例
    spider = LibrarySpider(cookie, category_code)

    # 获取当前分类的总藏书量
    total_count = spider.get_total_count()
    if total_count > 0:
        print(f"当前分类总藏书: {total_count:,} 本")

    print("\n请选择爬取模式：")
    print("1. 爬取全部图书（顺序爬取）")
    print("2. 自定义数量（顺序爬取）")
    print("3. 自定义页数（顺序爬取）")
    print("4. 🎲 随机爬取（推荐用于采样）")
    print()

    choice = input("请输入选项 (1/2/3/4): ").strip()

    if choice == '1':
        spider.crawl_books(rows_per_page=20, max_books=None, max_pages=None)

    elif choice == '2':
        try:
            max_books = int(input("请输入要爬取的图书数量: "))
            if max_books <= 0:
                print("数量必须大于0")
            else:
                pages_needed = (max_books + 19) // 20
                estimated_time = pages_needed * 0.3 / 60
                print(f"\n预计需要爬取 {pages_needed} 页，约 {estimated_time:.1f} 分钟")
                confirm = input(f"确认爬取 {max_books:,} 本图书？(y/n): ")
                if confirm.lower() == 'y':
                    spider.crawl_books(rows_per_page=20, max_books=max_books)
        except ValueError:
            print("输入无效")

    elif choice == '3':
        try:
            max_pages = int(input("请输入要爬取的页数（每页20本）: "))
            if max_pages <= 0:
                print("页数必须大于0")
            else:
                max_books = max_pages * 20
                estimated_time = max_pages * 0.3 / 60
                print(f"\n预计爬取 {max_pages} 页，约 {max_books} 本图书，约 {estimated_time:.1f} 分钟")
                confirm = input(f"确认爬取 {max_pages} 页？(y/n): ")
                if confirm.lower() == 'y':
                    spider.crawl_books(rows_per_page=20, max_books=None, max_pages=max_pages)
        except ValueError:
            print("输入无效")

    elif choice == '4':
        try:
            print("\n🎲 随机爬取模式")
            sample_size = int(input("请输入要随机爬取的数量（例如：500）: "))
            if sample_size <= 0:
                print("数量必须大于0")
            else:
                pages_needed = (sample_size + 19) // 20
                estimated_time = pages_needed * 0.5 / 60
                print(f"\n预计需要爬取约 {pages_needed} 个随机页面，约 {estimated_time:.1f} 分钟")
                confirm = input(f"\n确认随机爬取 {sample_size:,} 本图书？(y/n): ")
                if confirm.lower() == 'y':
                    spider.crawl_random_books(sample_size=sample_size, rows_per_page=20)
        except ValueError:
            print("输入无效")

    else:
        print("无效选项")
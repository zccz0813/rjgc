import requests
import csv
import time
from typing import List, Dict
from collections import Counter


class LibrarySpider:
    def __init__(self, cookie_string: str):
        """初始化爬虫"""
        self.session = requests.Session()

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
        """搜索图书 - 使用成功的参数"""
        url = "https://mfindhniit.libsp.cn/find/unify/search"

        # 使用您提供的成功参数
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
            "discode1": ["02"],
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

    def crawl_books(self, rows_per_page: int = 20, max_books: int = None, max_pages: int = None):
        """
        爬取图书（支持自定义数量）
        :param rows_per_page: 每页数量（建议20-50）
        :param max_books: 最大爬取图书数量，None表示爬取全部
        :param max_pages: 最大爬取页数，None表示不限制（优先级低于max_books）
        """
        print("=" * 60)
        print("开始爬取图书数据...")
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
            # 检查是否达到页数限制
            if max_pages and page > max_pages:
                print(f"\n已达到页数限制 ({max_pages} 页)，停止爬取")
                break

            print(f"\n正在抓取第 {page} 页...", end=' ')

            # 请求数据
            result = self.search_books(page, rows_per_page)

            if not result.get('success'):
                print("请求失败，停止爬取")
                break

            data = result.get('data', {})
            books = data.get('searchResult', [])

            # 获取总数（第一页）
            if total_found is None:
                total_found = data.get('numFound', 0)
                print(f"\n📚 共找到 {total_found:,} 本图书")
                print("-" * 60)

                # 如果设置了最大数量且大于总数，调整目标
                if max_books and max_books > total_found:
                    print(f"⚠️  目标数量 {max_books:,} 超过总书数，将爬取全部 {total_found:,} 本")
                    max_books = total_found

            if not books:
                print("无更多数据，爬取完成")
                break

            # 计算本次要添加的图书数量
            remaining = max_books - total_books if max_books else None
            if remaining is not None and remaining <= 0:
                break

            books_to_add = books
            if remaining is not None and len(books) > remaining:
                books_to_add = books[:remaining]

            # 解析并保存图书
            for book in books_to_add:
                parsed_book = self.parse_book_info(book)
                self.all_books.append(parsed_book)

            total_books += len(books_to_add)

            # 显示进度
            if max_books:
                progress = (total_books / max_books * 100)
                print(f"获取 {len(books_to_add)} 本 (累计: {total_books:,}/{max_books:,}, 进度: {progress:.1f}%)")
            else:
                progress = (total_books / total_found * 100) if total_found > 0 else 0
                print(f"获取 {len(books_to_add)} 本 (累计: {total_books:,}/{total_found:,}, 进度: {progress:.1f}%)")

            # 检查是否达到目标
            if max_books and total_books >= max_books:
                print(f"\n✓ 已达到目标数量 {max_books:,} 本，停止爬取")
                break

            # 检查是否还有下一页
            if len(books) < rows_per_page or total_books >= total_found:
                print("\n✓ 已爬取全部图书")
                break

            page += 1

            # 添加延迟，避免请求过快
            time.sleep(0.3)

        # 保存到CSV
        self.save_to_csv()

        # 显示完成信息
        print(f"\n🎉 爬取完成！共获取 {len(self.all_books):,} 本图书")
        if max_books and len(self.all_books) < max_books:
            print(f"⚠️  实际获取 {len(self.all_books):,} 本，少于目标 {max_books:,} 本（可能已无更多数据）")

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

        # 显示前5条数据预览
        print("\n📖 数据预览（前5条）:")
        print("-" * 60)
        for i, book in enumerate(self.all_books[:5], 1):
            print(f"{i}. 《{book['书名']}》")
            print(f"   作者: {book['作者']}")
            print(f"   出版社: {book['出版社']}")
            print(f"   ISBN: {book['ISBN']}")
            print()

        # 统计信息
        print("📊 统计信息:")
        print(f"  总图书数: {len(self.all_books):,}")

        # 按出版社统计（前10）
        publisher_counts = Counter([book['出版社'] for book in self.all_books if book['出版社']])
        if publisher_counts:
            print(f"\n  出版社分布（前10）:")
            for pub, count in publisher_counts.most_common(10):
                print(f"    {pub}: {count}本")


# 主程序
if __name__ == '__main__':
    # 您的Cookie（从浏览器复制）
    cookie = "SameSite=None; jwtHeader=jwtOpacAuth; route=fbb345105240e4e03f7b2fd9b6dde0f9; jwt=eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiI5MzU0MCIsImNyZWF0ZWQiOjE3NzY0Mzg1NzI0MDUsImV4cCI6MTc3NjUyNDk3MiwianRpIjoiYjcxY2RmODMtNTlmNi00ZmMyLTk4NGItMmFmN2MzNWUyMzdiIiwiZ3JvdXBDb2RlIjoiMjAwMTY0IiwibWFwcGluZ1BhdGgiOiJobmlpdCJ9.tR92FOPzay9aLZt-Y7UKUFJsacfhTCZPvrJXxx8iuhKiEO1843AiL1CfY7plQUkr9brw6yiY4TYMoflh9tPPvA; SESSION=ab8e91a0-9c1e-43b2-8507-26a463eb4194"

    # 创建爬虫实例
    spider = LibrarySpider(cookie)

    # 交互式选择爬取数量
    print("=" * 60)
    print("图书馆图书爬虫")
    print("=" * 60)
    print("总图书数: 204,737 本")
    print()
    print("请选择爬取模式：")
    print("1. 爬取全部图书（约204,737本，预计51分钟）")
    print("2. 自定义数量")
    print("3. 自定义页数")
    print()

    choice = input("请输入选项 (1/2/3): ").strip()

    if choice == '1':
        # 爬取全部
        spider.crawl_books(rows_per_page=20, max_books=None, max_pages=None)

    elif choice == '2':
        # 自定义数量
        try:
            max_books = int(input("请输入要爬取的图书数量（例如：1000）: "))
            if max_books <= 0:
                print("数量必须大于0，将爬取全部")
                spider.crawl_books(rows_per_page=20, max_books=None)
            else:
                # 计算预计页数和时间
                pages_needed = (max_books + 19) // 20
                estimated_time = pages_needed * 0.3 / 60
                print(f"\n预计需要爬取 {pages_needed} 页，约 {estimated_time:.1f} 分钟")
                confirm = input(f"确认爬取 {max_books:,} 本图书？(y/n): ")
                if confirm.lower() == 'y':
                    spider.crawl_books(rows_per_page=20, max_books=max_books)
                else:
                    print("已取消爬取")
        except ValueError:
            print("输入无效，将爬取全部")
            spider.crawl_books(rows_per_page=20, max_books=None)

    elif choice == '3':
        # 自定义页数
        try:
            max_pages = int(input("请输入要爬取的页数（每页20本，例如：10）: "))
            if max_pages <= 0:
                print("页数必须大于0，将爬取全部")
                spider.crawl_books(rows_per_page=20, max_pages=None)
            else:
                max_books = max_pages * 20
                estimated_time = max_pages * 0.3 / 60
                print(f"\n预计爬取 {max_pages} 页，约 {max_books} 本图书，约 {estimated_time:.1f} 分钟")
                confirm = input(f"确认爬取 {max_pages} 页？(y/n): ")
                if confirm.lower() == 'y':
                    spider.crawl_books(rows_per_page=20, max_books=None, max_pages=max_pages)
                else:
                    print("已取消爬取")
        except ValueError:
            print("输入无效，将爬取全部")
            spider.crawl_books(rows_per_page=20, max_books=None)

    else:
        print("无效选项，将爬取全部图书")
        spider.crawl_books(rows_per_page=20, max_books=None)
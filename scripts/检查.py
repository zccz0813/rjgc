# scripts/check_csv_duplicates.py
import csv
from collections import Counter

csv_file = 'library_books.csv'

with open(csv_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)

    # 统计记录ID
    record_ids = [row.get('记录ID', '').strip() for row in reader]

    # 统计重复
    id_counts = Counter(record_ids)
    unique_count = len([id for id in id_counts if id])
    duplicate_ids = {id: count for id, count in id_counts.items() if count > 1}

    print(f"总行数: {len(record_ids)}")
    print(f"唯一记录ID数: {unique_count}")
    print(f"重复的记录ID数: {len(duplicate_ids)}")

    if duplicate_ids:
        print(f"\n重复最多的前10个ID:")
        for id, count in sorted(duplicate_ids.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {id}: {count}次")
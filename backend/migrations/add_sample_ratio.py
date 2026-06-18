import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "biaozhu.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("""
        ALTER TABLE sampling_batches 
        ADD COLUMN sample_ratio FLOAT
    """)
    print("成功添加 sample_ratio 字段到 sampling_batches 表")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("sample_ratio 字段已存在，跳过")
    else:
        raise

conn.commit()
conn.close()

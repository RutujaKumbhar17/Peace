import sqlite3
import json
import os

DB_PATH = os.path.join('d:\\Peace', 'logs', 'peace.db')

def get_diary_example():
    if not os.path.exists(DB_PATH):
        print("DB not found")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT content_json FROM diary_entries LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(row[0])
    else:
        print("No entries found")
    conn.close()

if __name__ == '__main__':
    get_diary_example()

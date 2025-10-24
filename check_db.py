import sqlite3

db_path = r"C:\Users\Silve\Desktop\pms_demo\pms_demo\instance\pms_demo.db"
con = sqlite3.connect(db_path)
cur = con.cursor()

# List all tables
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print("Tables:", tables)

# Show all data in each table
for table_name in tables:
    print(f"\nData in table {table_name[0]}:")
    rows = cur.execute(f"SELECT * FROM {table_name[0]}").fetchall()
    for row in rows:
        print(row)

con.close()
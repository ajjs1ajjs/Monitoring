import sqlite3

db_path = 'd:/CODE/Monitoring/pymon.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

columns = [
    ('disk_info', 'TEXT'),
    ('raid_info', 'TEXT'),
    ('exporter_version', 'TEXT')
]

for col_name, col_type in columns:
    try:
        c.execute(f'ALTER TABLE servers ADD COLUMN {col_name} {col_type}')
        print(f"Added column: {col_name}")
    except sqlite3.OperationalError:
        print(f"Column {col_name} already exists")

conn.commit()
conn.close()

import sqlite3, json, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/flights.db')
cursor = conn.cursor()
cursor.execute("SELECT results_json FROM flight_searches WHERE id=97")
row = cursor.fetchone()
if row and row[0]:
    data = json.loads(row[0])
    print(json.dumps(data[8], indent=2, ensure_ascii=False))

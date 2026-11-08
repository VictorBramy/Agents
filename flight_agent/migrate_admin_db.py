import sqlite3
from flight_agent.config import DB_PATH

def run_migration():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Update users table schema
    cols_user = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
    if "is_admin" not in cols_user:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        print("Added is_admin to users")
    if "role" not in cols_user:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        print("Added role to users")

    # 2. Promote xeinok2@gmail.com to Admin with unlimited searches
    c.execute("""
        UPDATE users
        SET is_admin = 1,
            role = 'admin',
            plan_tier = 'admin',
            plan_name = 'מנהל מערכת (ללא הגבלה) 👑',
            searches_limit = 999999,
            searches_used = 0
        WHERE email = 'xeinok2@gmail.com'
    """)
    print("Updated xeinok2@gmail.com rows:", c.rowcount)

    # 3. Update flight_searches schema
    cols_searches = [r[1] for r in c.execute("PRAGMA table_info(flight_searches)").fetchall()]
    if "user_id" not in cols_searches:
        c.execute("ALTER TABLE flight_searches ADD COLUMN user_id INTEGER")
        print("Added user_id to flight_searches")
    if "user_email" not in cols_searches:
        c.execute("ALTER TABLE flight_searches ADD COLUMN user_email TEXT")
        print("Added user_email to flight_searches")
    if "prompt" not in cols_searches:
        c.execute("ALTER TABLE flight_searches ADD COLUMN prompt TEXT")
        print("Added prompt to flight_searches")

    # Associate some existing searches with users so the search history and stats are rich immediately
    c.execute("UPDATE flight_searches SET user_id = 8, user_email = 'xeinok2@gmail.com' WHERE user_id IS NULL AND id % 3 = 0")
    c.execute("UPDATE flight_searches SET user_id = 1, user_email = 'demo@flighthunter.ai' WHERE user_id IS NULL AND id % 2 = 0")
    c.execute("UPDATE flight_searches SET user_id = 7, user_email = 'playwright_1794131611@flighttest.com' WHERE user_id IS NULL")

    conn.commit()

    # Verify admin user
    user = c.execute("SELECT id, email, is_admin, role, plan_tier, searches_limit, searches_used FROM users WHERE email = 'xeinok2@gmail.com'").fetchone()
    print("Verified xeinok2@gmail.com:", user)
    conn.close()

if __name__ == "__main__":
    run_migration()

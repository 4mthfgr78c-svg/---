import sqlite3
from datetime import datetime
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                role TEXT DEFAULT 'worker',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_tg_id INTEGER,
                object_id INTEGER,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                actual_start TIMESTAMP,
                actual_end TIMESTAMP,
                photo_end TEXT,
                status TEXT DEFAULT 'scheduled',
                FOREIGN KEY(worker_tg_id) REFERENCES users(tg_id),
                FOREIGN KEY(object_id) REFERENCES objects(id)
            );
            
            CREATE TABLE IF NOT EXISTS supply_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_tg_id INTEGER,
                text TEXT NOT NULL,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_by INTEGER
            );
        """)
        # Добавляем менеджеров из config, если их ещё нет
        from config import MANAGER_IDS
        for tg_id in MANAGER_IDS:
            conn.execute(
                "INSERT OR IGNORE INTO users (tg_id, role) VALUES (?, ?)",
                (tg_id, "manager")
            )

# Работа с пользователями
def register_user(tg_id, username, full_name):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (tg_id, username, full_name, role) VALUES (?, ?, ?, 'worker')",
            (tg_id, username, full_name)
        )

def is_manager(tg_id):
    with get_connection() as conn:
        row = conn.execute("SELECT role FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        return row and row[0] == "manager"

# Объекты
def add_object(name, address, created_by):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO objects (name, address, created_by) VALUES (?, ?, ?)",
            (name, address, created_by)
        )
        return cur.lastrowid

def get_objects():
    with get_connection() as conn:
        return conn.execute("SELECT id, name, address FROM objects ORDER BY name").fetchall()

# Смены
def add_shift(worker_tg_id, object_id, start_time, end_time):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO shifts (worker_tg_id, object_id, start_time, end_time) VALUES (?, ?, ?, ?)",
            (worker_tg_id, object_id, start_time, end_time)
        )

def get_worker_shifts(worker_tg_id, status=None):
    with get_connection() as conn:
        query = """
            SELECT s.id, o.name, s.start_time, s.end_time, s.status, s.actual_start, s.actual_end
            FROM shifts s JOIN objects o ON s.object_id = o.id
            WHERE s.worker_tg_id = ?
        """
        params = [worker_tg_id]
        if status:
            query += " AND s.status = ?"
            params.append(status)
        query += " ORDER BY s.start_time"
        return conn.execute(query, params).fetchall()

def get_active_shift(worker_tg_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, object_id, start_time, end_time FROM shifts WHERE worker_tg_id = ? AND status = 'in_progress'",
            (worker_tg_id,)
        ).fetchone()

def start_shift(shift_id, actual_start):
    with get_connection() as conn:
        conn.execute(
            "UPDATE shifts SET actual_start = ?, status = 'in_progress' WHERE id = ?",
            (actual_start, shift_id)
        )

def end_shift(shift_id, actual_end, photo_file_id=None):
    with get_connection() as conn:
        conn.execute(
            "UPDATE shifts SET actual_end = ?, status = 'completed', photo_end = ? WHERE id = ?",
            (actual_end, photo_file_id, shift_id)
        )

# Заказы моющих
def add_supply_order(worker_tg_id, text):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO supply_orders (worker_tg_id, text) VALUES (?, ?)",
            (worker_tg_id, text)
        )

def get_new_orders():
    with get_connection() as conn:
        return conn.execute("""
            SELECT so.id, so.text, so.created_at, u.full_name
            FROM supply_orders so
            JOIN users u ON so.worker_tg_id = u.tg_id
            WHERE so.status = 'new'
            ORDER BY so.created_at
        """).fetchall()

def mark_order_processed(order_id, manager_tg_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE supply_orders SET status = 'processed', processed_by = ? WHERE id = ?",
            (manager_tg_id, order_id)
        )

# Утилиты для напоминаний
def get_shifts_for_reminder(hours_before):
    """Возвращает смены, которые начнутся ровно через hours_before часов от текущего момента"""
    from datetime import datetime, timedelta
    now = datetime.now()
    target_time = now + timedelta(hours=hours_before)
    # Ищем смены, у которых start_time попадает в интервал [target_time, target_time+1 минута)
    with get_connection() as conn:
        return conn.execute(
            "SELECT s.id, s.worker_tg_id, o.name, s.start_time FROM shifts s JOIN objects o ON s.object_id = o.id "
            "WHERE s.start_time BETWEEN ? AND ? AND s.status = 'scheduled'",
            (target_time, target_time + timedelta(minutes=1))
        ).fetchall()

def get_shifts_for_tomorrow():
    """Смены на следующий день (с 00:00 до 23:59)"""
    from datetime import datetime, timedelta
    tomorrow = datetime.now().date() + timedelta(days=1)
    start_dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
    end_dt = start_dt + timedelta(days=1)
    with get_connection() as conn:
        return conn.execute(
            "SELECT s.id, s.worker_tg_id, o.name, s.start_time FROM shifts s JOIN objects o ON s.object_id = o.id "
            "WHERE s.start_time >= ? AND s.start_time < ? AND s.status = 'scheduled'",
            (start_dt, end_dt)
        ).fetchall()
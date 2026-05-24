"""
Database - PostgreSQL menggunakan pg8000 (pure Python, kompatibel Python 3.13)
atau SQLite untuk lokal.
"""

import os
import json
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = DATABASE_URL.startswith("postgres")

if USE_POSTGRES:
    import pg8000.native
    parsed = urlparse(DATABASE_URL.replace("postgres://", "postgresql://"))
    PG_CONFIG = {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/"),
        "user": parsed.username,
        "password": parsed.password,
        "ssl_context": True
    }
    logger.info("✅ Menggunakan PostgreSQL (pg8000)")
else:
    import sqlite3
    DB_PATH = os.getenv("DB_PATH", "resi_tracker.db")
    logger.info(f"✅ Menggunakan SQLite: {DB_PATH}")


def _get_pg():
    return pg8000.native.Connection(**PG_CONFIG)


def _get_sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


CREATE_TABLE_PG = """
    CREATE TABLE IF NOT EXISTS packages (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        resi TEXT NOT NULL,
        courier TEXT NOT NULL,
        label TEXT DEFAULT 'Paket',
        last_status TEXT DEFAULT '',
        history TEXT DEFAULT '[]',
        is_delivered INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, resi)
    )
"""

CREATE_TABLE_SQLITE = """
    CREATE TABLE IF NOT EXISTS packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        resi TEXT NOT NULL,
        courier TEXT NOT NULL,
        label TEXT DEFAULT 'Paket',
        last_status TEXT DEFAULT '',
        history TEXT DEFAULT '[]',
        is_delivered INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, resi)
    )
"""


class Database:
    def __init__(self):
        if USE_POSTGRES:
            conn = _get_pg()
            conn.run(CREATE_TABLE_PG)
            conn.close()
        else:
            conn = _get_sqlite()
            conn.execute(CREATE_TABLE_SQLITE)
            conn.commit()
            conn.close()
        logger.info("✅ Database siap.")

    def add_package(self, user_id, resi, courier, label, last_status, history):
        try:
            if USE_POSTGRES:
                conn = _get_pg()
                conn.run("""
                    INSERT INTO packages (user_id, resi, courier, label, last_status, history)
                    VALUES (:user_id, :resi, :courier, :label, :last_status, :history)
                    ON CONFLICT (user_id, resi) DO NOTHING
                """, user_id=user_id, resi=resi.upper(), courier=courier.lower(),
                    label=label, last_status=last_status, history=json.dumps(history))
                conn.close()
            else:
                conn = _get_sqlite()
                conn.execute("""
                    INSERT OR IGNORE INTO packages
                    (user_id, resi, courier, label, last_status, history)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, resi.upper(), courier.lower(), label,
                      last_status, json.dumps(history)))
                conn.commit()
                conn.close()
            return True
        except Exception as e:
            logger.error(f"Error add_package: {e}")
            return False

    def update_package(self, user_id, resi, last_status, history):
        try:
            if USE_POSTGRES:
                conn = _get_pg()
                conn.run("""
                    UPDATE packages SET last_status=:status, history=:history,
                    updated_at=CURRENT_TIMESTAMP
                    WHERE user_id=:uid AND resi=:resi
                """, status=last_status, history=json.dumps(history),
                    uid=user_id, resi=resi.upper())
                conn.close()
            else:
                conn = _get_sqlite()
                conn.execute("""
                    UPDATE packages SET last_status=?, history=?,
                    updated_at=CURRENT_TIMESTAMP
                    WHERE user_id=? AND resi=?
                """, (last_status, json.dumps(history), user_id, resi.upper()))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Error update_package: {e}")

    def mark_delivered(self, user_id, resi):
        try:
            if USE_POSTGRES:
                conn = _get_pg()
                conn.run("""
                    UPDATE packages SET is_delivered=1, updated_at=CURRENT_TIMESTAMP
                    WHERE user_id=:uid AND resi=:resi
                """, uid=user_id, resi=resi.upper())
                conn.close()
            else:
                conn = _get_sqlite()
                conn.execute("""
                    UPDATE packages SET is_delivered=1, updated_at=CURRENT_TIMESTAMP
                    WHERE user_id=? AND resi=?
                """, (user_id, resi.upper()))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Error mark_delivered: {e}")

    def get_package(self, user_id, resi):
        try:
            if USE_POSTGRES:
                conn = _get_pg()
                rows = conn.run("""
                    SELECT * FROM packages WHERE user_id=:uid AND resi=:resi
                """, uid=user_id, resi=resi.upper())
                cols = [c["name"] for c in conn.columns]
                conn.close()
                if rows:
                    pkg = dict(zip(cols, rows[0]))
                    pkg["history"] = json.loads(pkg.get("history", "[]"))
                    return pkg
            else:
                conn = _get_sqlite()
                row = conn.execute("""
                    SELECT * FROM packages WHERE user_id=? AND resi=?
                """, (user_id, resi.upper())).fetchone()
                conn.close()
                if row:
                    pkg = dict(row)
                    pkg["history"] = json.loads(pkg.get("history", "[]"))
                    return pkg
            return None
        except Exception as e:
            logger.error(f"Error get_package: {e}")
            return None

    def get_user_packages(self, user_id, include_delivered=False):
        try:
            if USE_POSTGRES:
                conn = _get_pg()
                sql = "SELECT * FROM packages WHERE user_id=:uid"
                params = {"uid": user_id}
                if not include_delivered:
                    sql += " AND is_delivered=0"
                sql += " ORDER BY updated_at DESC"
                rows = conn.run(sql, **params)
                cols = [c["name"] for c in conn.columns]
                conn.close()
                packages = []
                for row in rows:
                    pkg = dict(zip(cols, row))
                    pkg["history"] = json.loads(pkg.get("history", "[]"))
                    packages.append(pkg)
                return packages
            else:
                conn = _get_sqlite()
                sql = "SELECT * FROM packages WHERE user_id=?"
                params = [user_id]
                if not include_delivered:
                    sql += " AND is_delivered=0"
                sql += " ORDER BY updated_at DESC"
                rows = conn.execute(sql, params).fetchall()
                conn.close()
                packages = []
                for row in rows:
                    pkg = dict(row)
                    pkg["history"] = json.loads(pkg.get("history", "[]"))
                    packages.append(pkg)
                return packages
        except Exception as e:
            logger.error(f"Error get_user_packages: {e}")
            return []

    def get_all_active_packages(self):
        try:
            if USE_POSTGRES:
                conn = _get_pg()
                rows = conn.run("""
                    SELECT * FROM packages WHERE is_delivered=0
                    ORDER BY updated_at ASC
                """)
                cols = [c["name"] for c in conn.columns]
                conn.close()
                packages = []
                for row in rows:
                    pkg = dict(zip(cols, row))
                    pkg["history"] = json.loads(pkg.get("history", "[]"))
                    packages.append(pkg)
                return packages
            else:
                conn = _get_sqlite()
                rows = conn.execute("""
                    SELECT * FROM packages WHERE is_delivered=0
                    ORDER BY updated_at ASC
                """).fetchall()
                conn.close()
                packages = []
                for row in rows:
                    pkg = dict(row)
                    pkg["history"] = json.loads(pkg.get("history", "[]"))
                    packages.append(pkg)
                return packages
        except Exception as e:
            logger.error(f"Error get_all_active_packages: {e}")
            return []

    def remove_package(self, user_id, resi):
        try:
            if USE_POSTGRES:
                conn = _get_pg()
                conn.run("""
                    DELETE FROM packages WHERE user_id=:uid AND resi=:resi
                """, uid=user_id, resi=resi.upper())
                conn.close()
                return True
            else:
                conn = _get_sqlite()
                cursor = conn.execute("""
                    DELETE FROM packages WHERE user_id=? AND resi=?
                """, (user_id, resi.upper()))
                conn.commit()
                count = cursor.rowcount
                conn.close()
                return count > 0
        except Exception as e:
            logger.error(f"Error remove_package: {e}")
            return False

    def remove_all_packages(self, user_id):
        try:
            if USE_POSTGRES:
                conn = _get_pg()
                conn.run("DELETE FROM packages WHERE user_id=:uid", uid=user_id)
                conn.close()
                return 1
            else:
                conn = _get_sqlite()
                cursor = conn.execute(
                    "DELETE FROM packages WHERE user_id=?", (user_id,))
                conn.commit()
                count = cursor.rowcount
                conn.close()
                return count
        except Exception as e:
            logger.error(f"Error remove_all_packages: {e}")
            return 0

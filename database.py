"""
Database - Mendukung PostgreSQL (Railway) dan SQLite (Termux/lokal).
Otomatis mendeteksi mana yang digunakan berdasarkan DATABASE_URL.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

# Deteksi otomatis: pakai PostgreSQL kalau ada DATABASE_URL, kalau tidak pakai SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = DATABASE_URL.startswith("postgres")


# ============================================================
# SETUP DATABASE
# ============================================================

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    logger.info("✅ Menggunakan PostgreSQL (Railway)")
else:
    import sqlite3
    DB_PATH = os.getenv("DB_PATH", "resi_tracker.db")
    logger.info(f"✅ Menggunakan SQLite: {DB_PATH}")


def _get_conn():
    """Ambil koneksi database."""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def _create_tables():
    """Buat tabel jika belum ada."""
    if USE_POSTGRES:
        sql = """
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
    else:
        sql = """
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
    with _get_conn() as conn:
        if USE_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(sql)
        else:
            conn.execute(sql)
        conn.commit()
    logger.info("✅ Database siap.")


class Database:
    def __init__(self):
        _create_tables()

    def add_package(self, user_id, resi, courier, label, last_status, history):
        try:
            if USE_POSTGRES:
                sql = """
                    INSERT INTO packages (user_id, resi, courier, label, last_status, history)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, resi) DO NOTHING
                """
                with _get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql, (user_id, resi.upper(), courier.lower(),
                                         label, last_status, json.dumps(history)))
                    conn.commit()
            else:
                sql = """
                    INSERT INTO packages (user_id, resi, courier, label, last_status, history)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                with _get_conn() as conn:
                    conn.execute(sql, (user_id, resi.upper(), courier.lower(),
                                      label, last_status, json.dumps(history)))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error add_package: {e}")
            return False

    def update_package(self, user_id, resi, last_status, history):
        try:
            if USE_POSTGRES:
                sql = """
                    UPDATE packages SET last_status=%s, history=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE user_id=%s AND resi=%s
                """
                with _get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql, (last_status, json.dumps(history),
                                         user_id, resi.upper()))
                    conn.commit()
            else:
                sql = """
                    UPDATE packages SET last_status=?, history=?, updated_at=CURRENT_TIMESTAMP
                    WHERE user_id=? AND resi=?
                """
                with _get_conn() as conn:
                    conn.execute(sql, (last_status, json.dumps(history),
                                      user_id, resi.upper()))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error update_package: {e}")

    def mark_delivered(self, user_id, resi):
        try:
            if USE_POSTGRES:
                sql = """UPDATE packages SET is_delivered=1, updated_at=CURRENT_TIMESTAMP
                         WHERE user_id=%s AND resi=%s"""
                with _get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql, (user_id, resi.upper()))
                    conn.commit()
            else:
                sql = """UPDATE packages SET is_delivered=1, updated_at=CURRENT_TIMESTAMP
                         WHERE user_id=? AND resi=?"""
                with _get_conn() as conn:
                    conn.execute(sql, (user_id, resi.upper()))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error mark_delivered: {e}")

    def get_package(self, user_id, resi):
        try:
            if USE_POSTGRES:
                sql = "SELECT * FROM packages WHERE user_id=%s AND resi=%s"
                with _get_conn() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute(sql, (user_id, resi.upper()))
                        row = cur.fetchone()
                if row:
                    pkg = dict(row)
                    pkg["history"] = json.loads(pkg.get("history", "[]"))
                    return pkg
            else:
                sql = "SELECT * FROM packages WHERE user_id=? AND resi=?"
                with _get_conn() as conn:
                    row = conn.execute(sql, (user_id, resi.upper())).fetchone()
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
                sql = "SELECT * FROM packages WHERE user_id=%s"
                params = [user_id]
                if not include_delivered:
                    sql += " AND is_delivered=0"
                sql += " ORDER BY updated_at DESC"
                with _get_conn() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute(sql, params)
                        rows = cur.fetchall()
            else:
                sql = "SELECT * FROM packages WHERE user_id=?"
                params = [user_id]
                if not include_delivered:
                    sql += " AND is_delivered=0"
                sql += " ORDER BY updated_at DESC"
                with _get_conn() as conn:
                    rows = conn.execute(sql, params).fetchall()

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
                sql = "SELECT * FROM packages WHERE is_delivered=0 ORDER BY updated_at ASC"
                with _get_conn() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute(sql)
                        rows = cur.fetchall()
            else:
                sql = "SELECT * FROM packages WHERE is_delivered=0 ORDER BY updated_at ASC"
                with _get_conn() as conn:
                    rows = conn.execute(sql).fetchall()

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
                sql = "DELETE FROM packages WHERE user_id=%s AND resi=%s"
                with _get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql, (user_id, resi.upper()))
                        count = cur.rowcount
                    conn.commit()
                return count > 0
            else:
                sql = "DELETE FROM packages WHERE user_id=? AND resi=?"
                with _get_conn() as conn:
                    cursor = conn.execute(sql, (user_id, resi.upper()))
                    conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error remove_package: {e}")
            return False

    def remove_all_packages(self, user_id):
        try:
            if USE_POSTGRES:
                sql = "DELETE FROM packages WHERE user_id=%s"
                with _get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql, (user_id,))
                        count = cur.rowcount
                    conn.commit()
                return count
            else:
                sql = "DELETE FROM packages WHERE user_id=?"
                with _get_conn() as conn:
                    cursor = conn.execute(sql, (user_id,))
                    conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error remove_all_packages: {e}")
            return 0

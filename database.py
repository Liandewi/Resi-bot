"""
Database menggunakan SQLite untuk menyimpan data resi yang ditracking.
"""

import sqlite3
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
DB_PATH = "resi_tracker.db"


class Database:
    def __init__(self):
        self._create_tables()

    def _get_conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        """Buat tabel jika belum ada."""
        with self._get_conn() as conn:
            conn.execute("""
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
            """)
            conn.commit()
        logger.info("✅ Database siap.")

    def add_package(self, user_id: int, resi: str, courier: str,
                    label: str, last_status: str, history: list) -> bool:
        """Tambah resi baru."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO packages (user_id, resi, courier, label, last_status, history)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, resi.upper(), courier.lower(), label,
                      last_status, json.dumps(history)))
                conn.commit()
            logger.info(f"✅ Resi {resi} ditambahkan untuk user {user_id}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Resi {resi} sudah ada untuk user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error add_package: {e}")
            return False

    def update_package(self, user_id: int, resi: str, last_status: str, history: list):
        """Update status dan history resi."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    UPDATE packages
                    SET last_status = ?, history = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND resi = ?
                """, (last_status, json.dumps(history), user_id, resi.upper()))
                conn.commit()
        except Exception as e:
            logger.error(f"Error update_package: {e}")

    def mark_delivered(self, user_id: int, resi: str):
        """Tandai paket sebagai terkirim (auto-stop tracking)."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    UPDATE packages SET is_delivered = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND resi = ?
                """, (user_id, resi.upper()))
                conn.commit()
            logger.info(f"📦 Resi {resi} ditandai sebagai terkirim.")
        except Exception as e:
            logger.error(f"Error mark_delivered: {e}")

    def get_package(self, user_id: int, resi: str) -> dict | None:
        """Ambil data satu paket."""
        try:
            with self._get_conn() as conn:
                row = conn.execute("""
                    SELECT * FROM packages WHERE user_id = ? AND resi = ?
                """, (user_id, resi.upper())).fetchone()

            if row:
                pkg = dict(row)
                pkg["history"] = json.loads(pkg.get("history", "[]"))
                return pkg
            return None
        except Exception as e:
            logger.error(f"Error get_package: {e}")
            return None

    def get_user_packages(self, user_id: int, include_delivered: bool = False) -> list:
        """Ambil semua paket milik user."""
        try:
            with self._get_conn() as conn:
                query = "SELECT * FROM packages WHERE user_id = ?"
                params = [user_id]

                if not include_delivered:
                    query += " AND is_delivered = 0"

                query += " ORDER BY updated_at DESC"
                rows = conn.execute(query, params).fetchall()

            packages = []
            for row in rows:
                pkg = dict(row)
                pkg["history"] = json.loads(pkg.get("history", "[]"))
                packages.append(pkg)
            return packages
        except Exception as e:
            logger.error(f"Error get_user_packages: {e}")
            return []

    def get_all_active_packages(self) -> list:
        """Ambil semua paket aktif dari semua user (untuk auto-check)."""
        try:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT * FROM packages
                    WHERE is_delivered = 0
                    ORDER BY updated_at ASC
                """).fetchall()

            packages = []
            for row in rows:
                pkg = dict(row)
                pkg["history"] = json.loads(pkg.get("history", "[]"))
                packages.append(pkg)
            return packages
        except Exception as e:
            logger.error(f"Error get_all_active_packages: {e}")
            return []

    def remove_package(self, user_id: int, resi: str) -> bool:
        """Hapus satu resi dari tracking."""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute("""
                    DELETE FROM packages WHERE user_id = ? AND resi = ?
                """, (user_id, resi.upper()))
                conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error remove_package: {e}")
            return False

    def remove_all_packages(self, user_id: int) -> int:
        """Hapus semua resi user dari tracking."""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM packages WHERE user_id = ?", (user_id,)
                )
                conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Error remove_all_packages: {e}")
            return 0

    def get_stats(self) -> dict:
        """Statistik database."""
        try:
            with self._get_conn() as conn:
                total = conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
                active = conn.execute("SELECT COUNT(*) FROM packages WHERE is_delivered=0").fetchone()[0]
                users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM packages").fetchone()[0]
            return {"total": total, "active": active, "users": users}
        except Exception as e:
            logger.error(f"Error get_stats: {e}")
            return {}

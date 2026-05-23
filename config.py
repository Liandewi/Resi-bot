"""
Konfigurasi Bot - Edit file ini sesuai kebutuhan.
ATAU gunakan file .env (lebih aman untuk production).
"""

import os
from dotenv import load_dotenv

load_dotenv()  # Muat dari file .env jika ada

# ============================================================
# WAJIB DIISI - Ganti dengan nilai milikmu!
# ============================================================

# Token bot dari @BotFather di Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "MASUKKAN_BOT_TOKEN_DISINI")

# API Key dari BinderByte (daftar gratis di https://binderbyte.com)
# Mendukung 60+ kurir: JNE, J&T, SiCepat, Anteraja, Pos, dll.
BINDERBYTE_API_KEY = os.getenv("BINDERBYTE_API_KEY", "MASUKKAN_BINDERBYTE_API_KEY_DISINI")

# ============================================================
# OPSIONAL - Bisa dibiarkan default
# ============================================================

# Seberapa sering bot auto-cek update (dalam menit)
# Default: 30 menit. Minimal disarankan 15 menit agar tidak kena rate limit.
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))

# Maksimal resi yang bisa ditrack per user (0 = unlimited)
MAX_PACKAGES_PER_USER = int(os.getenv("MAX_PACKAGES_PER_USER", "20"))

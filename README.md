# 🤖 Bot Tracking Resi Otomatis

Bot Telegram untuk tracking semua resi paket dengan notifikasi otomatis.

## ✨ Fitur
- 📦 Tracking 60+ kurir (JNE, J&T, SiCepat, Anteraja, Pos, TIKI, dll.)
- 🔔 Notifikasi otomatis setiap ada update status
- ✅ Auto-stop tracking ketika paket terkirim
- 💾 Database SQLite (tidak perlu setup server database)
- 🚀 Ringan dan mudah dijalankan

## 📋 Persiapan

### 1. Buat Bot di Telegram
1. Buka Telegram, cari **@BotFather**
2. Kirim `/newbot`
3. Ikuti instruksi, masukkan nama dan username bot
4. **Salin token bot** yang diberikan

### 2. Daftar API BinderByte (GRATIS)
1. Buka https://binderbyte.com
2. Klik **Daftar** / Register
3. Verifikasi email
4. Buka dashboard, **salin API key**

### 3. Setup Project
```bash
# Clone atau download project ini
cd resi-bot

# Install Python dependencies
pip install -r requirements.txt

# Buat file konfigurasi
cp .env.example .env
```

### 4. Isi Konfigurasi
Edit file `.env`:
```
BOT_TOKEN=token_dari_botfather_kamu
BINDERBYTE_API_KEY=api_key_dari_binderbyte_kamu
CHECK_INTERVAL_MINUTES=30
```

### 5. Jalankan Bot
```bash
python bot.py
```

Bot akan mulai berjalan! Buka Telegram dan cari bot kamu.

---

## 💬 Perintah Bot

| Perintah | Fungsi |
|----------|--------|
| `/start` | Mulai & lihat panduan |
| `/track <resi> <kurir>` | Tambah resi baru |
| `/track <resi> <kurir> <label>` | Tambah resi dengan nama |
| `/list` | Lihat semua resi aktif |
| `/cek <resi>` | Cek status sekarang |
| `/stop <resi>` | Hentikan tracking resi |
| `/stopall` | Hentikan semua tracking |

## 🚚 Kurir yang Didukung

| Kode | Kurir |
|------|-------|
| `jne` | JNE |
| `jnt` | J&T Express |
| `sicepat` | SiCepat |
| `anteraja` | Anteraja |
| `pos` | Pos Indonesia |
| `tiki` | TIKI |
| `lion` | Lion Parcel |
| `ninja` | Ninja Xpress |
| `wahana` | Wahana |
| `idexpress` | ID Express |
| `sap` | SAP Express |
| `gosend` | GoSend |

Dan masih banyak lagi! Lihat daftar lengkap di https://binderbyte.com

## 🔧 Menjalankan di Background (Server/VPS)

```bash
# Menggunakan screen
screen -S resi-bot
python bot.py
# Tekan Ctrl+A lalu D untuk detach

# Atau menggunakan nohup
nohup python bot.py > bot.log 2>&1 &

# Atau menggunakan systemd (direkomendasikan untuk production)
# Buat file /etc/systemd/system/resi-bot.service
```

Contoh systemd service:
```ini
[Unit]
Description=Resi Tracking Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/resi-bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable resi-bot
sudo systemctl start resi-bot
sudo systemctl status resi-bot
```

## ❓ FAQ

**Q: Bot tidak merespons?**
A: Pastikan BOT_TOKEN sudah benar dan bot sedang berjalan (`python bot.py`)

**Q: Resi tidak ditemukan?**
A: Pastikan kurir yang dipilih sesuai dengan nomor resi

**Q: Notifikasi tidak masuk?**
A: Cek interval check di `.env` (CHECK_INTERVAL_MINUTES). Pastikan user sudah pernah kirim pesan ke bot.

**Q: Apakah bisa jalan 24/7?**
A: Ya, jalankan di VPS/server menggunakan screen, PM2, atau systemd

---
Made with ❤️ | API by BinderByte

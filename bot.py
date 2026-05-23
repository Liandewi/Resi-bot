"""
Bot Telegram - Tracking Resi Otomatis
Mendukung: JNE, J&T, SiCepat, Anteraja, Pos Indonesia, Tiki, Lion Parcel, dll.
API: BinderByte (binderbyte.com) - daftar gratis untuk mendapatkan API key
"""

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from database import Database
from tracker import Tracker
from config import BOT_TOKEN, BINDERBYTE_API_KEY, CHECK_INTERVAL_MINUTES

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

db = Database()
tracker = Tracker(BINDERBYTE_API_KEY)

COURIER_EMOJIS = {
    "jne": "🟡", "jnt": "🔴", "sicepat": "🟠", "anteraja": "🟣",
    "pos": "🔵", "tiki": "🟢", "lion": "🟤", "ninja": "⚫",
    "wahana": "🔴", "idexpress": "🟡", "sap": "🔵",
}

SUPPORTED_COURIERS = [
    "jne", "jnt", "sicepat", "anteraja", "pos", "tiki",
    "lion", "ninja", "wahana", "idexpress", "sap", "gosend",
    "grab", "lalamove", "ncs", "rex", "rpx", "sentral",
    "star", "jet", "pandu", "dse", "first", "indah", "spx", "shopee", "spe"
]


def format_status_message(package: dict, history: list) -> str:
    """Format pesan tracking menjadi tampilan yang rapi."""
    courier_emoji = COURIER_EMOJIS.get(package["courier"].lower(), "📦")
    status_icon = "✅" if "terkirim" in package["last_status"].lower() or "delivered" in package["last_status"].lower() else "🚚"

    msg = f"{courier_emoji} *{package['courier'].upper()}* | `{package['resi']}`\n"
    msg += f"📝 {package.get('label', 'Paket')} \n"
    msg += f"━━━━━━━━━━━━━━━━━━━\n"
    msg += f"{status_icon} *Status Terakhir:*\n"
    msg += f"`{package['last_status']}`\n\n"

    if history:
        msg += "📋 *Riwayat Perjalanan:*\n"
        for i, item in enumerate(history[:8]):  # Tampilkan 8 terbaru
            prefix = "├" if i < len(history[:8]) - 1 else "└"
            msg += f"{prefix} `{item.get('date', '')}` {item.get('desc', '')}\n"

    msg += f"\n🔄 Update otomatis setiap {CHECK_INTERVAL_MINUTES} menit"
    return msg


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pesan sambutan."""
    user = update.effective_user
    text = (
        f"👋 Halo, *{user.first_name}*\\!\n\n"
        "🤖 Saya bot *Tracking Resi Otomatis*\\.\n"
        "Saya bisa memantau paket kamu dari berbagai kurir dan "
        "mengirim notifikasi otomatis setiap ada update\\.\n\n"
        "📦 *Kurir yang didukung:*\n"
        "JNE, J\\&T, SiCepat, Anteraja, Pos Indonesia, TIKI, "
        "Lion Parcel, Ninja Xpress, Wahana, ID Express, SAP, dan banyak lagi\\!\n\n"
        "📌 *Cara pakai:*\n"
        "• `/track <resi> <kurir>` — Tambah resi baru\n"
        "• `/list` — Lihat semua paket aktif\n"
        "• `/stop <resi>` — Berhenti tracking\n"
        "• `/help` — Bantuan lengkap\n\n"
        "📝 *Contoh:*\n"
        "`/track 1234567890 jne`\n"
        "`/track 8877665544 sicepat Baju Online`"
    )
    await update.message.reply_text(text, parse_mode="MarkdownV2")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pesan bantuan."""
    couriers_list = " · ".join([c.upper() for c in SUPPORTED_COURIERS[:12]])
    text = (
        "📖 *Panduan Lengkap Bot Tracking*\n\n"
        f"*Perintah:*\n"
        f"`/track <resi> <kurir> [label]`\n"
        f"  Mulai tracking resi baru\n\n"
        f"`/list`\n"
        f"  Tampilkan semua resi yang dipantau\n\n"
        f"`/cek <resi>`\n"
        f"  Cek status resi sekarang\n\n"
        f"`/stop <resi>`\n"
        f"  Hentikan tracking resi\n\n"
        f"`/stopall`\n"
        f"  Hentikan semua tracking\n\n"
        f"*Kurir yang didukung:*\n"
        f"`{couriers_list}` ...dan lebih banyak lagi\n\n"
        f"*Contoh penggunaan:*\n"
        f"`/track JD123456789 jne Sepatu Adidas`\n"
        f"`/track 8901234567 sicepat`\n"
        f"`/track 000123456789 pos Buku Pelajaran`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tambah resi baru untuk ditracking."""
    user_id = update.effective_user.id

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Format salah!\n\n"
            "Gunakan: `/track <nomor_resi> <kurir> [label]`\n\n"
            "Contoh:\n"
            "`/track 1234567890 jne`\n"
            "`/track 8877665544 sicepat Baju Koko`",
            parse_mode="Markdown"
        )
        return

    resi = context.args[0].strip().upper()
    courier = context.args[1].strip().lower()
    label = " ".join(context.args[2:]) if len(context.args) > 2 else f"Paket {courier.upper()}"

    if courier not in SUPPORTED_COURIERS:
        await update.message.reply_text(
            f"❌ Kurir `{courier}` tidak dikenali.\n\n"
            f"Kurir yang didukung:\n`{', '.join(SUPPORTED_COURIERS)}`",
            parse_mode="Markdown"
        )
        return

    # Cek apakah sudah ditambahkan
    existing = db.get_package(user_id, resi)
    if existing:
        await update.message.reply_text(
            f"⚠️ Resi `{resi}` sudah ada dalam daftar tracking.",
            parse_mode="Markdown"
        )
        return

    msg = await update.message.reply_text(f"🔍 Mengecek resi `{resi}`...", parse_mode="Markdown")

    # Cek status awal
    result = await tracker.check(resi, courier)

    if result["success"]:
        last_status = result["last_status"]
        history = result["history"]

        db.add_package(user_id, resi, courier, label, last_status, history)

        package = {"resi": resi, "courier": courier, "label": label, "last_status": last_status}
        text = f"✅ *Resi berhasil ditambahkan!*\n\n" + format_status_message(package, history)

        keyboard = [[InlineKeyboardButton("🗑 Stop Tracking", callback_data=f"stop_{resi}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await msg.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await msg.edit_text(
            f"❌ *Gagal mengambil data resi* `{resi}`\n\n"
            f"Pesan error: {result.get('error', 'Unknown error')}\n\n"
            f"Pastikan:\n"
            f"• Nomor resi benar\n"
            f"• Kurir yang dipilih sesuai\n"
            f"• API key valid",
            parse_mode="Markdown"
        )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan semua paket yang sedang ditracking."""
    user_id = update.effective_user.id
    packages = db.get_user_packages(user_id)

    if not packages:
        await update.message.reply_text(
            "📭 Belum ada resi yang dipantau.\n\n"
            "Gunakan `/track <resi> <kurir>` untuk mulai tracking.",
            parse_mode="Markdown"
        )
        return

    text = f"📦 *Daftar Paket Aktif ({len(packages)} resi):*\n\n"

    keyboard = []
    for pkg in packages:
        courier_emoji = COURIER_EMOJIS.get(pkg["courier"].lower(), "📦")
        is_delivered = "terkirim" in pkg["last_status"].lower() or "delivered" in pkg["last_status"].lower()
        status_icon = "✅" if is_delivered else "🚚"

        text += (
            f"{courier_emoji} *{pkg['label']}*\n"
            f"  `{pkg['resi']}` ({pkg['courier'].upper()})\n"
            f"  {status_icon} {pkg['last_status'][:60]}{'...' if len(pkg['last_status']) > 60 else ''}\n\n"
        )
        keyboard.append([
            InlineKeyboardButton(f"🔍 Cek {pkg['resi']}", callback_data=f"cek_{pkg['resi']}_{pkg['courier']}"),
            InlineKeyboardButton("🗑 Stop", callback_data=f"stop_{pkg['resi']}")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def cek_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cek status resi secara manual."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Gunakan: `/cek <nomor_resi>`", parse_mode="Markdown")
        return

    resi = context.args[0].strip().upper()
    package = db.get_package(user_id, resi)

    if not package:
        await update.message.reply_text(
            f"❌ Resi `{resi}` tidak ditemukan dalam daftar tracking.\n"
            f"Tambahkan dulu dengan `/track {resi} <kurir>`",
            parse_mode="Markdown"
        )
        return

    msg = await update.message.reply_text(f"🔍 Mengecek resi `{resi}`...", parse_mode="Markdown")
    result = await tracker.check(resi, package["courier"])

    if result["success"]:
        db.update_package(user_id, resi, result["last_status"], result["history"])
        text = format_status_message(package, result["history"])

        keyboard = [[InlineKeyboardButton("🗑 Stop Tracking", callback_data=f"stop_{resi}")]]
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await msg.edit_text(f"❌ Gagal cek resi: {result.get('error', 'Unknown error')}")


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hentikan tracking resi tertentu."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Gunakan: `/stop <nomor_resi>`", parse_mode="Markdown")
        return

    resi = context.args[0].strip().upper()
    deleted = db.remove_package(user_id, resi)

    if deleted:
        await update.message.reply_text(f"✅ Tracking resi `{resi}` dihentikan.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Resi `{resi}` tidak ditemukan.", parse_mode="Markdown")


async def stopall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hentikan semua tracking."""
    user_id = update.effective_user.id
    count = db.remove_all_packages(user_id)

    if count > 0:
        await update.message.reply_text(f"✅ Semua {count} resi telah dihapus dari tracking.")
    else:
        await update.message.reply_text("📭 Tidak ada resi yang sedang dipantau.")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk tombol inline keyboard."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data.startswith("stop_"):
        resi = data[5:]
        deleted = db.remove_package(user_id, resi)
        if deleted:
            await query.edit_message_text(f"✅ Tracking resi `{resi}` dihentikan.", parse_mode="Markdown")
        else:
            await query.answer("Resi tidak ditemukan.", show_alert=True)

    elif data.startswith("cek_"):
        parts = data[4:].split("_")
        resi = parts[0]
        courier = parts[1] if len(parts) > 1 else ""
        package = db.get_package(user_id, resi)
        if package:
            await query.edit_message_text(f"🔍 Mengecek `{resi}`...", parse_mode="Markdown")
            result = await tracker.check(resi, courier or package["courier"])
            if result["success"]:
                db.update_package(user_id, resi, result["last_status"], result["history"])
                text = format_status_message(package, result["history"])
                keyboard = [[InlineKeyboardButton("🗑 Stop Tracking", callback_data=f"stop_{resi}")]]
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def auto_check_job(context: ContextTypes.DEFAULT_TYPE):
    """Job yang berjalan otomatis untuk cek semua resi."""
    logger.info("🔄 Menjalankan auto-check semua resi...")
    all_packages = db.get_all_active_packages()

    for pkg in all_packages:
        try:
            result = await tracker.check(pkg["resi"], pkg["courier"])

            if result["success"] and result["last_status"] != pkg["last_status"]:
                # Ada perubahan status!
                old_status = pkg["last_status"]
                new_status = result["last_status"]

                db.update_package(pkg["user_id"], pkg["resi"], new_status, result["history"])

                courier_emoji = COURIER_EMOJIS.get(pkg["courier"].lower(), "📦")
                is_delivered = "terkirim" in new_status.lower() or "delivered" in new_status.lower()

                notification = (
                    f"🔔 *UPDATE PAKET!*\n\n"
                    f"{courier_emoji} *{pkg['label']}*\n"
                    f"`{pkg['resi']}` ({pkg['courier'].upper()})\n\n"
                    f"📌 Status baru:\n`{new_status}`\n\n"
                    f"📌 Status sebelumnya:\n`{old_status}`\n\n"
                )

                if result["history"]:
                    notification += "📋 Update terbaru:\n"
                    for item in result["history"][:3]:
                        notification += f"• `{item.get('date', '')}` {item.get('desc', '')}\n"

                if is_delivered:
                    notification += "\n✅ *Paket telah terkirim! Tracking dihentikan.*"
                    db.mark_delivered(pkg["user_id"], pkg["resi"])

                try:
                    await context.bot.send_message(
                        chat_id=pkg["user_id"],
                        text=notification,
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ Notifikasi dikirim ke user {pkg['user_id']} untuk resi {pkg['resi']}")
                except Exception as e:
                    logger.error(f"Gagal kirim notifikasi ke {pkg['user_id']}: {e}")

            await asyncio.sleep(1)  # Jeda antar request API

        except Exception as e:
            logger.error(f"Error checking resi {pkg['resi']}: {e}")

    logger.info(f"✅ Auto-check selesai. Total {len(all_packages)} resi dicek.")


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk pesan yang tidak dikenali."""
    text = update.message.text.strip()

    # Jika terlihat seperti nomor resi (hanya angka/huruf, cukup panjang)
    if text.replace(" ", "").isalnum() and len(text) >= 8:
        await update.message.reply_text(
            f"🤔 Sepertinya itu nomor resi `{text}`.\n\n"
            f"Gunakan format:\n`/track {text} <kurir>`\n\n"
            f"Contoh: `/track {text} jne`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❓ Perintah tidak dikenal. Ketik `/help` untuk bantuan.",
            parse_mode="Markdown"
        )


def main():
    """Jalankan bot."""
    if not BOT_TOKEN or BOT_TOKEN == "MASUKKAN_BOT_TOKEN_DISINI":
        print("❌ ERROR: BOT_TOKEN belum diisi di file config.py atau .env!")
        return

    if not BINDERBYTE_API_KEY or BINDERBYTE_API_KEY == "MASUKKAN_BINDERBYTE_API_KEY_DISINI":
        print("❌ ERROR: BINDERBYTE_API_KEY belum diisi di file config.py atau .env!")
        print("   Daftar gratis di: https://binderbyte.com")
        return

    print("🤖 Bot Tracking Resi sedang berjalan...")
    print(f"🔄 Auto-check setiap {CHECK_INTERVAL_MINUTES} menit")

    app = Application.builder().token(BOT_TOKEN).build()

    # Daftarkan handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("track", track_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("cek", cek_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("stopall", stopall_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    # Jadwalkan auto-check
    app.job_queue.run_repeating(
        auto_check_job,
        interval=CHECK_INTERVAL_MINUTES * 60,
        first=60  # Mulai 1 menit setelah bot aktif
    )

    print("✅ Bot siap! Tekan Ctrl+C untuk menghentikan.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

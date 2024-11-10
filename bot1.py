import logging
from datetime import datetime
import sqlite3

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# Token bot dan ID channel
TOKEN = '7221290461:AAGL3dK4ceWjEcM1BuOOilGJe1pXgPk2TzE'
CHANNEL_ID = '-1002078297463'

# Username admin Telegram (tanpa '@')
ADMIN_USERNAME = 'zixxi99'

# Koneksi database SQLite
conn = sqlite3.connect('testimoni.db')
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS testimoni (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        foto BLOB,
        harga TEXT,
        item TEXT,
        jumlah TEXT
    )
"""
)
conn.commit()

# State untuk menyimpan data testimoni
testimoni_data = {}

# Fungsi untuk mendapatkan tanggal saat ini
def get_formatted_date():
    return datetime.now().strftime("%Y-%m-%d")

# Fungsi untuk mengirim testimoni ke channel dengan tombol
async def send_to_channel(context, photo_bytes, testimoni_data):
    caption = f"""
Testimoni Baru:

📆 Tanggal: {get_formatted_date()}
💰 Harga: {testimoni_data['harga']}
📦 Produk: {testimoni_data['item']}
🧮 Jumlah: {testimoni_data['jumlah']}

Jika kamu tertarik dengan produk ini bisa membelinya di admin 👇
    """

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🛒Buy Disini", url=f"https://t.me/{ADMIN_USERNAME}")]]
    )

    await context.bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=photo_bytes,
        caption=caption.strip(),
        reply_markup=keyboard,
    )

# Handler untuk perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Silakan kirim foto produk untuk memulai testimoni.")

# Handler untuk foto
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
    photo_bytes = await photo_file.download_as_bytearray()

    cursor.execute('INSERT INTO testimoni (foto) VALUES (?)', (photo_bytes,))
    testimoni_id = cursor.lastrowid
    conn.commit()

    testimoni_data[user_id] = {'testimoni_id': testimoni_id}
    await update.message.reply_text("Berapa harga produknya?")

# Handler untuk pesan teks
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in testimoni_data:
        if 'harga' not in testimoni_data[user_id]:
            testimoni_data[user_id]['harga'] = update.message.text
            await update.message.reply_text("Apa nama produknya?")
        elif 'item' not in testimoni_data[user_id]:
            testimoni_data[user_id]['item'] = update.message.text
            await update.message.reply_text("Berapa jumlah produk yang dibeli?")
        elif 'jumlah' not in testimoni_data[user_id]:
            testimoni_data[user_id]['jumlah'] = update.message.text

            # Ambil foto dari database
            cursor.execute('SELECT foto FROM testimoni WHERE id = ?', (testimoni_data[user_id]['testimoni_id'],))
            photo_bytes = cursor.fetchone()[0]

            # Kirim ke channel
            await send_to_channel(context, photo_bytes, testimoni_data[user_id])

            # Update data testimoni di database
            cursor.execute('''UPDATE testimoni SET harga = ?, item = ?, jumlah = ? WHERE id = ?''', 
                           (testimoni_data[user_id]['harga'], testimoni_data[user_id]['item'], testimoni_data[user_id]['jumlah'], testimoni_data[user_id]['testimoni_id']))
            conn.commit()

            del testimoni_data[user_id]

# Handler untuk callback query (saat tombol diklik)
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

# Membuat aplikasi bot
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()

    # Menambahkan handler
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # Menjalankan bot
    application.run_polling()

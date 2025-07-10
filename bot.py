import json
import logging
import os
from datetime import datetime, timedelta
import pytz
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

# Cấu hình Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Khởi tạo Scheduler
timezone = pytz.timezone("Asia/Ho_Chi_Minh")
scheduler = BackgroundScheduler(timezone=timezone)
scheduler.start()

# File JSON lưu lời nhắc
DATA_FILE = "reminders.json"

# Đọc dữ liệu từ file
def load_reminders():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump([], f)
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

# Ghi dữ liệu vào file
def save_reminders(reminders):
    with open(DATA_FILE, 'w') as f:
        json.dump(reminders, f, indent=4)

# Gửi tin nhắn
async def send_message(context: ContextTypes.DEFAULT_TYPE, chat_id, text):
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logging.error(f"Gửi lỗi: {e}")

# Tạo các job gửi nhắc nhở
def schedule_reminder_jobs(application, reminder):
    chat_id = reminder['chat_id']
    day = int(reminder['day'])
    text = reminder['text']
    reminder_id = reminder['id']

    for offset, label in [(-2, "còn 2 ngày để thanh toán:"),
                          (-1, "còn 1 ngày để thanh toán:"),
                          (0, "GẤP! Thanh toán ngay:")]:
        run_day = (day + offset - 1) % 31 + 1
        scheduler.add_job(
            lambda: application.create_task(send_message(application.bot, chat_id, f"{label} {text}")),
            CronTrigger(day=run_day, hour=8, minute=0, timezone=timezone),
            id=f"{reminder_id}_{offset}",
            replace_existing=True
        )

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Bot đang chạy...\nGõ /add [ngày] [nội dung] để thêm lời nhắc.")

# /chatid
async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Chat ID của bạn là: `{update.effective_chat.id}`", parse_mode='Markdown')

# /add
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.split(' ', 2)
        if len(parts) < 3:
            await update.message.reply_text("⚠️ Sai cú pháp. Dùng: /add [ngày] [nội dung]")
            return

        day = int(parts[1])
        if not (1 <= day <= 31):
            await update.message.reply_text("⚠️ Ngày phải nằm trong khoảng từ 1 đến 31.")
            return

        text = parts[2]
        chat_id = update.effective_chat.id
        reminders = load_reminders()
        reminder_id = len(reminders) + 1

        new_reminder = {
            "id": reminder_id,
            "chat_id": chat_id,
            "day": day,
            "text": text
        }

        reminders.append(new_reminder)
        save_reminders(reminders)
        schedule_reminder_jobs(context.application, new_reminder)

        await update.message.reply_text(f"✅ Đã thêm lời nhắc ID {reminder_id}: Ngày {day} - {text}")

    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

# /list
async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = load_reminders()
    chat_id = update.effective_chat.id
    filtered = [r for r in reminders if r['chat_id'] == chat_id]

    if not filtered:
        await update.message.reply_text("📭 Không có lời nhắc nào.")
        return

    msg = "📋 Danh sách lời nhắc:\n"
    for r in filtered:
        msg += f"🔷 ID {r['id']}: Ngày {r['day']} - {r['text']}\n"
    await update.message.reply_text(msg)

# /remove
async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.split(' ', 1)
        if len(parts) < 2:
            await update.message.reply_text("⚠️ Dùng: /remove [ID]")
            return

        remove_id = int(parts[1])
        reminders = load_reminders()
        new_reminders = [r for r in reminders if r['id'] != remove_id]
        if len(new_reminders) == len(reminders):
            await update.message.reply_text("❌ Không tìm thấy ID.")
            return

        # Xóa jobs
        for offset in [-2, -1, 0]:
            job_id = f"{remove_id}_{offset}"
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

        save_reminders(new_reminders)
        await update.message.reply_text(f"🗑️ Đã xóa lời nhắc ID {remove_id}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

# Main
def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chatid", chatid))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("remove", remove))

    # Lập lịch nhắc cho lời nhắc đã lưu
    for r in load_reminders():
        schedule_reminder_jobs(app, r)

    print("🤖 Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()

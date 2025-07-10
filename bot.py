import json
import os
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
from apscheduler.schedulers.background import BackgroundScheduler
from uuid import uuid4

DATA_FILE = "data.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return []

def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

def send_reminder(context: CallbackContext, chat_id, message):
    context.bot.send_message(chat_id=chat_id, text=message)

def check_reminders(context: CallbackContext):
    now = datetime.now()
    data = load_data()
    for item in data:
        reminder_day = int(item["day"])
        chat_id = item["chat_id"]
        message = item["message"]
        id_ = item["id"]

        # Tạo ngày tháng hiện tại với ngày nhắc
        try:
            this_month = now.replace(day=reminder_day, hour=8, minute=0, second=0, microsecond=0)
        except ValueError:
            # Ngày không hợp lệ với tháng hiện tại
            continue

        diff_days = (this_month.date() - now.date()).days
        if diff_days == 2:
            send_reminder(context, chat_id, f"⏰ Còn 2 ngày để thanh toán: {message}")
        elif diff_days == 1:
            send_reminder(context, chat_id, f"⏰ Còn 1 ngày để thanh toán: {message}")
        elif diff_days == 0 and now.hour == 8:
            send_reminder(context, chat_id, f"🚨 GẤP! Thanh toán ngay: {message}")

def add_reminder(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    print(f"📌 Chat ID: {chat_id}")  # ✅ In ra chat_id khi dùng /add

    args = context.args
    if len(args) < 2:
        update.message.reply_text("❌ Cú pháp sai. Dùng: /add [ngày] [nội dung nhắc]")
        return
    day = args[0]
    if not day.isdigit() or not (1 <= int(day) <= 31):
        update.message.reply_text("❌ Ngày phải từ 1 đến 31.")
        return
    message = " ".join(args[1:])
    data = load_data()
    new_id = len(data) + 1
    data.append({
        "id": new_id,
        "day": int(day),
        "message": message,
        "chat_id": chat_id
    })
    save_data(data)
    update.message.reply_text(f"✅ Đã thêm lời nhắc ID {new_id}: Ngày {day} - {message}")

def list_reminders(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    data = load_data()
    reminders = [r for r in data if r["chat_id"] == chat_id]
    if not reminders:
        update.message.reply_text("📭 Không có lời nhắc nào.")
        return
    msg = "📋 Danh sách lời nhắc:\n"
    for r in reminders:
        msg += f"🔹 ID {r['id']}: Ngày {r['day']} - {r['message']}\n"
    update.message.reply_text(msg)

def remove_reminder(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        update.message.reply_text("❌ Dùng: /remove [id]")
        return
    rem_id = int(args[0])
    data = load_data()
    new_data = [r for r in data if not (r["id"] == rem_id and r["chat_id"] == chat_id)]
    if len(data) == len(new_data):
        update.message.reply_text("❌ Không tìm thấy ID.")
    else:
        save_data(new_data)
        update.message.reply_text(f"🗑️ Đã xóa lời nhắc ID {rem_id}.")

def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    print(f"👋 /start từ chat_id: {chat_id}")  # ✅ In ra chat_id khi bắt đầu
    update.message.reply_text("🤖 Bot đang chạy! Dùng /add [ngày] [nội dung] để thêm lời nhắc.")

def main():
    TOKEN = os.getenv("BOT_TOKEN") or "YOUR_TELEGRAM_BOT_TOKEN"
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add", add_reminder))
    dp.add_handler(CommandHandler("list", list_reminders))
    dp.add_handler(CommandHandler("remove", remove_reminder))

    # Nếu muốn in chat_id bất kỳ tin nhắn nào:
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, lambda u, c: print(f"📨 Tin nhắn từ chat_id: {u.message.chat_id}")))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: check_reminders(updater.bot), "interval", hours=1)
    scheduler.start()

    print("⚙️ Bot đang chạy...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

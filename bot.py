import os
import json
from datetime import datetime, date
from telegram.ext import Updater, CommandHandler
import threading
import time

# 🔐 Telegram Token từ biến môi trường
TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATA_FILE = "data.json"

# 📦 Load hoặc tạo dữ liệu nếu chưa có
def load_reminders():
    if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
        with open(DATA_FILE, "w") as f:
            json.dump([], f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_reminders(reminders):
    with open(DATA_FILE, "w") as f:
        json.dump(reminders, f, indent=2)

# ➕ /add [ngày] [nội dung]
def add(update, context):
    args = context.args
    if len(args) < 2:
        update.message.reply_text("❌ Dùng: /add [ngày] [nội dung nhắc]")
        return
    try:
        day = int(args[0])
        if not 1 <= day <= 31:
            update.message.reply_text("❌ Ngày phải từ 1 đến 31.")
            return
    except:
        update.message.reply_text("❌ Ngày không hợp lệ.")
        return

    text = " ".join(args[1:])
    reminders = load_reminders()
    new_id = max([r["id"] for r in reminders], default=0) + 1
    reminders.append({
        "id": new_id,
        "day": day,
        "text": text,
        "chat_id": update.message.chat_id
    })
    save_reminders(reminders)
    update.message.reply_text(f"✅ Đã lưu nhắc: ngày {day} - {text}")

# 📋 /list
def list_reminders(update, context):
    chat_id = update.message.chat_id
    reminders = load_reminders()
    user_reminders = [r for r in reminders if r["chat_id"] == chat_id]
    if not user_reminders:
        update.message.reply_text("📭 Bạn chưa có lời nhắc nào.")
        return
    reply = "📋 Danh sách lời nhắc:\n"
    for r in user_reminders:
        reply += f"🔸 ID {r['id']}: Ngày {r['day']} - {r['text']}\n"
    update.message.reply_text(reply)

# ❌ /remove [id]
def remove_reminder(update, context):
    args = context.args
    if len(args) != 1:
        update.message.reply_text("❌ Dùng: /remove [id]")
        return
    try:
        rid = int(args[0])
    except:
        update.message.reply_text("❌ ID phải là số.")
        return

    reminders = load_reminders()
    new_reminders = [r for r in reminders if r["id"] != rid or r["chat_id"] != update.message.chat_id]
    if len(new_reminders) == len(reminders):
        update.message.reply_text("⚠️ Không tìm thấy ID đó.")
    else:
        save_reminders(new_reminders)
        update.message.reply_text(f"✅ Đã xóa lời nhắc ID {rid}")

# ⏰ Kiểm tra và gửi lời nhắc (mỗi sáng 8h)
def check_and_send_reminders():
    today = date.today()
    reminders = load_reminders()
    for r in reminders:
        chat_id = r["chat_id"]
        text = r["text"]
        reminder_day = int(r["day"])
        try:
            reminder_date = date(today.year, today.month, reminder_day)
        except:
            continue  # ví dụ: 31/2 không tồn tại

        delta = (reminder_date - today).days

        if delta == 2:
            bot.send_message(chat_id, f"⏰ Còn 2 ngày để thanh toán: {text}")
        elif delta == 1:
            bot.send_message(chat_id, f"⚠️ Còn 1 ngày để thanh toán: {text}")
        elif delta == 0:
            bot.send_message(chat_id, f"🚨 Gấp! Thanh toán ngay: {text}")

# 🔁 Thread chạy nhắc lúc 8:00 mỗi ngày
def run_scheduler():
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            check_and_send_reminders()
            time.sleep(60)  # tránh lặp trong cùng phút
        time.sleep(20)

# 🚀 Khởi tạo bot
updater = Updater(token=TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("add", add))
dp.add_handler(CommandHandler("list", list_reminders))
dp.add_handler(CommandHandler("remove", remove_reminder))

bot = updater.bot

threading.Thread(target=run_scheduler, daemon=True).start()

print("🤖 Bot đang chạy...")
updater.start_polling()
updater.idle()

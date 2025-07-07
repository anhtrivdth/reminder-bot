import os
import json
from datetime import datetime, timedelta
from telegram.ext import Updater, CommandHandler
import threading
import time

# 🔐 Lấy token từ biến môi trường Railway
TOKEN = os.environ.get("TELEGRAM_TOKEN")

REMINDER_FILE = "reminders.json"

# 📦 Load hoặc khởi tạo reminder list
def load_reminders():
    if not os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, "w") as f:
            json.dump([], f)
    with open(REMINDER_FILE, "r") as f:
        return json.load(f)

def save_reminders(data):
    with open(REMINDER_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ➕ /add lệnh
def add_reminder(update, context):
    try:
        args = context.args
        if len(args) < 2:
            update.message.reply_text("❌ Dùng: /add [ngày] [nội dung]")
            return
        day = int(args[0])
        if not (1 <= day <= 31):
            update.message.reply_text("❌ Ngày phải từ 1 đến 31.")
            return
        message = " ".join(args[1:])
        reminders = load_reminders()
        new_id = max([r["id"] for r in reminders], default=0) + 1
        reminders.append({
            "id": new_id,
            "user_id": update.message.chat_id,
            "day": day,
            "message": message
        })
        save_reminders(reminders)
        update.message.reply_text(f"✅ Đã lưu lời nhắc vào ngày {day} hàng tháng: {message}")
    except Exception as e:
        update.message.reply_text(f"❌ Lỗi: {e}")

# 📋 /list lệnh
def list_reminders(update, context):
    user_id = update.message.chat_id
    reminders = load_reminders()
    user_reminders = [r for r in reminders if r["user_id"] == user_id]
    if not user_reminders:
        update.message.reply_text("📭 Bạn chưa có lời nhắc nào.")
        return
    reply = "📋 Danh sách lời nhắc:\n"
    for r in user_reminders:
        reply += f"🔹 ID {r['id']}: Ngày {r['day']} - {r['message']}\n"
    update.message.reply_text(reply)

# ❌ /remove lệnh
def remove_reminder(update, context):
    try:
        args = context.args
        if len(args) != 1:
            update.message.reply_text("❌ Dùng: /remove [id]")
            return
        rid = int(args[0])
        reminders = load_reminders()
        new_reminders = [r for r in reminders if r["id"] != rid or r["user_id"] != update.message.chat_id]
        if len(new_reminders) == len(reminders):
            update.message.reply_text("⚠️ Không tìm thấy lời nhắc cần xóa.")
        else:
            save_reminders(new_reminders)
            update.message.reply_text(f"✅ Đã xóa lời nhắc ID {rid}.")
    except Exception as e:
        update.message.reply_text(f"❌ Lỗi: {e}")

# ⏰ Hàm kiểm tra và gửi nhắc
def check_and_notify(context):
    now = datetime.now()
    current_day = now.day
    for r in load_reminders():
        if r["user_id"] is None: continue
        for offset in [0, 1, 2]:
            target_day = r["day"] - offset
            # Tránh ngày âm hoặc không hợp lệ
            if target_day <= 0 or target_day > 31: continue
            if current_day == target_day:
                try:
                    if offset == 2:
                        text = f"🔔 Còn 2 ngày để thanh toán: {r['message']}"
                    elif offset == 1:
                        text = f"⚠️ Còn 1 ngày để thanh toán: {r['message']}"
                    else:
                        text = f"🚨 Gấp! Thanh toán ngay: {r['message']}"
                    context.bot.send_message(chat_id=r["user_id"], text=text)
                except Exception as e:
                    print(f"Lỗi gửi tin nhắn: {e}")

# 🧠 Chạy mỗi sáng 8h
def scheduler():
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            print("🔁 Đang kiểm tra nhắc nhở...")
            dummy_context = type("obj", (object,), {"bot": updater.bot})()
            check_and_notify(dummy_context)
            time.sleep(60)  # tránh chạy lặp
        time.sleep(30)

# 🧩 Main
updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("add", add_reminder))
dp.add_handler(CommandHandler("list", list_reminders))
dp.add_handler(CommandHandler("remove", remove_reminder))

# 🔄 Thread riêng cho lịch nhắc
threading.Thread(target=scheduler, daemon=True).start()

print("🤖 Bot đang chạy...")
updater.start_polling()
updater.idle()

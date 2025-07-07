import telegram
from telegram.ext import Updater, CommandHandler
import schedule
import time
import threading
from datetime import datetime
import os

TOKEN = os.environ.get("TELEGRAM_TOKEN")  # lấy từ biến môi trường Railway
bot = telegram.Bot(token=TOKEN)

user_list = set()

def start(update, context):
    chat_id = update.message.chat_id
    user_list.add(chat_id)
    context.bot.send_message(chat_id=chat_id, text="✅ Bạn đã đăng ký nhắc nhở thanh toán.")

def remind_users():
    today = datetime.now().strftime('%d/%m/%Y')
    for user_id in user_list:
        try:
            bot.send_message(chat_id=user_id, text=f"🔔 Hôm nay ({today}) nhớ thanh toán nha!")
        except Exception as e:
            print(f"Lỗi gửi tin cho {user_id}: {e}")

schedule.every().day.at("09:00").do(remind_users)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    threading.Thread(target=run_schedule).start()
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

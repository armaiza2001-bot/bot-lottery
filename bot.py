import telebot
import requests
import time
import threading
import schedule
from datetime import datetime
import os
from flask import Flask

# ดึงค่าจาก Environment Variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROUP_CHAT_ID = os.environ.get('GROUP_CHAT_ID')

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ==========================================
# 🌐 ส่วนของ Web Server (สำหรับ Render)
# ==========================================
@app.route('/')
def home():
    return "Lotto Bot is running!"

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 🎰 ระบบเช็คและแจ้งผลหวย
# ==========================================
def fetch_and_send_lotto():
    # กำหนดวันที่ของวันนี้
    today_str = datetime.now().strftime("%d-%m-%Y")
    
    url = "https://www.xsthm.com/result"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }

    print(f"[System] เริ่มจับตาดูผลหวยงวดวันที่ {today_str} ...")

    while True:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                api_date = data.get("label", "")
                
                # ถ้าวันที่ใน API อัปเดตเป็นของวันนี้แล้ว
                if api_date == today_str:
                    numbers = data.get("items", [])
                    
                    if len(numbers) > 0:
                        prize_1 = numbers[0]       
                        prize_special = numbers[-1] 
                        
                        top_3 = prize_special[-3:] 
                        bottom_2 = prize_1[-2:]    
                        
                        # จัดรูปแบบข้อความ
                        msg = (
                            f"🇻🇳 **ผลหวยฮานอยพิเศษ ออกแล้ว!** 🇻🇳\n"
                            f"📅 งวดวันที่: {api_date}\n\n"
                            f"🎯 **3 ตัวบน:** {top_3}\n"
                            f"👇 **2 ตัวล่าง:** {bottom_2}\n"
                        )
                        
                        # ส่งเข้ากลุ่ม
                        bot.send_message(GROUP_CHAT_ID, msg)
                        print("[System] ส่งผลหวยเข้ากลุ่มเรียบร้อยแล้ว!")
                        
                        # ทะลุลูปออกไป รอทำงานใหม่วันพรุ่งนี้
                        break 
                else:
                    # ถ้าเว็บยังไม่อัปเดต ให้แสดงข้อความว่ารออีก 10 วินาที
                    print(f"[System] ผลของวันทียังไม่ออก รออีก 10 วินาที...")
            
        except Exception as e:
            print(f"[Error] เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
            
        # พัก 10 วินาทีแล้วดึง API ใหม่
        time.sleep(10)

# ==========================================
# ⏰ ระบบตั้งเวลาทำงานอัตโนมัติ (Scheduler)
# ==========================================
def schedule_checker():
    # ตั้งเวลาให้เริ่มเช็คผลตอน 17:30 น. ของทุกวัน
    schedule.every().day.at("17:30").do(fetch_and_send_lotto)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# ==========================================
# 🚀 จุดเริ่มต้นการทำงานของโปรแกรม
# ==========================================
if __name__ == "__main__":
    # 1. รัน Web Server แยกไปอีก 1 Thread
    threading.Thread(target=run_server, daemon=True).start()
    
    # 2. รันระบบตั้งเวลาแยกไปอีก 1 Thread
    threading.Thread(target=schedule_checker, daemon=True).start()
    
    # 3. รันบอท
    print("Bot is up and running...")
    bot.infinity_polling()

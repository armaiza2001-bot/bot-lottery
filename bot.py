import telebot
import requests
import time
import threading
from datetime import datetime
import pytz
import os
from flask import Flask

# ดึงค่าตัวแปรจาก Render
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROUP_CHAT_ID = os.environ.get('GROUP_CHAT_ID')

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
# ตั้งค่าโซนเวลาเป็นของประเทศไทย
tz = pytz.timezone('Asia/Bangkok')

# ==========================================
# 🌐 1. ส่วนของ Web Server (กัน Render ปิดบอท)
# ==========================================
@app.route('/')
def home():
    return "Lotto Bot is running!"

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 🎰 2. ระบบเช็คและแจ้งผลหวยฮานอยพิเศษ
# ==========================================
def fetch_and_send_lotto():
    today_str = datetime.now(tz).strftime("%d-%m-%Y")
    url = "https://www.xsthm.com/result"
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
    }

    print(f"[System] เริ่มดึงข้อมูล งวดวันที่ {today_str} ...")
    
    # ส่งข้อความไปบอกแอดมินในกลุ่มว่าเริ่มรอผลแล้ว
    bot.send_message(GROUP_CHAT_ID, f"⏳ บอทกำลังรอผลหวยฮานอยพิเศษ งวดวันที่ {today_str} ครับ...")

    while True:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                api_date = data.get("label", "")
                
                # ถ้าเว็บอัปเดตเป็นของวันนี้แล้ว
                if api_date == today_str:
                    numbers = data.get("items", [])
                    if len(numbers) > 0:
                        prize_1 = numbers[0]       
                        prize_special = numbers[-1] 
                        
                        top_3 = prize_special[-3:] 
                        bottom_2 = prize_1[-2:]    
                        
                        msg = (
                            f"🇻🇳 **ผลหวยฮานอยพิเศษ** 🇻🇳\n"
                            f"📅 งวดวันที่: {api_date}\n\n"
                            f"🎯 **3 ตัวบน:** {top_3}\n"
                            f"👇 **2 ตัวล่าง:** {bottom_2}\n"
                        )
                        
                        bot.send_message(GROUP_CHAT_ID, msg)
                        print("[System] ส่งผลหวยเข้ากลุ่มเรียบร้อยแล้ว!")
                        break # ทำงานเสร็จ ออกจากลูปได้
                else:
                    print(f"[System] ผลยังไม่ออก (เว็บแสดง {api_date}) รออีก 10 วินาที...")
                    
        except Exception as e:
            print(f"[Error] ดึงข้อมูลไม่ได้: {e}")
            
        time.sleep(10) # พัก 10 วินาทีแล้วเช็คใหม่

# ==========================================
# 💬 3. ระบบตอบกลับคำสั่ง Telegram (เพิ่มใหม่)
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "สวัสดีครับ! 🤖 บอทแจ้งผลหวยฮานอยพิเศษออนไลน์และพร้อมทำงานแล้วครับ\n\nเดี๋ยวผมจะคอยส่งผลหวยให้ในกลุ่มนี้อัตโนมัติ ทุกวันเวลา 17:30 น. นะครับ 🚀")

# ==========================================
# ⏰ 4. ระบบเช็คเวลา 17:30 น. (ตามเวลาไทย)
# ==========================================
def time_checker():
    has_run_today = False
    last_check_date = ""

    while True:
        now = datetime.now(tz)
        current_date = now.strftime("%d-%m-%Y")

        # ถ้าระบบขึ้นวันใหม่ ให้รีเซ็ตสถานะ
        if current_date != last_check_date:
            has_run_today = False
            last_check_date = current_date

        # ถ้าถึงเวลา 17:30 น. และยังไม่ได้รันของวันนี้
        if now.hour == 17 and now.minute == 30 and not has_run_today:
            has_run_today = True
            # สั่งให้ฟังก์ชันหาหวยเริ่มทำงาน
            threading.Thread(target=fetch_and_send_lotto, daemon=True).start()

        time.sleep(30) # เช็คเวลาทุกๆ ครึ่งนาที

# ==========================================
# 🚀 5. เริ่มการทำงานทั้งหมด
# ==========================================
if __name__ == "__main__":
    # 1. รัน Web Server
    threading.Thread(target=run_server, daemon=True).start()
    
    # 2. รันระบบจับเวลา
    threading.Thread(target=time_checker, daemon=True).start()
    
    # 3. รันบอท
    print("Bot is up and running...")
    bot.infinity_polling()

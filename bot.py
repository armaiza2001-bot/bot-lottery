import telebot
import requests
import time
import threading
from datetime import datetime
import pytz
import os
from flask import Flask
from bs4 import BeautifulSoup # นำเข้าเครื่องมือดึงข้อมูลหน้าเว็บ

# ดึงค่าตัวแปรจาก Render
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROUP_CHAT_ID = os.environ.get('GROUP_CHAT_ID')

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
tz = pytz.timezone('Asia/Bangkok')

# ==========================================
# 🌐 1. ส่วนของ Web Server
# ==========================================
@app.route('/')
def home():
    return "Lotto Bot is running!"

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 🎰 2.1 ดึงผล: ฮานอยพิเศษ (API)
# ==========================================
def fetch_hanoi_special():
    today_str = datetime.now(tz).strftime("%d-%m-%Y")
    url = "https://www.xsthm.com/result"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอยพิเศษ** งวดวันที่ {today_str} ครับ...")

    while True:
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                api_date = data.get("label", "")
                
                if api_date == today_str:
                    numbers = data.get("items", [])
                    if len(numbers) > 0:
                        prize_1 = numbers[0]       
                        prize_special = numbers[-1] 
                        top_3 = prize_special[-3:] 
                        bottom_2 = prize_1[-2:]    
                        
                        msg = (f"🇻🇳 **ผลหวยฮานอยพิเศษ** 🇻🇳\n📅 วันที่: {api_date}\n\n"
                               f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        break 
        except Exception as e:
            print(f"[Error] ฮานอยพิเศษ: {e}")
        time.sleep(10)

# ==========================================
# 🎰 2.2 ดึงผล: ฮานอยปกติ (Minh Ngoc - Web Scraping)
# ==========================================
def fetch_hanoi_normal():
    today_str = datetime.now(tz).strftime("%d-%m-%Y")
    url = "https://www.minhngoc.net.vn/xo-so-truc-tiep/mien-bac.html"
    headers = {'User-Agent': 'Mozilla/5.0'}

    bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอยปกติ** งวดวันที่ {today_str} ครับ...")

    while True:
        try:
            res = requests.get(url, headers=headers)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # ค้นหาบล็อกข้อมูลของวันนี้ (ป้องกันการดึงข้อมูลของเมื่อวาน)
            date_check = soup.find('td', class_='ngay')
            
            # ถ้าระบบเจอวันที่ตรงกับวันนี้ แปลว่าเว็บเริ่มอัปเดตแล้ว
            if date_check and today_str.replace("-", "/") in date_check.text:
                # ดึงรางวัลพิเศษ (Giải ĐB) และ รางวัลที่ 1 (Giải Nhất)
                prize_special = soup.find(class_='giaidb')
                prize_1 = soup.find(class_='giai1')

                # รอจนกว่าตัวเลขจะออกครบ (ไม่มีเครื่องหมายรอผล)
                if prize_special and prize_1 and len(prize_special.text.strip()) >= 5:
                    top_3 = prize_special.text.strip()[-3:]
                    bottom_2 = prize_1.text.strip()[-2:]
                    
                    msg = (f"🇻🇳 **ผลหวยฮานอยปกติ** 🇻🇳\n📅 วันที่: {today_str}\n\n"
                           f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                    bot.send_message(GROUP_CHAT_ID, msg)
                    break
        except Exception as e:
            print(f"[Error] ฮานอยปกติ: {e}")
        time.sleep(10)

# ==========================================
# 💬 3. ระบบตอบกลับคำสั่ง Telegram
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "สวัสดีครับ! 🤖 บอทแจ้งผลหวยพร้อมทำงานแล้ว\n\n📌 **ตารางแจ้งผล:**\n- 17:30 น. : ฮานอยพิเศษ\n- 18:30 น. : ฮานอยปกติ")

# ==========================================
# ⏰ 4. ระบบเช็คเวลา
# ==========================================
def time_checker():
    has_run_special = False
    has_run_normal = False
    last_check_date = ""

    while True:
        now = datetime.now(tz)
        current_date = now.strftime("%d-%m-%Y")

        if current_date != last_check_date:
            has_run_special = False
            has_run_normal = False
            last_check_date = current_date

        # รันฮานอยพิเศษ ตอน 17:30
        if now.hour == 17 and now.minute == 30 and not has_run_special:
            has_run_special = True
            threading.Thread(target=fetch_hanoi_special, daemon=True).start()

        # รันฮานอยปกติ ตอน 18:30 (หวยปกติน่าจะออกครบหมดช่วงเวลานี้พอดี)
        if now.hour == 18 and now.minute == 30 and not has_run_normal:
            has_run_normal = True
            threading.Thread(target=fetch_hanoi_normal, daemon=True).start()

        time.sleep(30)

# ==========================================
# 🚀 5. เริ่มการทำงานทั้งหมด
# ==========================================
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    threading.Thread(target=time_checker, daemon=True).start()
    print("Bot is up and running with 2 lotteries...")
    bot.infinity_polling()

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
# 🎰 2.2 ดึงผล: ฮานอยปกติ (Minh Ngoc - Web Scraping + กดกฎให้แน่นขึ้น)
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
            
            date_check = soup.find('td', class_='ngay')
            
            if date_check and today_str.replace("-", "/") in date_check.text:
                prize_special = soup.find(class_='giaidb')
                prize_1 = soup.find(class_='giai1')

                if prize_special and prize_1:
                    # ทำความสะอาดข้อความ ลบช่องว่างทิ้งให้หมด
                    text_db = prize_special.text.replace(" ", "").strip()
                    text_1 = prize_1.text.replace(" ", "").strip()
                    
                    # 🔥 กฎเหล็ก: ต้องเป็น "ตัวเลขล้วน" และ "ยาว 5 ตัวเป๊ะ" เท่านั้น ถึงจะแปลว่าหมุนเสร็จแล้ว
                    is_db_ready = len(text_db) == 5 and text_db.isdigit()
                    is_1_ready = len(text_1) == 5 and text_1.isdigit()

                    if is_db_ready and is_1_ready:
                        top_3 = text_db[-3:]
                        bottom_2 = text_1[-2:]
                        
                        msg = (f"🇻🇳 **ผลหวยฮานอยปกติ** 🇻🇳\n📅 วันที่: {today_str}\n\n"
                               f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        break
        except Exception as e:
            print(f"[Error] ฮานอยปกติ: {e}")
        time.sleep(15)

# ==========================================
# 💬 3. ระบบตอบกลับคำสั่ง Telegram (เพิ่มปุ่มเทส)
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "สวัสดีครับ! 🤖 บอทแจ้งผลหวยพร้อมทำงานแล้ว\n\n📌 **คำสั่งสำหรับใช้งาน:**\n/start - ดูข้อความนี้\n/test_special - ทดสอบดึงผลฮานอยพิเศษ (เดี๋ยวนี้)\n/test_normal - ทดสอบดึงผลฮานอยปกติ (เดี๋ยวนี้)")

@bot.message_handler(commands=['test_special'])
def test_special(message):
    bot.reply_to(message, "🛠️ แอดมินสั่งทดสอบดึงผล **ฮานอยพิเศษ** แบบทันที...")
    threading.Thread(target=fetch_hanoi_special, daemon=True).start()

@bot.message_handler(commands=['test_normal'])
def test_normal(message):
    bot.reply_to(message, "🛠️ แอดมินสั่งทดสอบดึงผล **ฮานอยปกติ** แบบทันที...")
    threading.Thread(target=fetch_hanoi_normal, daemon=True).start()

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

        if now.hour == 17 and now.minute == 30 and not has_run_special:
            has_run_special = True
            threading.Thread(target=fetch_hanoi_special, daemon=True).start()

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
    print("Bot is up and running...")
    bot.infinity_polling()

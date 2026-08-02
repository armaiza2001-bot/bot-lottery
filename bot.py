import telebot
import requests
import time
import threading
from datetime import datetime, timedelta
import pytz
import os
from flask import Flask
from bs4 import BeautifulSoup

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
    return "Lotto Bot is running with 9 Lotteries!"

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 🎰 2.1 ดึงผล: ฮานอยพิเศษ (17:30)
# ==========================================
def fetch_hanoi_special():
    today_str = datetime.now(tz).strftime("%d-%m-%Y")
    url = "https://www.xsthm.com/result"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอยพิเศษ** งวดวันที่ {today_str} ครับ...")

    while True:
        try:
            res = requests.get(url, headers=headers, timeout=15)
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
# 🎰 2.2 ดึงผล: ฮานอยสามัคคี (17:30)
# ==========================================
def fetch_hanoi_samakkhi():
    today_str_api = datetime.now(tz).strftime("%Y-%m-%d") 
    today_str_display = datetime.now(tz).strftime("%d-%m-%Y")
    url = "https://api.xosounion.com/api/result"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }

    bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอยสามัคคี** งวดวันที่ {today_str_display} ครับ...")

    while True:
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                
                if json_data.get("status") == "success":
                    data_node = json_data.get("data", {})
                    api_date = str(data_node.get("lotto_date", "")).strip()
                    
                    if api_date == today_str_api:
                        results_node = data_node.get("results", {})
                        prize_special = str(results_node.get("prize_1st") or "").strip()
                        prize_1 = str(results_node.get("prize_2nd") or "").strip()
                        
                        if len(prize_special) == 5 and prize_special.isdigit() and len(prize_1) == 5 and prize_1.isdigit():
                            top_3 = prize_special[-3:] 
                            bottom_2 = prize_1[-2:]    
                            
                            msg = (f"🇻🇳 **ผลหวยฮานอยสามัคคี** 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            break 
        except Exception as e:
            print(f"[Error] ฮานอยสามัคคี: {e}")
        time.sleep(10)

# ==========================================
# 🎰 2.3 ดึงผล: ฮานอยปกติ (18:30)
# ==========================================
def fetch_hanoi_normal():
    today_str = datetime.now(tz).strftime("%d-%m-%Y")
    url = "https://www.minhngoc.net.vn/xo-so-truc-tiep/mien-bac.html"
    headers = {'User-Agent': 'Mozilla/5.0'}

    bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอยปกติ** งวดวันที่ {today_str} ครับ...")

    while True:
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            date_check = soup.find('td', class_='ngay')
            
            if date_check and today_str.replace("-", "/") in date_check.text:
                prize_special = soup.find(class_='giaidb')
                prize_1 = soup.find(class_='giai1')

                if prize_special and prize_1:
                    text_db = prize_special.text.replace(" ", "").strip()
                    text_1 = prize_1.text.replace(" ", "").strip()
                    
                    if len(text_db) == 5 and text_db.isdigit() and len(text_1) == 5 and text_1.isdigit():
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
# 🎰 2.4 ดึงผล: ฮานอย VIP (19:30)
# ==========================================
def fetch_hanoi_vip():
    today_str = datetime.now(tz).strftime("%d-%m-%Y")
    url = "https://www.mlnhngoc.net/mlnhngoc"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอย VIP** งวดวันที่ {today_str} ครับ...")

    while True:
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                data = res.json()
                api_date = str(data.get("label", "")).strip()
                
                if api_date == today_str:
                    item_data = data.get("item", {}) 
                    prize_special = str(item_data.get("ran26") or "").strip()
                    prize_1 = str(item_data.get("ran0") or "").strip()
                    
                    if len(prize_special) == 5 and prize_special.isdigit() and len(prize_1) == 5 and prize_1.isdigit():
                        top_3 = prize_special[-3:] 
                        bottom_2 = prize_1[-2:]    
                        
                        msg = (f"🇻🇳 **ผลหวยฮานอย VIP** 🇻🇳\n📅 วันที่: {api_date}\n\n"
                               f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        break 
        except Exception as e:
            print(f"[Error] ฮานอย VIP: {e}")
        time.sleep(10)

# ==========================================
# 🎰 2.5 ดึงผล: ฮานอยพัฒนา (19:30)
# ==========================================
def fetch_hanoi_develop():
    today_str_api = datetime.now(tz).strftime("%Y-%m-%d") 
    today_str_display = datetime.now(tz).strftime("%d-%m-%Y")
    url = "https://api.xosodevelop.com/api/result"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }

    bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอยพัฒนา** งวดวันที่ {today_str_display} ครับ...")

    while True:
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                
                if json_data.get("status") == "success":
                    data_node = json_data.get("data", {})
                    api_date = str(data_node.get("lotto_date", "")).strip()
                    
                    if api_date == today_str_api:
                        results_node = data_node.get("results", {})
                        prize_special = str(results_node.get("prize_1st") or "").strip()
                        prize_1 = str(results_node.get("prize_2nd") or "").strip()
                        
                        if len(prize_special) == 5 and prize_special.isdigit() and len(prize_1) == 5 and prize_1.isdigit():
                            top_3 = prize_special[-3:] 
                            bottom_2 = prize_1[-2:]    
                            
                            msg = (f"🇻🇳 **ผลหวยฮานอยพัฒนา** 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            break 
        except Exception as e:
            print(f"[Error] ฮานอยพัฒนา: {e}")
        time.sleep(10)

# ==========================================
# 🎰 2.6 ดึงผล: ลาวสามัคคี (20:30)
# ==========================================
def fetch_lao_samakkhi():
    today_str_api = datetime.now(tz).strftime("%Y-%m-%d") 
    today_str_display = datetime.now(tz).strftime("%d-%m-%Y")
    url = "https://public-api.laounion.com/result"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }

    bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยลาวสามัคคี** งวดวันที่ {today_str_display} ครับ...")

    while True:
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                
                if json_data.get("status") == "success":
                    data_node = json_data.get("data", {})
                    api_date = str(data_node.get("lotto_date", "")).strip()
                    
                    if api_date == today_str_api:
                        results_node = data_node.get("results", {})
                        digit4 = str(results_node.get("digit4") or "").strip()
                        
                        if len(digit4) == 4 and digit4.isdigit():
                            top_3 = digit4[-3:]  
                            bottom_2 = digit4[:2]  
                            
                            msg = (f"🇱🇦 **ผลหวยลาวสามัคคี** 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            break 
        except Exception as e:
            print(f"[Error] ลาวสามัคคี: {e}")
        time.sleep(10)

# ==========================================
# 🎰 2.7 ดึงผล: ลาวอาเซียน (21:00)
# ==========================================
def fetch_lao_asean():
    today_str_api = datetime.now(tz).strftime("%Y-%m-%d") 
    today_str_display = datetime.now(tz).strftime("%d-%m-%Y")
    url = "https://hi.lotterylaosasean.com/result"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }

    bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยลาวอาเซียน** งวดวันที่ {today_str_display} ครับ...")

    while True:
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                data_node = json_data.get("data", {})
                api_date = str(data_node.get("lotto_date", "")).strip()
                
                if api_date == today_str_api:
                    results_node = data_node.get("results", {})
                    digit5 = str(results_node.get("digit5") or "").strip()
                    
                    if len(digit5) == 5 and digit5.isdigit():
                        top_3 = digit5[-3:]  
                        bottom_2 = digit5[:2]  
                        
                        msg = (f"🇱🇦 **ผลหวยลาวอาเซียน** 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        break 
        except Exception as e:
            print(f"[Error] ลาวอาเซียน: {e}")
        time.sleep(10)

# ==========================================
# 🎰 2.8 ดึงผล: ลาว VIP (21:30)
# ==========================================
def fetch_lao_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    today_str_api = target_date.strftime("%d/%m/%Y") 
    url = "https://laosviplot.com/result"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json, text/plain, */*'
    }

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยลาว VIP** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code in [200, 304]: 
                data = res.json()
                api_date = str(data.get("date", "")).strip()
                
                if api_date == today_str_api:
                    l1 = str(data.get("lotto_1", "")).strip()
                    l2 = str(data.get("lotto_2", "")).strip()
                    l3 = str(data.get("lotto_3", "")).strip()
                    l4 = str(data.get("lotto_4", "")).strip()
                    
                    if l1 and l2 and l3 and l4:
                        digit4 = l1 + l2 + l3 + l4
                        top_3 = digit4[-3:]  
                        bottom_2 = digit4[:2] 
                        
                        msg = (f"🇱🇦 **ผลหวยลาว VIP** 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return 
        except Exception as e:
            print(f"[Error] ลาว VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ลาว VIP**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.9 ดึงผล: ลาวสามัคคี VIP (21:30) [เพิ่มใหม่!]
# ==========================================
def fetch_lao_samakkhi_vip():
    today_str_api = datetime.now(tz).strftime("%Y-%m-%d") 
    today_str_display = datetime.now(tz).strftime("%d-%m-%Y")
    
    # URL จากรูปหน้า Network
    url = "https://api.laounionvip.com/result"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }

    bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยลาวสามัคคี VIP** งวดวันที่ {today_str_display} ครับ...")

    while True:
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                
                # โครงสร้าง API ตัวนี้ไม่มี data หุ้ม
                api_date = str(json_data.get("lotto_date", "")).strip()
                
                if api_date == today_str_api:
                    results_node = json_data.get("results", {})
                    digit4 = str(results_node.get("digit4") or "").strip()
                    
                    if len(digit4) == 4 and digit4.isdigit():
                        top_3 = digit4[-3:]    # 3 ตัวท้าย
                        bottom_2 = digit4[:2]  # 2 ตัวหน้า
                        
                        msg = (f"🇱🇦 **ผลหวยลาวสามัคคี VIP** 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        break 
        except Exception as e:
            print(f"[Error] ลาวสามัคคี VIP: {e}")
        time.sleep(10)

# ==========================================
# 💬 3. ระบบตอบกลับคำสั่ง Telegram
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "สวัสดีครับ! 🤖 บอทแจ้งผลหวย 9 รอบ พร้อมทำงานแล้ว\n\n📌 **ตารางแจ้งผลอัตโนมัติ:**\n- 17:30 น. : ฮานอยพิเศษ & ฮานอยสามัคคี\n- 18:30 น. : ฮานอยปกติ\n- 19:30 น. : ฮานอย VIP & ฮานอยพัฒนา\n- 20:30 น. : ลาวสามัคคี\n- 21:00 น. : ลาวอาเซียน\n- 21:30 น. : ลาว VIP & ลาวสามัคคี VIP\n\n**คำสั่งทดสอบ:**\n/test_special\n/test_samakkhi\n/test_normal\n/test_vip\n/test_develop\n/test_lao_samakkhi\n/test_lao_asean\n/test_lao_vip\n/test_lao_samakkhi_vip")

@bot.message_handler(commands=['test_special'])
def test_special(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **ฮานอยพิเศษ**...")
    threading.Thread(target=fetch_hanoi_special, daemon=True).start()

@bot.message_handler(commands=['test_samakkhi'])
def test_samakkhi(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **ฮานอยสามัคคี**...")
    threading.Thread(target=fetch_hanoi_samakkhi, daemon=True).start()

@bot.message_handler(commands=['test_normal'])
def test_normal(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **ฮานอยปกติ**...")
    threading.Thread(target=fetch_hanoi_normal, daemon=True).start()

@bot.message_handler(commands=['test_vip'])
def test_vip(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **ฮานอย VIP**...")
    threading.Thread(target=fetch_hanoi_vip, daemon=True).start()

@bot.message_handler(commands=['test_develop'])
def test_develop(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **ฮานอยพัฒนา**...")
    threading.Thread(target=fetch_hanoi_develop, daemon=True).start()

@bot.message_handler(commands=['test_lao_samakkhi'])
def test_lao_samakkhi(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **ลาวสามัคคี**...")
    threading.Thread(target=fetch_lao_samakkhi, daemon=True).start()

@bot.message_handler(commands=['test_lao_asean'])
def test_lao_asean(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **ลาวอาเซียน**...")
    threading.Thread(target=fetch_lao_asean, daemon=True).start()

@bot.message_handler(commands=['test_lao_vip'])
def test_lao_vip_cmd(message):
    try:
        offset = int(message.text.split()[1]) if len(message.text.split()) > 1 else 0
    except ValueError:
        offset = 0
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ลาว VIP** (ย้อนหลัง {offset} วัน)...")
    threading.Thread(target=fetch_lao_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_lao_samakkhi_vip'])
def test_lao_samakkhi_vip(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **ลาวสามัคคี VIP**...")
    threading.Thread(target=fetch_lao_samakkhi_vip, daemon=True).start()

# ==========================================
# ⏰ 4. ระบบเช็คเวลา 
# ==========================================
def time_checker():
    has_run_special = False
    has_run_samakkhi = False
    has_run_normal = False
    has_run_vip = False
    has_run_develop = False
    has_run_lao_samakkhi = False
    has_run_lao_asean = False
    has_run_lao_vip = False
    has_run_lao_samakkhi_vip = False
    last_check_date = ""

    while True:
        now = datetime.now(tz)
        current_date = now.strftime("%d-%m-%Y")

        if current_date != last_check_date:
            has_run_special = False
            has_run_samakkhi = False
            has_run_normal = False
            has_run_vip = False
            has_run_develop = False
            has_run_lao_samakkhi = False
            has_run_lao_asean = False
            has_run_lao_vip = False
            has_run_lao_samakkhi_vip = False
            last_check_date = current_date

        # รอบ 17:30
        if now.hour == 17 and now.minute == 30:
            if not has_run_special:
                has_run_special = True
                threading.Thread(target=fetch_hanoi_special, daemon=True).start()
            if not has_run_samakkhi:
                has_run_samakkhi = True
                threading.Thread(target=fetch_hanoi_samakkhi, daemon=True).start()

        # รอบ 18:30
        if now.hour == 18 and now.minute == 30 and not has_run_normal:
            has_run_normal = True
            threading.Thread(target=fetch_hanoi_normal, daemon=True).start()
            
        # รอบ 19:30
        if now.hour == 19 and now.minute == 30:
            if not has_run_vip:
                has_run_vip = True
                threading.Thread(target=fetch_hanoi_vip, daemon=True).start()
            if not has_run_develop:
                has_run_develop = True
                threading.Thread(target=fetch_hanoi_develop, daemon=True).start()
                
        # รอบ 20:30
        if now.hour == 20 and now.minute == 30 and not has_run_lao_samakkhi:
            has_run_lao_samakkhi = True
            threading.Thread(target=fetch_lao_samakkhi, daemon=True).start()
            
        # รอบ 21:00
        if now.hour == 21 and now.minute == 00 and not has_run_lao_asean:
            has_run_lao_asean = True
            threading.Thread(target=fetch_lao_asean, daemon=True).start()

        # รอบ 21:30 (เพิ่มลาวสามัคคี VIP ให้ทำงานพร้อมลาว VIP)
        if now.hour == 21 and now.minute == 30:
            if not has_run_lao_vip:
                has_run_lao_vip = True
                threading.Thread(target=fetch_lao_vip, daemon=True).start()
            if not has_run_lao_samakkhi_vip:
                has_run_lao_samakkhi_vip = True
                threading.Thread(target=fetch_lao_samakkhi_vip, daemon=True).start()

        time.sleep(30)

# ==========================================
# 🚀 5. เริ่มการทำงานทั้งหมด
# ==========================================
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    threading.Thread(target=time_checker, daemon=True).start()
    print("Bot is up and running with 9 lotteries (Timeout protected)...")
    bot.infinity_polling()

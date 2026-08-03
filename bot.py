import telebot
import requests
import time
import threading
from datetime import datetime, timedelta
import pytz
import os
import re
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
def fetch_hanoi_special(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str = target_date.strftime("%d-%m-%Y")
    url = "https://www.xsthm.com/result"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอยพิเศษ** งวดวันที่ {today_str} ครับ...")

    attempts = 0
    while True:
        attempts += 1
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
                        return 
        except Exception as e:
            print(f"[Error] ฮานอยพิเศษ: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ฮานอยพิเศษ**: ไม่พบข้อมูลวันที่ {today_str}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.2 ดึงผล: ฮานอยสามัคคี (17:30)
# ==========================================
def fetch_hanoi_samakkhi(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    url = "https://api.xosounion.com/api/result"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอยสามัคคี** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
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
                        if len(prize_special) == 5 and len(prize_1) == 5:
                            top_3 = prize_special[-3:] 
                            bottom_2 = prize_1[-2:]    
                            msg = (f"🇻🇳 **ผลหวยฮานอยสามัคคี** 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
        except Exception as e:
            print(f"[Error] ฮานอยสามัคคี: {e}")
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ฮานอยสามัคคี**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.3 ดึงผล: ฮานอยปกติ (18:30) [เวอร์ชัน ไฮบริด สุดยอดความเสถียร]
# ==========================================
def fetch_hanoi_normal(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    today_str_html = target_date.strftime("%d/%m/%Y") # เว็บมักใช้ / แทน -
    
    main_url = "https://www.minhngoc.net.vn/xo-so-truc-tiep/mien-bac.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*'
    }

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอยปกติ** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            # โหลดหน้าหลักก่อนเสมอ
            res_main = requests.get(f"{main_url}?v={int(time.time())}", headers=headers, timeout=15)
            res_main.encoding = 'utf-8'
            soup = BeautifulSoup(res_main.text, 'html.parser')
            
            # 🎯 แผน A: หาจากตาราง HTML ปกติ (ใช้ได้ทั้งย้อนหลัง และตอนที่หวยออกเสร็จแล้ว)
            tables = soup.find_all('table', class_='bkqmiennam')
            for tbl in tables:
                date_td = tbl.find('td', class_='ngay')
                if date_td and today_str_html in date_td.text:
                    prize_special = tbl.find(class_='giaidb')
                    prize_1 = tbl.find(class_='giai1')
                    
                    if prize_special and prize_1:
                        text_db = prize_special.text.replace(" ", "").strip()
                        text_1 = prize_1.text.replace(" ", "").strip()
                        
                        # ถ้าเลขครบ 5 ตัว แปลว่าออกเสร็จแล้ว ดึงมาใช้ได้เลย!
                        if len(text_db) == 5 and len(text_1) == 5 and text_db.isdigit() and text_1.isdigit():
                            msg = (f"🇻🇳 **ผลหวยฮานอยปกติ** 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {text_db[-3:]}\n👇 **2 ตัวล่าง:** {text_1[-2:]}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return
            
            # 🚀 แผน B: ถ้าแผน A ยังไม่ได้เลขครบ และเป็นการดึงผลของ "วันนี้" (กำลังไลฟ์สด) ให้ใช้ Live API
            if offset_days == 0:
                match_url = re.search(r'src="(https://server-live[^"]+js_m2\.js[^"]+)"', res_main.text)
                if match_url:
                    live_api_url = match_url.group(1)
                    res_api = requests.get(live_api_url, headers=headers, timeout=15)
                    
                    match_0 = re.search(r'0:\s*"(\d{5})"', res_api.text)
                    match_1 = re.search(r'1:\s*"(\d{5})"', res_api.text)
                    
                    if match_0 and match_1:
                        text_db = match_0.group(1)
                        text_1 = match_1.group(1)
                        
                        if len(text_db) == 5 and len(text_1) == 5:
                            msg = (f"🇻🇳 **ผลหวยฮานอยปกติ** 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {text_db[-3:]}\n👇 **2 ตัวล่าง:** {text_1[-2:]}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 

        except Exception as e:
            print(f"[Error] ฮานอยปกติ: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ฮานอยปกติ**: ไม่พบข้อมูลวันที่ {today_str_display} (หรือผลยังไม่ออก)")
            return
        time.sleep(10)
        
# ==========================================
# 🎰 2.4 ดึงผล: ฮานอย VIP (19:30)
# ==========================================
def fetch_hanoi_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str = target_date.strftime("%d-%m-%Y")
    url = "https://www.mlnhngoc.net/mlnhngoc"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอย VIP** งวดวันที่ {today_str} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                data = res.json()
                api_date = str(data.get("label", "")).strip()
                if api_date == today_str:
                    item_data = data.get("item", {}) 
                    prize_special = str(item_data.get("ran26") or "").strip()
                    prize_1 = str(item_data.get("ran0") or "").strip()
                    if len(prize_special) == 5 and len(prize_1) == 5:
                        top_3 = prize_special[-3:] 
                        bottom_2 = prize_1[-2:]    
                        msg = (f"🇻🇳 **ผลหวยฮานอย VIP** 🇻🇳\n📅 วันที่: {api_date}\n\n"
                               f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return 
        except Exception as e:
            print(f"[Error] ฮานอย VIP: {e}")
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ฮานอย VIP**: ไม่พบข้อมูลวันที่ {today_str}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.5 ดึงผล: ฮานอยพัฒนา (19:30)
# ==========================================
def fetch_hanoi_develop(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    url = "https://api.xosodevelop.com/api/result"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอยพัฒนา** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
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
                        if len(prize_special) == 5 and len(prize_1) == 5:
                            top_3 = prize_special[-3:] 
                            bottom_2 = prize_1[-2:]    
                            msg = (f"🇻🇳 **ผลหวยฮานอยพัฒนา** 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
        except Exception as e:
            print(f"[Error] ฮานอยพัฒนา: {e}")
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ฮานอยพัฒนา**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.6 ดึงผล: ลาวสามัคคี (20:30)
# ==========================================
def fetch_lao_samakkhi(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    url = "https://public-api.laounion.com/result"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยลาวสามัคคี** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
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
                        if len(digit4) == 4:
                            top_3 = digit4[-3:]  
                            bottom_2 = digit4[:2]  
                            msg = (f"🇱🇦 **ผลหวยลาวสามัคคี** 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
        except Exception as e:
            print(f"[Error] ลาวสามัคคี: {e}")
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ลาวสามัคคี**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.7 ดึงผล: ลาวอาเซียน (21:00)
# ==========================================
def fetch_lao_asean(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    url = "https://hi.lotterylaosasean.com/result"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยลาวอาเซียน** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                data_node = json_data.get("data", {})
                api_date = str(data_node.get("lotto_date", "")).strip()
                if api_date == today_str_api:
                    results_node = data_node.get("results", {})
                    digit5 = str(results_node.get("digit5") or "").strip()
                    if len(digit5) == 5:
                        top_3 = digit5[-3:]  
                        bottom_2 = digit5[:2]  
                        msg = (f"🇱🇦 **ผลหวยลาวอาเซียน** 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return 
        except Exception as e:
            print(f"[Error] ลาวอาเซียน: {e}")
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ลาวอาเซียน**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.8 ดึงผล: ลาว VIP (21:30)
# ==========================================
def fetch_lao_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    today_str_api = target_date.strftime("%d/%m/%Y") 
    url = "https://laosviplot.com/result"
    
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

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
# 🎰 2.9 ดึงผล: ลาวสามัคคี VIP (21:30) [แก้บั๊ก JSON โครงสร้างซ้อนทับ]
# ==========================================
def fetch_lao_samakkhi_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    url = "https://api.laounionvip.com/result"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยลาวสามัคคี VIP** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                
                # 💡 เช็คว่าสถานะ success ไหม
                if json_data.get("status") == "success":
                    # 💡 มุดเข้าไปในกล่อง "data" ก่อน! (ตรงนี้แหละที่พลาดไป)
                    data_node = json_data.get("data", {})
                    
                    # แล้วค่อยดึงวันที่ออกมาเช็ค
                    api_date = str(data_node.get("lotto_date", "")).strip()
                    
                    if api_date == today_str_api:
                        results_node = data_node.get("results", {})
                        digit4 = str(results_node.get("digit4") or "").strip()
                        
                        if len(digit4) == 4 and digit4.isdigit():
                            top_3 = digit4[-3:]    
                            bottom_2 = digit4[:2]  
                            
                            msg = (f"🇱🇦 **ผลหวยลาวสามัคคี VIP** 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
        except Exception as e:
            print(f"[Error] ลาวสามัคคี VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ลาวสามัคคี VIP**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.10 ดึงผล: ลาวสตาร์ VIP (22:00)
# ==========================================
def fetch_lao_star_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    url = "https://api.laostars-vip.com/result"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยลาวสตาร์ VIP** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                
                if json_data.get("status") == "success":
                    data_node = json_data.get("data", {})
                    api_date = str(data_node.get("lotto_date", "")).strip()
                    
                    if api_date == today_str_api:
                        results_node = data_node.get("results", {})
                        digit5 = str(results_node.get("digit5") or "").strip()
                        
                        # ตัด 2 ตัวหน้า เป็นล่าง / 3 ตัวหลัง เป็นบน
                        if len(digit5) == 5 and digit5.isdigit():
                            top_3 = digit5[-3:]    
                            bottom_2 = digit5[:2]  
                            
                            msg = (f"🇱🇦 **ผลหวยลาวสตาร์ VIP** 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
        except Exception as e:
            print(f"[Error] ลาวสตาร์ VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ลาวสตาร์ VIP**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.11 ดึงผล: อังกฤษ VIP (21:50) [อัปเดตลิงก์ใหม่!]
# ==========================================
def fetch_england_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    # 💡 ใช้ลิงก์ลับที่คุณหามาได้! (แนบวันที่ไปด้วยเผื่อย้อนหลัง)
    url = f"https://gcp.lottosuperrich.com/result?date={today_str_api}"
    
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยอังกฤษ VIP** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                if json_data.get("status") == "success":
                    data_gb = json_data.get("data", {}).get("gb", {})
                    api_date = str(data_gb.get("lotto_date", "")).strip()
                    
                    if api_date == today_str_api:
                        results = data_gb.get("results", {})
                        p1, p2 = str(results.get("prize_1st", "")), str(results.get("prize_2nd", ""))
                        
                        if len(p1) >= 3 and len(p2) >= 2:
                            msg = (f"🇬🇧 **ผลหวยอังกฤษ VIP** 🇬🇧\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {p1[-3:]}\n👇 **2 ตัวล่าง:** {p2[-2:]}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
                    elif not is_auto and attempts == 1 and api_date != "":
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ **อังกฤษ VIP**: ข้อมูลใน API ตอนนี้เป็นของวันที่ {api_date}")
                        return
        except Exception as e:
            print(f"[Error] อังกฤษ VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **อังกฤษ VIP**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.12 ดึงผล: เยอรมัน VIP (22:50) [อัปเดตลิงก์ใหม่!]
# ==========================================
def fetch_germany_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    url = f"https://gcp.lottosuperrich.com/result?date={today_str_api}"
    
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยเยอรมัน VIP** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                if json_data.get("status") == "success":
                    data_de = json_data.get("data", {}).get("de", {})
                    api_date = str(data_de.get("lotto_date", "")).strip()
                    
                    if api_date == today_str_api:
                        results = data_de.get("results", {})
                        p1, p2 = str(results.get("prize_1st", "")), str(results.get("prize_2nd", ""))
                        
                        if len(p1) >= 3 and len(p2) >= 2:
                            msg = (f"🇩🇪 **ผลหวยเยอรมัน VIP** 🇩🇪\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {p1[-3:]}\n👇 **2 ตัวล่าง:** {p2[-2:]}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
                    elif not is_auto and attempts == 1 and api_date != "":
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ **เยอรมัน VIP**: ข้อมูลใน API ตอนนี้เป็นของวันที่ {api_date}")
                        return
        except Exception as e:
            print(f"[Error] เยอรมัน VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **เยอรมัน VIP**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.13 ดึงผล: รัสเซีย VIP (23:50) [อัปเดตลิงก์ใหม่!]
# ==========================================
def fetch_russia_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    url = f"https://gcp.lottosuperrich.com/result?date={today_str_api}"
    
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยรัสเซีย VIP** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                if json_data.get("status") == "success":
                    data_ru = json_data.get("data", {}).get("ru", {})
                    api_date = str(data_ru.get("lotto_date", "")).strip()
                    
                    if api_date == today_str_api:
                        results = data_ru.get("results", {})
                        p1, p2 = str(results.get("prize_1st", "")), str(results.get("prize_2nd", ""))
                        
                        if len(p1) >= 3 and len(p2) >= 2:
                            msg = (f"🇷🇺 **ผลหวยรัสเซีย VIP** 🇷🇺\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {p1[-3:]}\n👇 **2 ตัวล่าง:** {p2[-2:]}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
                    elif not is_auto and attempts == 1 and api_date != "":
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ **รัสเซีย VIP**: ข้อมูลใน API ตอนนี้เป็นของวันที่ {api_date}")
                        return
        except Exception as e:
            print(f"[Error] รัสเซีย VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **รัสเซีย VIP**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.14 ดึงผล: ฮานอย EXTRA (22:30)
# ==========================================
def fetch_hanoi_extra(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    # 💡 ใส่ ?date= เผื่อเว็บรองรับการดึงผลย้อนหลัง
    url = f"https://api.xosoextra.com/result?date={today_str_api}"
    
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยฮานอย EXTRA** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                if json_data.get("status") == "success":
                    data_node = json_data.get("data", {})
                    api_date = str(data_node.get("lotto_date", "")).strip()
                    
                    if api_date == today_str_api:
                        results = data_node.get("results", {})
                        
                        # ดึงข้อมูลและตัดตัวเลข
                        prize_1st = str(results.get("prize_1st", ""))
                        prize_2digits = str(results.get("prize_2digits_1", ""))
                        
                        if len(prize_1st) >= 3 and len(prize_2digits) >= 2:
                            top_3 = prize_1st[-3:]
                            bottom_2 = prize_2digits[-2:]
                            
                            msg = (f"🇻🇳 **ผลหวยฮานอย EXTRA** 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
                    elif not is_auto and attempts == 1 and api_date != "":
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ **ฮานอย EXTRA**: ข้อมูลใน API ตอนนี้เป็นของวันที่ {api_date}")
                        return
        except Exception as e:
            print(f"[Error] ฮานอย EXTRA: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ฮานอย EXTRA**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🎰 2.15 ดึงผล: ลาวกาชาด (23:30)
# ==========================================
def fetch_lao_redcross(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    # 💡 ใส่ ?date= เผื่อไว้รองรับการดึงผลย้อนหลัง
    url = f"https://api.lao-redcross.com/result?date={today_str_api}"
    
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยลาวกาชาด** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                
                # รองรับกรณีที่เว็บส่งข้อมูลมาตรงๆ (ไม่มี status/data ครอบ)
                data_node = json_data.get("data") if "data" in json_data else json_data
                api_date = str(data_node.get("lotto_date", "")).strip()
                
                if api_date == today_str_api:
                    results = data_node.get("results", {})
                    digit5 = str(results.get("digit5", "")).strip()
                    
                    if len(digit5) == 5 and digit5.isdigit():
                        top_3 = digit5[-3:]
                        bottom_2 = digit5[:2]
                        
                        msg = (f"🇱🇦 **ผลหวยลาวกาชาด** 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return 
                elif not is_auto and attempts == 1 and api_date != "":
                    bot.send_message(GROUP_CHAT_ID, f"⚠️ **ลาวกาชาด**: ข้อมูลใน API ตอนนี้เป็นของวันที่ {api_date}")
                    return
        except Exception as e:
            print(f"[Error] ลาวกาชาด: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ลาวกาชาด**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)
        
# ==========================================
# 💬 3. ระบบตอบกลับคำสั่ง Telegram
# ==========================================

# ฟังก์ชันช่วยอ่านตัวเลขย้อนหลัง
def get_offset(message):
    try:
        parts = message.text.split()
        if len(parts) > 1 and parts[1].isdigit():
            return int(parts[1])
    except Exception:
        pass
    return 0

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "📌 **ตารางแจ้งผลอัตโนมัติ:**\n"
        "- 17:30 น. : ฮานอยพิเศษ & ฮานอยสามัคคี\n"
        "- 18:30 น. : ฮานอยปกติ\n"
        "- 19:30 น. : ฮานอย VIP & ฮานอยพัฒนา\n"
        "- 20:30 น. : ลาวสามัคคี\n"
        "- 21:00 น. : ลาวอาเซียน\n"
        "- 21:30 น. : ลาว VIP & ลาวสามัคคี VIP\n"
        "- 21:50 น. : อังกฤษ VIP\n"
        "- 22:00 น. : ลาวสตาร์ VIP\n"
        "- 22:30 น. : ฮานอย EXTRA\n"
        "- 22:50 น. : เยอรมัน VIP\n"
        "- 23:30 น. : ลาวกาชาด\n\n"
        "- 23:50 น. : รัสเซีย VIP\n\n"
        "**คำสั่งทดสอบ:**\n"
        "/test_special | /test_samakkhi | /test_normal | /test_vip | /test_develop\n"
        "/test_lao_samakkhi | /test_lao_asean | /test_lao_vip | /test_lao_samakkhi_vip\n"
        "/test_lao_star_vip | /test_england_vip | /test_hanoi_extra | /test_germany_vip | /test_lao_redcross | /test_russia_vip\n"
        "/yesterday (ดึงผลเมื่อวานทั้งหมด)"
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['yesterday'])
def test_all_yesterday(message):
    bot.reply_to(message, "🛠️ กำลังดึงผลย้อนหลัง 1 วัน สำหรับทุกหวย...")
    threading.Thread(target=fetch_hanoi_special, args=(1, False), daemon=True).start()
    threading.Thread(target=fetch_hanoi_samakkhi, args=(1, False), daemon=True).start()
    threading.Thread(target=fetch_hanoi_normal, args=(1, False), daemon=True).start()
    threading.Thread(target=fetch_hanoi_vip, args=(1, False), daemon=True).start()
    threading.Thread(target=fetch_hanoi_develop, args=(1, False), daemon=True).start()
    threading.Thread(target=fetch_lao_samakkhi, args=(1, False), daemon=True).start()
    threading.Thread(target=fetch_lao_asean, args=(1, False), daemon=True).start()
    threading.Thread(target=fetch_lao_vip, args=(1, False), daemon=True).start()
    threading.Thread(target=fetch_lao_samakkhi_vip, args=(1, False), daemon=True).start()
    threading.Thread(target=fetch_lao_star_vip, args=(1, False), daemon=True).start()
    threading.Thread(target=fetch_england_vip, args=(1, False), daemon=True).start()
    threading.Thread(target=fetch_germany_vip, args=(1, False), daemon=True).start()
    threading.Thread(target=fetch_russia_vip, args=(1, False), daemon=True).start()

@bot.message_handler(commands=['test_special'])
def test_special(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮานอยพิเศษ**{txt}...")
    threading.Thread(target=fetch_hanoi_special, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_samakkhi'])
def test_samakkhi(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮานอยสามัคคี**{txt}...")
    threading.Thread(target=fetch_hanoi_samakkhi, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_normal'])
def test_normal(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮานอยปกติ**{txt}...")
    threading.Thread(target=fetch_hanoi_normal, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_vip'])
def test_vip(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮานอย VIP**{txt}...")
    threading.Thread(target=fetch_hanoi_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_develop'])
def test_develop(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮานอยพัฒนา**{txt}...")
    threading.Thread(target=fetch_hanoi_develop, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_lao_samakkhi'])
def test_lao_samakkhi(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ลาวสามัคคี**{txt}...")
    threading.Thread(target=fetch_lao_samakkhi, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_lao_asean'])
def test_lao_asean(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ลาวอาเซียน**{txt}...")
    threading.Thread(target=fetch_lao_asean, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_lao_vip'])
def test_lao_vip_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ลาว VIP**{txt}...")
    threading.Thread(target=fetch_lao_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_lao_samakkhi_vip'])
def test_lao_samakkhi_vip_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ลาวสามัคคี VIP**{txt}...")
    threading.Thread(target=fetch_lao_samakkhi_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_lao_star_vip'])
def test_lao_star_vip_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ลาวสตาร์ VIP**{txt}...")
    threading.Thread(target=fetch_lao_star_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_england_vip'])
def test_england_vip_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **อังกฤษ VIP**{txt}...")
    threading.Thread(target=fetch_england_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_germany_vip'])
def test_germany_vip_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **เยอรมัน VIP**{txt}...")
    threading.Thread(target=fetch_germany_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_russia_vip'])
def test_russia_vip_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **รัสเซีย VIP**{txt}...")
    threading.Thread(target=fetch_russia_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_hanoi_extra'])
def test_hanoi_extra_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮานอย EXTRA**{txt}...")
    threading.Thread(target=fetch_hanoi_extra, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_lao_redcross'])
def test_lao_redcross_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ลาวกาชาด**{txt}...")
    threading.Thread(target=fetch_lao_redcross, args=(offset, False), daemon=True).start()
    
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
    has_run_lao_star_vip = False
    has_run_hanoi_extra = False
    has_run_lao_redcross = False
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
            has_run_england_vip = False
            has_run_germany_vip = False
            has_run_russia_vip = False
            last_check_date = current_date

        if now.hour == 17 and now.minute == 30:
            if not has_run_special:
                has_run_special = True
                threading.Thread(target=fetch_hanoi_special, daemon=True).start()
            if not has_run_samakkhi:
                has_run_samakkhi = True
                threading.Thread(target=fetch_hanoi_samakkhi, daemon=True).start()

        if now.hour == 18 and now.minute == 30 and not has_run_normal:
            has_run_normal = True
            threading.Thread(target=fetch_hanoi_normal, daemon=True).start()
            
        if now.hour == 19 and now.minute == 30:
            if not has_run_vip:
                has_run_vip = True
                threading.Thread(target=fetch_hanoi_vip, daemon=True).start()
            if not has_run_develop:
                has_run_develop = True
                threading.Thread(target=fetch_hanoi_develop, daemon=True).start()
                
        if now.hour == 20 and now.minute == 30 and not has_run_lao_samakkhi:
            has_run_lao_samakkhi = True
            threading.Thread(target=fetch_lao_samakkhi, daemon=True).start()
            
        if now.hour == 21 and now.minute == 00 and not has_run_lao_asean:
            has_run_lao_asean = True
            threading.Thread(target=fetch_lao_asean, daemon=True).start()

        if now.hour == 21 and now.minute == 30:
            if not has_run_lao_vip:
                has_run_lao_vip = True
                threading.Thread(target=fetch_lao_vip, daemon=True).start()
            if not has_run_lao_samakkhi_vip:
                has_run_lao_samakkhi_vip = True
                threading.Thread(target=fetch_lao_samakkhi_vip, daemon=True).start()

        if now.hour == 21 and now.minute == 50 and not has_run_england_vip:
            has_run_england_vip = True
            threading.Thread(target=fetch_england_vip, daemon=True).start()

        if now.hour == 22 and now.minute == 00 and not has_run_lao_star_vip:
            has_run_lao_star_vip = True
            threading.Thread(target=fetch_lao_star_vip, daemon=True).start()

        if now.hour == 22 and now.minute == 30 and not has_run_hanoi_extra:
            has_run_hanoi_extra = True
            threading.Thread(target=fetch_hanoi_extra, daemon=True).start()

        if now.hour == 22 and now.minute == 50 and not has_run_germany_vip:
            has_run_germany_vip = True
            threading.Thread(target=fetch_germany_vip, daemon=True).start()

        if now.hour == 23 and now.minute == 30 and not has_run_lao_redcross:
            has_run_lao_redcross = True
            threading.Thread(target=fetch_lao_redcross, daemon=True).start()

        if now.hour == 23 and now.minute == 50 and not has_run_russia_vip:
            has_run_russia_vip = True
            threading.Thread(target=fetch_russia_vip, daemon=True).start()

        time.sleep(30)

# ==========================================
# 🚀 5. เริ่มการทำงานทั้งหมด
# ==========================================
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    threading.Thread(target=time_checker, daemon=True).start()
    print("Bot is up and running with 9 lotteries...")
    bot.infinity_polling()

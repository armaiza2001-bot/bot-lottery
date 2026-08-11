import telebot
import cloudscraper
import requests
import time
import threading
import urllib.parse
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
                        
                        msg = (f"🇻🇳 ผลหวยฮานอยพิเศษ 🇻🇳\n📅 วันที่: {api_date}\n\n"
                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return 
        except Exception as e:
            print(f"[Error] ฮานอยพิเศษ: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ฮานอยพิเศษ**: ไม่พบข้อมูลวันที่ {today_str}")
            return
        time.sleep(10)

# ==========================================
# 🇸🇬 ดึงผลหวยหุ้นสิงคโปร์ VIP (อัปเดตโครงสร้าง JSON ล่าสุด)
# ==========================================
def fetch_singapore_vip_fast(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล **หวยหุ้นสิงคโปร์ VIP** งวดวันที่ {today_str_display} ครับ...")

    # URL ของ API หุ้นสิงคโปร์ VIP
    base_url = "https://api.stocks-vip.com/api/sg"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        # ใส่ timestamp กันเว็บแคชข้อมูลเก่า
        timestamp = int(datetime.now().timestamp() * 1000)
        url = f"{base_url}?t={timestamp}"
        
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            raw_data = res.json()
            
            # 🛑 เจาะโครงสร้าง: เช็คว่า status เป็น success และเจาะเข้า data -> prices
            if raw_data.get("status") == "success":
                prices_list = raw_data.get("data", {}).get("prices", [])
                
                if prices_list and len(prices_list) > 0:
                    # ดึงข้อมูลจากก้อนสุดท้าย (ล่าสุดตอนตลาดปิด)
                    latest_data = prices_list[-1]
                    
                    price = latest_data.get("price", 0)
                    diff = latest_data.get("diff", "0")
                    
                    # แปลงเป็นทศนิยม 2 ตำแหน่ง
                    price_str = f"{float(price):.2f}"
                    diff_str = f"{float(diff):.2f}"
                    
                    # 🎯 ตัดเลข 3 ตัวบน
                    integer_part, decimal_part = price_str.split('.')
                    top_3 = integer_part[-1] + decimal_part 
                    
                    # 👇 ตัดเลข 2 ตัวล่าง (ใช้ replace เอาเครื่องหมายลบออกถ้ามี)
                    bottom_2 = diff_str.replace('-', '').split('.')[1] 
                    
                    # 📢 ส่งผลเข้ากลุ่ม
                    msg = (f"🇸🇬 **ผลหวยหุ้นสิงคโปร์ VIP 🇸🇬\n📅 วันที่: {today_str_display}\n\n"
                           f"📊 SGX VIP: {price_str} ({float(diff):+.2f})\n\n"
                           f"🎯 **3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                    bot.send_message(GROUP_CHAT_ID, msg)
                    return
    except Exception as e:
        print(f"[Error] หวยหุ้นสิงคโปร์ VIP: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ **หวยหุ้นสิงคโปร์ VIP**: ไม่สามารถดึงข้อมูลได้ในขณะนี้")

# ==========================================
# 🇮🇳 IN ดึงผลหวยหุ้นอินเดีย (เปลี่ยนมาใช้ Yahoo Finance ข้อมูลเสถียรสุดหลังตลาดปิด)
# ==========================================
def fetch_india_stock_fast(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล **หวยหุ้นอินเดีย** งวดวันที่ {today_str_display} ครับ...")

    # ใช้ query1 ของ Yahoo สำหรับดัชนี SENSEX ของอินเดีย
    url = "https://query1.finance.yahoo.com/v8/finance/chart/^BSESN?interval=1d&range=1d"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        
        if res.status_code == 200:
            data = res.json()
            
            # ดึงข้อมูล meta
            meta = data.get("chart", {}).get("result", [])[0].get("meta", {})
            
            if meta:
                # ดึงราคาปิดและคำนวณค่า Change
                current_price = meta.get("regularMarketPrice", 0)
                prev_close = meta.get("chartPreviousClose", 0)
                change = current_price - prev_close
                
                # จัดรูปแบบทศนิยม 2 ตำแหน่ง
                price_str = f"{current_price:.2f}"
                change_str = f"{change:.2f}"
                
                # 🎯 ตัดเลข 3 ตัวบน (หลักหน่วย + ทศนิยม)
                integer_part, decimal_part = price_str.split('.')
                top_3 = integer_part[-1] + decimal_part
                
                # 👇 ตัดเลข 2 ตัวล่าง (เอาทศนิยมของค่า change)
                bottom_2 = change_str.replace('-', '').split('.')[1]
                
                # 📢 ส่งผลเข้ากลุ่ม Telegram
                msg = (f"🇮🇳 ผลหวยหุ้นอินเดีย 🇮🇳\n📅 วันที่: {today_str_display}\n\n"
                       f"📊 BSE SENSEX: {price_str} ({change:+.2f})\n\n"
                       f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                bot.send_message(GROUP_CHAT_ID, msg)
                return
            else:
                print("[Error] Yahoo Finance (India): ดึงโครงสร้าง Meta ไม่สำเร็จ")
        else:
            print(f"[Error] Yahoo Finance (India): ตอบกลับสถานะ {res.status_code}")
            
    except Exception as e:
        print(f"[Error] Yahoo Finance (India) Exception: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ **หวยหุ้นอินเดีย**: ไม่สามารถดึงข้อมูลจาก Yahoo Finance ได้ในขณะนี้")

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
                            msg = (f"🇻🇳 ผลหวยฮานอยสามัคคี 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
        except Exception as e:
            print(f"[Error] ฮานอยสามัคคี: {e}")
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ฮานอยสามัคคี**: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🇻🇳 ดึงผล: ฮานอยปกติ (18:30) [ดึงจากหน้า Live อัปเดตไวสุด]
# ==========================================
def fetch_hanoi_normal(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    today_str_html = target_date.strftime("%d/%m/%Y") 
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล **หวยฮานอยปกติ** งวดวันที่ {today_str_display} ครับ...")

    # 🚀 เปลี่ยนมาใช้หน้า Live หลักที่อัปเดตแบบ Real-time
    url = "https://www.minhngoc.net.vn/xo-so-mien-bac.html"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    }

    attempts = 0
    max_attempts = 30 # จำกัดการดึงสูงสุด 30 รอบ (ประมาณ 5 นาที) ป้องกันบอทค้าง

    while attempts < max_attempts:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')

            # 🛡️ เช็ควันที่หน้าเว็บก่อนว่าอัปเดตเป็นของวันนี้หรือยัง
            page_title = soup.find('h1', class_='pagetitle')
            box_title = soup.find('div', class_='title')
            
            is_correct_date = False
            if page_title and today_str_html in page_title.text:
                is_correct_date = True
            elif box_title and today_str_html in box_title.text:
                is_correct_date = True

            # 🎯 ถ้าวันที่ตรงกับวันนี้แล้ว ค่อยดึงตัวเลข
            if is_correct_date:
                prize_special = soup.find('td', class_='giaidb')
                prize_1 = soup.find('td', class_='giai1')

                if prize_special and prize_1:
                    text_db = prize_special.text.replace(" ", "").replace("-", "").strip()
                    text_1 = prize_1.text.replace(" ", "").replace("-", "").strip()

                    # ตรวจสอบว่าผลออกมาครบ 5 ตัวแล้วหรือยัง
                    if len(text_db) == 5 and len(text_1) == 5 and text_db.isdigit() and text_1.isdigit():
                        msg = (f"🇻🇳 ผลหวยฮานอยปกติ 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 3 ตัวบน: {text_db[-3:]}\n👇 2 ตัวล่าง: {text_1[-2:]}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return
                    else:
                        if not is_auto and attempts == 1:
                            bot.send_message(GROUP_CHAT_ID, f"🔍 [Debug] เจอช่องแล้วแต่เลขยังออกไม่ครบ บน:'{text_db}', ล่าง:'{text_1}'")
            else:
                if not is_auto and attempts == 1:
                    bot.send_message(GROUP_CHAT_ID, f"⚠️ [Debug] วันที่ในหน้าเว็บยังไม่ใช่ {today_str_display} (เว็บยังไม่รีเฟรชงวดใหม่)")

        except Exception as e:
            print(f"[Error] ฮานอยปกติ: {e}")
            
        # ถ้าเป็นการทดสอบดึงผลแบบแมนนวล (is_auto=False) ให้ลองแค่ 2 ครั้งพอ
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ฮานอยปกติ**: ไม่พบข้อมูลวันที่ {today_str_display} หรือผลยังไม่ออก")
            return
            
        time.sleep(10) # พัก 10 วินาทีก่อนลองใหม่

    # ถ้ารัน Auto จนครบ max_attempts แล้วยังไม่ได้ผล ให้แจ้งเตือน
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏰ **ฮานอยปกติ**: ดึงข้อมูลนานเกินเวลาที่กำหนด กรุณากดเช็คด้วยตัวเองอีกครั้งผ่าน /test_normal")
        
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
                    if len(prize_special) == 5 and len(prize_1) == 5 and prize_special.isdigit() and prize_1.isdigit():
                        top_3 = prize_special[-3:] 
                        bottom_2 = prize_1[-2:]    
                        msg = (f"🇻🇳 ผลหวยฮานอย VIP 🇻🇳\n📅 วันที่: {api_date}\n\n"
                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
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
                            msg = (f"🇻🇳 ผลหวยฮานอยพัฒนา 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
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
                            msg = (f"🇱🇦 ผลหวยลาวสามัคคี 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
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
                        msg = (f"🇱🇦 ผลหวยลาวอาเซียน 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 3 ตัวบน:** {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
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
                        
                        msg = (f"🇱🇦 ผลหวยลาว VIP 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
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
                            
                            msg = (f"🇱🇦 ผลหวยลาวสามัคคี VIP 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
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
                            
                            msg = (f"🇱🇦 ผลหวยลาวสตาร์ VIP 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
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
                        
                        if len(p1) >= 3 and len(p2) >= 2 and p1.isdigit() and p2.isdigit():
                            msg = (f"🇬🇧 ผลหวยอังกฤษ VIP 🇬🇧\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {p1[-3:]}\n👇 2 ตัวล่าง: {p2[-2:]}\n")
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
                        
                        if len(p1) >= 3 and len(p2) >= 2 and p1.isdigit() and p2.isdigit():
                            msg = (f"🇩🇪 ผลหวยเยอรมัน VIP 🇩🇪\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {p1[-3:]}\n👇 2 ตัวล่าง: {p2[-2:]}\n")
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
                        
                        if len(p1) >= 3 and len(p2) >= 2 and p1.isdigit() and p2.isdigit():
                            msg = (f"🇷🇺 ผลหวยรัสเซีย VIP 🇷🇺\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {p1[-3:]}\n👇 2 ตัวล่าง: {p2[-2:]}\n")
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
                        prize_2digits = str(results.get("prize_2nd", ""))
                        
                        if len(prize_1st) >= 3 and len(prize_2digits) >= 2 and prize_1st.isdigit() and prize_2digits.isdigit():
                            top_3 = prize_1st[-3:]
                            bottom_2 = prize_2digits[-2:]
                            
                            msg = (f"🇻🇳 ผลหวยฮานอย EXTRA 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
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
                        
                        msg = (f"🇱🇦 ผลหวยลาวกาชาด 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
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
# 🎰 2.16 ดึงผล: ดาวโจนส์ VIP (00:30)
# ==========================================
def fetch_dowjones_vip(offset_days=0, is_auto=True):
    # target_date คือวันที่เราต้องการแสดงผลให้คนดู (เช่น 03-08-2026)
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    # 💡 ทริคแก้ปัญหาหวยเที่ยงคืน: API ใช้วันที่ของเมื่อวาน (ต้องลบ 1 วัน)
    draw_date = target_date - timedelta(days=1)
    draw_str_api = draw_date.strftime("%Y-%m-%d") # จะได้เป็น 2026-08-02
    
    # ส่ง draw_str_api ไปดึงผล เพื่อให้ดึงย้อนหลังได้ด้วย
    url = f"https://api.dowjonespowerball.com/result?draw={draw_str_api}"
    
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล **หวยดาวโจนส์ VIP** งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                
                # เช็คสถานะ success และเจาะเข้ากล่อง data
                if json_data.get("status") == "success":
                    data_node = json_data.get("data", {})
                    api_lotto_date = str(data_node.get("lotto_date", "")).strip()
                    
                    # เช็คว่า lotto_date ตรงกับวันที่เราส่งไปขอหรือไม่ (เช่น 2026-08-02)
                    if api_lotto_date == draw_str_api:
                        results = data_node.get("results", {})
                        
                        p1 = str(results.get("prize_1st", "")).strip()
                        p2 = str(results.get("prize_2nd", "")).strip()
                        
                        # ล็อค 2 ชั้นเหมือนเดิม
                        if len(p1) >= 3 and len(p2) >= 2 and p1.isdigit() and p2.isdigit():
                            top_3 = p1[-3:]
                            bottom_2 = p2[-2:]
                            
                            msg = (f"🇺🇸 ผลหวยดาวโจนส์ VIP 🇺🇸\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
                    elif not is_auto and attempts == 1 and api_lotto_date != "":
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ **ดาวโจนส์ VIP**: ข้อมูลใน API ตอนนี้เป็นงวด {api_lotto_date}")
                        return
        except Exception as e:
            print(f"[Error] ดาวโจนส์ VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ **ดาวโจนส์ VIP**: ไม่พบข้อมูลงวดวันที่ {today_str_display}")
            return
        time.sleep(10)

# ==========================================
# 🇸🇬 ดึงผลหวยหุ้นสิงคโปร์ (ปกติ) จากเว็บ SGX โดยตรง
# ==========================================
def fetch_singapore_fast(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล **หวยหุ้นสิงคโปร์** งวดวันที่ {today_str_display} ครับ...")

    # ใช้ API ตรงของตลาดสิงคโปร์ SGX 
    url = "https://api.sgx.com/indices/v1.0/pid/.STI/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            
            # เจาะเข้าไปใน Array "data" 
            data_list = data.get("data", [])
            
            if data_list and len(data_list) > 0:
                latest_data = data_list[0]
                
                # "lp" = Last Price (ดัชนี), "c" = Change (ค่าการเปลี่ยนแปลง)
                current_price = latest_data.get("lp", 0)
                change = latest_data.get("c", 0)
                
                # จัดรูปแบบทศนิยม 2 ตำแหน่งกันเหนียว
                price_str = f"{float(current_price):.2f}"
                change_str = f"{float(change):.2f}"
                
                # 🎯 ตัดเลข 3 ตัวบน (หลักหน่วยหน้าจุด + ทศนิยม 2 ตำแหน่ง)
                integer_part, decimal_part = price_str.split('.')
                top_3 = integer_part[-1] + decimal_part 
                
                # 👇 ตัดเลข 2 ตัวล่าง (เอาเครื่องหมายลบออกก่อนถ้ามี)
                bottom_2 = change_str.replace('-', '').split('.')[1] 
                
                # 📢 ส่งผลเข้ากลุ่ม Telegram
                msg = (f"🇸🇬 ผลหวยหุ้นสิงคโปร์ 🇸🇬\n📅 วันที่: {today_str_display}\n\n"
                       f"📊 STI: {price_str} ({float(change):+.2f})\n\n"
                       f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                bot.send_message(GROUP_CHAT_ID, msg)
                return
    except Exception as e:
        print(f"[Error] หวยหุ้นสิงคโปร์: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ **หวยหุ้นสิงคโปร์**: ไม่สามารถดึงข้อมูลได้ในขณะนี้")

import requests
from datetime import datetime, timedelta

# ==========================================
# 🇹🇭 ดึงผลหวยหุ้นไทยเย็น (ใช้ Yahoo Finance API)
# ==========================================
def fetch_thai_evening_fast(offset_days=0, is_auto=True):
    target_date = datetime.now() - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล **หวยหุ้นไทยเย็น** งวดวันที่ {today_str_display} ครับ...")

    # ใช้ query1 ของ Yahoo ซึ่งเป็นตัวที่เสถียรและไม่ค่อยติดบล็อก
    url_set = "https://query1.finance.yahoo.com/v8/finance/chart/^SET.BK?interval=1d&range=1d"
    url_set50 = "https://query1.finance.yahoo.com/v8/finance/chart/^SET50.BK?interval=1d&range=1d"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        res_set = requests.get(url_set, headers=headers, timeout=15)
        res_set50 = requests.get(url_set50, headers=headers, timeout=15)
        
        if res_set.status_code == 200 and res_set50.status_code == 200:
            data_set = res_set.json()
            data_set50 = res_set50.json()
            
            # ดึงข้อมูล meta ซึ่งเป็นข้อมูลสรุปตัวเลขใหญ่ๆ ที่โชว์หน้าเว็บ
            meta_set = data_set.get("chart", {}).get("result", [])[0].get("meta", {})
            meta_set50 = data_set50.get("chart", {}).get("result", [])[0].get("meta", {})
            
            if meta_set and meta_set50:
                # ดึงราคาปิด SET และคำนวณค่า Change (+/-)
                set_last = meta_set.get("regularMarketPrice", 0)
                set_prev = meta_set.get("chartPreviousClose", 0)
                set_change = set_last - set_prev
                
                # ดึงราคาปิด SET50
                set50_last = meta_set50.get("regularMarketPrice", 0)
                
                # จัดรูปแบบทศนิยม 2 ตำแหน่ง
                set_last_str = f"{set_last:.2f}"
                set_change_str = f"{set_change:.2f}"
                set50_last_str = f"{set50_last:.2f}"
                
                # 🎯 ตัดเลข 3 ตัวบน (หลักหน่วย SET50 + ทศนิยม 2 ตัว SET)
                set50_last_digit = set50_last_str[-1]
                set_decimals = set_last_str.split('.')[1]
                top_3 = set50_last_digit + set_decimals
                
                # 👇 ตัดเลข 2 ตัวล่าง (ทศนิยมค่า Change ของ SET)
                bottom_2 = set_change_str.replace('-', '').split('.')[1]
                
                msg = (f"🇹🇭 ผลหวยหุ้นไทยเย็น 🇹🇭\n📅 วันที่: {today_str_display}\n\n"
                       f"📊 SET: {set_last_str} ({set_change:+.2f})\n"
                       f"📊 SET50: {set50_last_str}\n\n"
                       f"🎯 **3 ตัวบน:** {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                bot.send_message(GROUP_CHAT_ID, msg)
                return
            else:
                print("[Error] Yahoo Finance: ดึงโครงสร้าง Meta ไม่สำเร็จ")
        else:
            print(f"[Error] Yahoo Finance: SET={res_set.status_code}, SET50={res_set50.status_code}")
            
    except Exception as e:
        print(f"[Error] Yahoo Finance Exception: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ **หวยหุ้นไทยเย็น**: ไม่สามารถดึงข้อมูลจาก Yahoo Finance ได้ในขณะนี้")

# ==========================================
# 🇲🇾 ดึงผลหวยมาเลย์ (Magnum 4D) + ระบบถอดรหัส Key อัตโนมัติ
# ==========================================
def fetch_malay_magnum(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    today_api_format = target_date.strftime("%d/%m/%Y")
    
    url = "https://www.magnum4d.my/live-draw"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            results = data.get("Data", {}).get("Results", {})
            
            if results:
                draw_date = results.get("DrawDate", "")
                
                if is_auto and draw_date != today_api_format:
                    return # ให้บอทจบการทำงานเงียบๆ ไม่ต้องส่งอะไรเข้ากลุ่ม
                    
                if is_auto:
                    bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล **หวยมาเลย์** งวดวันที่ {today_str_display} ครับ...")
                    
                # 🔍 1. ดึงตัวอักษรที่บอกตำแหน่งรางวัลที่ 1 และ 2
                t1_letter = results.get("T1", "") # ตัวอักษรของรางวัลที่ 1
                t2_letter = results.get("T2", "") # ตัวอักษรของรางวัลที่ 2
                
                if t1_letter and t2_letter:
                    # ⚙️ 2. แปลงตัวอักษรเป็นตัวเลข (A=1, B=2, ..., M=13) ด้วยการใช้ ASCII code
                    # ord('A') จะได้ 65 ดังนั้นลบ 64 จะได้ 1 พอดี
                    t1_idx = ord(t1_letter.upper()) - 64
                    t2_idx = ord(t2_letter.upper()) - 64
                    
                    # 🎯 3. ประกอบร่างสร้างชื่อ Key เช่น S02, S10
                    key_1st = f"S{t1_idx:02d}"
                    key_2nd = f"S{t2_idx:02d}"
                    
                    # 📥 4. ดึงผลรางวัลที่ 1 และ 2 ออกมาอย่างแม่นยำ
                    prize_1st = results.get(key_1st, "")
                    prize_2nd = results.get(key_2nd, "")
                    
                    if prize_1st and prize_2nd:
                        # 🎯 3 ตัวบน: เอา 3 ตัวท้ายของรางวัลที่ 1
                        top_3 = prize_1st[-3:]
                        
                        # 👇 2 ตัวล่าง: เอา 2 ตัวท้ายของรางวัลที่ 2
                        bottom_2 = prize_2nd[-2:]
                        
                        msg = (f"🇲🇾 **ผลหวยมาเลย์ (Magnum 4D)** 🇲🇾\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 **3 ตัวบน:** {top_3}\n👇 **2 ตัวล่าง:** {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return
                        
    except Exception as e:
        print(f"[Error] หวยมาเลย์: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ **หวยมาเลย์**: ไม่พบผลรางวัลของวันที่ {today_str_display} (อาจไม่มีรอบ Special Draw)")

# ==========================================
# 🇬🇧 ดึงผลหวยหุ้นอังกฤษ (จากดัชนี FTSE 100 โดยตรง)
# ==========================================
def fetch_england_stock_fast(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล **หวยหุ้นอังกฤษ** งวดวันที่ {today_str_display} (จากกระดานหุ้นโลก) ครับ...")

    url = "https://query1.finance.yahoo.com/v8/finance/chart/^FTSE"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            result = data.get("chart", {}).get("result", [])
            if result:
                meta = result[0].get("meta", {})
                current_price = meta.get("regularMarketPrice", 0)
                prev_close = meta.get("chartPreviousClose", 0)
                change = current_price - prev_close
                
                # จัดรูปแบบทศนิยม 2 ตำแหน่ง
                price_str = f"{current_price:.2f}"
                change_str = f"{change:.2f}"
                
                # 🎯 ตัดเลข 3 ตัวบน (หลักหน่วยของค่าดัชนี + ทศนิยม 2 ตำแหน่ง)
                integer_part, decimal_part = price_str.split('.')
                top_3 = integer_part[-1] + decimal_part 
                
                # 👇 ตัดเลข 2 ตัวล่าง (ทศนิยม 2 ตำแหน่งของค่าเปลี่ยนแปลง)
                bottom_2 = change_str.split('.')[1]
                
                # 📢 ส่งผลเข้ากลุ่ม Telegram
                msg = (f"🇬🇧 ผลหวยหุ้นอังกฤษ 🇬🇧\n📅 วันที่: {today_str_display}\n\n"
                       f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง:** {bottom_2}\n")
                bot.send_message(GROUP_CHAT_ID, msg)
                return
    except Exception as e:
        print(f"[Error] หวยหุ้นอังกฤษ: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ **หวยหุ้นอังกฤษ**: ไม่สามารถดึงข้อมูลได้ในขณะนี้")

# ==========================================
# 🇩🇪 ดึงผลหวยหุ้นเยอรมัน (DAX) จาก Yahoo Finance
# ==========================================
def fetch_germany_normal(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล **หวยหุ้นเยอรมัน** งวดวันที่ {today_str_display} ครับ...")

    # ใช้ดัชนี ^GDAXI สำหรับ DAX ของเยอรมัน
    url = "https://query1.finance.yahoo.com/v8/finance/chart/^GDAXI"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            result = data.get("chart", {}).get("result", [])
            if result:
                meta = result[0].get("meta", {})
                current_price = meta.get("regularMarketPrice", 0)
                prev_close = meta.get("chartPreviousClose", 0)
                change = current_price - prev_close
                
                # จัดรูปแบบทศนิยม 2 ตำแหน่ง
                price_str = f"{current_price:.2f}"
                change_str = f"{change:.2f}"
                
                # 🎯 ตัดเลข 3 ตัวบน (หลักหน่วย + ทศนิยม)
                integer_part, decimal_part = price_str.split('.')
                top_3 = integer_part[-1] + decimal_part 
                
                # 👇 ตัดเลข 2 ตัวล่าง (เอาเครื่องหมายลบออกก่อนถ้ามี)
                bottom_2 = change_str.replace('-', '').split('.')[1] 
                
                # 📢 ส่งผลเข้ากลุ่ม Telegram
                msg = (f"🇩🇪 ผลหวยหุ้นเยอรมัน (DAX) 🇩🇪\n📅 วันที่: {today_str_display}\n\n"
                       f"📊 DAX: {price_str} ({change:+.2f})\n\n"
                       f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                bot.send_message(GROUP_CHAT_ID, msg)
                return
    except Exception as e:
        print(f"[Error] หวยหุ้นเยอรมัน: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ **หวยหุ้นเยอรมัน**: ไม่สามารถดึงข้อมูลได้ในขณะนี้")

# ==========================================
# 🇷🇺 ดึงผลหวยหุ้นรัสเซีย (อ้างอิง MOEX Blue Chip จาก rts-standard)
# ==========================================
def fetch_russia_normal(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล **หวยหุ้นรัสเซีย** งวดวันที่ {today_str_display} ครับ...")

    # 🛑 อัปเดต API เป็น MOEXBC เพื่อให้เลข 15,000+ ตรงกับเว็บ Investing.com
    url = "https://iss.moex.com/iss/engines/stock/markets/index/securities/MOEXBC.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            
            marketdata = data.get("marketdata", {})
            columns = marketdata.get("columns", [])
            row_data = marketdata.get("data", [[]])[0]
            
            if columns and row_data:
                try:
                    idx_current = columns.index("CURRENTVALUE")
                    idx_change = columns.index("LASTCHANGE")
                    
                    current_price = float(row_data[idx_current])
                    change = float(row_data[idx_change])
                    
                    price_str = f"{current_price:.2f}"
                    change_str = f"{change:.2f}"
                    
                    # 🎯 ตัดเลข 3 ตัวบน (หลักหน่วย + ทศนิยม 2 ตำแหน่ง)
                    integer_part, decimal_part = price_str.split('.')
                    top_3 = integer_part[-1] + decimal_part 
                    
                    # 👇 ตัดเลข 2 ตัวล่าง (เอาเครื่องหมายลบออกก่อน)
                    bottom_2 = change_str.replace('-', '').split('.')[1] 
                    
                    # 📢 ส่งผลเข้ากลุ่ม Telegram
                    msg = (f"🇷🇺 ผลหวยหุ้นรัสเซีย (RTS Standard) 🇷🇺\n📅 วันที่: {today_str_display}\n\n"
                           f"📊 Index: {price_str} ({change:+.2f})\n\n"
                           f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                    bot.send_message(GROUP_CHAT_ID, msg)
                    return
                except ValueError:
                    print("[Error] หวยหุ้นรัสเซีย: ไม่พบข้อมูลใน API")
    except Exception as e:
        print(f"[Error] หวยหุ้นรัสเซีย: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ **หวยหุ้นรัสเซีย**: ไม่สามารถดึงข้อมูลได้ในขณะนี้")

# ==========================================
# 🇺🇸 ดึงผลหวยหุ้นดาวโจนส์ (ปกติ) จาก Yahoo Finance (^DJI)
# ==========================================
def fetch_dowjones_normal(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล **หวยหุ้นดาวโจนส์** งวดวันที่ {today_str_display} ครับ...")

    # ใช้ดัชนี ^DJI (Dow Jones Industrial Average)
    url = "https://query1.finance.yahoo.com/v8/finance/chart/^DJI"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            result = data.get("chart", {}).get("result", [])
            if result:
                meta = result[0].get("meta", {})
                current_price = meta.get("regularMarketPrice", 0)
                prev_close = meta.get("chartPreviousClose", 0)
                change = current_price - prev_close
                
                # จัดรูปแบบทศนิยม 2 ตำแหน่ง
                price_str = f"{current_price:.2f}"
                change_str = f"{change:.2f}"
                
                # 🎯 ตัดเลข 3 ตัวบน (หลักหน่วยหน้าจุด + ทศนิยม 2 ตำแหน่ง)
                integer_part, decimal_part = price_str.split('.')
                top_3 = integer_part[-1] + decimal_part 
                
                # 👇 ตัดเลข 2 ตัวล่าง (เอาเครื่องหมายลบออกก่อนถ้ามี)
                bottom_2 = change_str.replace('-', '').split('.')[1] 
                
                # 📢 ส่งผลเข้ากลุ่ม Telegram
                msg = (f"🇺🇸 ผลหวยหุ้นดาวโจนส์ (ปกติ) 🇺🇸\n📅 วันที่: {today_str_display}\n\n"
                       f"📊 Dow Jones: {price_str} ({change:+.2f})\n\n"
                       f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                bot.send_message(GROUP_CHAT_ID, msg)
                return
    except Exception as e:
        print(f"[Error] หวยหุ้นดาวโจนส์: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ **หวยหุ้นดาวโจนส์**: ไม่สามารถดึงข้อมูลได้ในขณะนี้")
        
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
        "📌 **ตารางแจ้งผลอัตโนมัติ และคำสั่งทดสอบ:**\n\n"
        "- 16:30 น. : สิงคโปร์ /test_singapore\n"
        "- 16:45 น. : ไทยเย็น /test_thai_evening\n"
        "- 17:11 น. : อินเดีย /test_india\n"
        "- 17:12 น. : สิงคโปร์ VIP /test_singapore_vip\n"
        "- 17:30 น. : ฮานอยพิเศษ /test_special\n"
        "- 17:30 น. : ฮานอยสามัคคี /test_samakkhi\n"
        "- 18:30 น. : ฮานอยปกติ /test_normal\n"
        "- 18:45 น. : มาเลย์ (พุธ, เสาร์, อาทิตย์) /test_malay\n"
        "- 19:30 น. : ฮานอย VIP /test_vip\n"
        "- 19:30 น. : ฮานอยพัฒนา /test_develop\n"
        "- 20:30 น. : ลาวสามัคคี /test_lao_samakkhi\n"
        "- 21:00 น. : ลาวอาเซียน /test_lao_asean\n"
        "- 21:30 น. : ลาว VIP /test_lao_vip\n"
        "- 21:30 น. : ลาวสามัคคี VIP /test_lao_samakkhi_vip\n"
        "- 21:50 น. : อังกฤษ VIP /test_england_vip\n"
        "- 22:00 น. : ลาวสตาร์ VIP /test_lao_star_vip\n"
        "- 22:30 น. : ฮานอย EXTRA /test_hanoi_extra\n"
        "- 22:50 น. : เยอรมัน VIP /test_germany_vip\n"
        "- 23:00 น. : อังกฤษ (ปกติ) /test_england_normal\n"
        "- 23:00 น. : เยอรมัน (ปกติ) /test_germany_normal\n"
        "- 23:00 น. : รัสเซีย (ปกติ) /test_russia_normal\n"
        "- 23:30 น. : ลาวกาชาด /test_lao_redcross\n"
        "- 23:50 น. : รัสเซีย VIP /test_russia_vip\n"
        "- 00:30 น. : ดาวโจนส์ VIP /test_dowjones_vip\n"
        "- 04:10 น. : ดาวโจนส์ (ปกติ) /test_dowjones_normal\n\n"
        "🔄 **คำสั่งอื่นๆ:**\n"
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

# ==========================================
# 🧹 คำสั่งสำหรับให้บอทลบข้อความของตัวเอง (ลบแค่ของบอทเท่านั้น)
# ==========================================
@bot.message_handler(commands=['del', 'delete'])
def delete_bot_message(message):
    # เช็คว่ามีการ Reply ข้อความอยู่หรือไม่
    if message.reply_to_message:
        # เช็คว่าข้อความที่ถูก Reply เป็นของบอทหรือไม่
        if message.reply_to_message.from_user.id == bot.get_me().id:
            try:
                # ลบเฉพาะข้อความของบอทที่ถูกตอบกลับ
                bot.delete_message(message.chat.id, message.reply_to_message.message_id)
            except Exception:
                pass # ถ้าลบไม่ได้ (เช่น โดนเตะออกจากสิทธิ์แอดมิน) ก็ให้เงียบไว้

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

@bot.message_handler(commands=['test_dowjones_vip'])
def test_dowjones_vip_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ดาวโจนส์ VIP**{txt}...")
    threading.Thread(target=fetch_dowjones_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_england_normal'])
def test_england_normal_cmd(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **หวยหุ้นอังกฤษ** จากตลาดหุ้น...")
    threading.Thread(target=fetch_england_stock_fast, args=(0, False), daemon=True).start()

@bot.message_handler(commands=['test_germany_normal'])
def test_germany_normal_cmd(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **หวยหุ้นเยอรมัน (ปกติ)** ล่าสุด...")
    threading.Thread(target=fetch_germany_normal, daemon=True).start()

@bot.message_handler(commands=['test_russia_normal'])
def test_russia_normal_cmd(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **หวยหุ้นรัสเซีย (ปกติ)** ล่าสุด...")
    threading.Thread(target=fetch_russia_normal, daemon=True).start()

@bot.message_handler(commands=['test_thai_evening'])
def test_thai_evening_cmd(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **หวยหุ้นไทย (เย็น)** จากตลาดหุ้น...")
    threading.Thread(target=fetch_thai_evening_fast, args=(0, False), daemon=True).start()

@bot.message_handler(commands=['test_singapore'])
def test_singapore_cmd(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **หวยหุ้นสิงคโปร์** จากตลาดหุ้น...")
    threading.Thread(target=fetch_singapore_fast, args=(0, False), daemon=True).start()

@bot.message_handler(commands=['test_malay'])
def test_malay_cmd(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **หวยมาเลย์** จากเว็บ Magnum4D...")
    threading.Thread(target=fetch_malay_magnum, args=(0, False), daemon=True).start()

@bot.message_handler(commands=['test_singapore_vip'])
def test_singapore_vip_cmd(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **หวยหุ้นสิงคโปร์ VIP**...")
    threading.Thread(target=fetch_singapore_vip_fast, args=(0, False), daemon=True).start()

@bot.message_handler(commands=['test_india'])
def test_india_cmd(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **หวยหุ้นอินเดีย**...")
    threading.Thread(target=fetch_india_stock_fast, args=(0, False), daemon=True).start()

@bot.message_handler(commands=['test_germany'])
def test_germany_cmd(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **หวยหุ้นเยอรมัน (DAX)**...")
    threading.Thread(target=fetch_germany_normal, args=(0, False), daemon=True).start()

@bot.message_handler(commands=['test_russia'])
def test_russia_cmd(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **หวยหุ้นรัสเซีย (RTS)**...")
    threading.Thread(target=fetch_russia_normal, args=(0, False), daemon=True).start()

@bot.message_handler(commands=['test_dowjones_normal'])
def test_dowjones_normal_cmd(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **หวยหุ้นดาวโจนส์ (ปกติ)**...")
    threading.Thread(target=fetch_dowjones_normal, args=(0, False), daemon=True).start()
    
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
    has_run_dowjones_vip = False
    has_run_england_vip = False
    has_run_germany_vip = False
    has_run_russia_vip = False
    has_run_england_normal = False
    has_run_germany_normal = False
    has_run_russia_normal = False
    has_run_thai_evening = False
    has_run_singapore = False
    has_run_malay = False
    has_run_singapore_vip = False
    has_run_india = False
    has_run_dowjones_normal = False
    
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
            has_run_lao_star_vip = False
            has_run_hanoi_extra = False
            has_run_lao_redcross = False
            has_run_dowjones_vip = False
            has_run_england_vip = False
            has_run_germany_vip = False
            has_run_russia_vip = False
            has_run_england_normal = False
            has_run_germany_normal = False
            has_run_russia_normal = False
            has_run_thai_evening = False
            has_run_singapore = False
            has_run_malay = False
            has_run_singapore_vip = False
            has_run_india = False
            has_run_dowjones_normal = False

            last_check_date = current_date

        # 🕒 รอบ 17:30 น.
        if now.hour == 17 and now.minute == 30:
            if not has_run_special:
                has_run_special = True
                threading.Thread(target=fetch_hanoi_special, daemon=True).start()
                time.sleep(2) # 📌 หน่วงเวลาคั่น
                
            if not has_run_samakkhi:
                has_run_samakkhi = True
                threading.Thread(target=fetch_hanoi_samakkhi, daemon=True).start()

        # 🕒 รอบ 18:30 น.
        if now.hour == 18 and now.minute == 30 and not has_run_normal:
            has_run_normal = True
            threading.Thread(target=fetch_hanoi_normal, daemon=True).start()

        # 🕒 รอบ 19:30 น.
        if now.hour == 19 and now.minute == 30:
            if not has_run_vip:
                has_run_vip = True
                threading.Thread(target=fetch_hanoi_vip, daemon=True).start()
                time.sleep(2) # 📌 หน่วงเวลาคั่น
                
            if not has_run_develop:
                has_run_develop = True
                threading.Thread(target=fetch_hanoi_develop, daemon=True).start()

        # 🕒 รอบ 20:30 น.
        if now.hour == 20 and now.minute == 30 and not has_run_lao_samakkhi:
            has_run_lao_samakkhi = True
            threading.Thread(target=fetch_lao_samakkhi, daemon=True).start()

        # 🕒 รอบ 21:00 น.
        if now.hour == 21 and now.minute == 00 and not has_run_lao_asean:
            has_run_lao_asean = True
            threading.Thread(target=fetch_lao_asean, daemon=True).start()

        # 🕒 รอบ 21:30 น.
        if now.hour == 21 and now.minute == 30:
            if not has_run_lao_vip:
                has_run_lao_vip = True
                threading.Thread(target=fetch_lao_vip, daemon=True).start()
                time.sleep(2) # 📌 หน่วงเวลาคั่น
                
            if not has_run_lao_samakkhi_vip:
                has_run_lao_samakkhi_vip = True
                threading.Thread(target=fetch_lao_samakkhi_vip, daemon=True).start()

        # 🕒 รอบ 21:50 น.
        if now.hour == 21 and now.minute == 50 and not has_run_england_vip:
            has_run_england_vip = True
            threading.Thread(target=fetch_england_vip, daemon=True).start()

        # 🕒 รอบ 22:00 น.
        if now.hour == 22 and now.minute == 00 and not has_run_lao_star_vip:
            has_run_lao_star_vip = True
            threading.Thread(target=fetch_lao_star_vip, daemon=True).start()

        # 🕒 รอบ 22:30 น.
        if now.hour == 22 and now.minute == 30 and not has_run_hanoi_extra:
            has_run_hanoi_extra = True
            threading.Thread(target=fetch_hanoi_extra, daemon=True).start()

        # 🕒 รอบ 22:50 น.
        if now.hour == 22 and now.minute == 50 and not has_run_germany_vip:
            has_run_germany_vip = True
            threading.Thread(target=fetch_germany_vip, daemon=True).start()

        # 🕒 รอบ 23:00 น. (หวยหุ้นอังกฤษ)
        if now.hour == 23 and now.minute == 0 and now.weekday() < 5:
            if not has_run_england_normal:
                has_run_england_normal = True
                threading.Thread(target=fetch_england_stock_fast, daemon=True).start()
                time.sleep(2)
                
        # 🕒 รอบ 23:30 น.
        if now.hour == 23 and now.minute == 30 and not has_run_lao_redcross:
            has_run_lao_redcross = True
            threading.Thread(target=fetch_lao_redcross, daemon=True).start()

        # 🕒 รอบ 23:50 น.
        if now.hour == 23 and now.minute == 50 and not has_run_russia_vip:
            has_run_russia_vip = True
            threading.Thread(target=fetch_russia_vip, daemon=True).start()

        # 🕒 รอบ 00:30 น.
        if now.hour == 0 and now.minute == 30 and not has_run_dowjones_vip:
            has_run_dowjones_vip = True
            threading.Thread(target=fetch_dowjones_vip, daemon=True).start()

        # 🕒 รอบ 16:45 น. (หวยหุ้นไทยรอบเย็น)
        if now.hour == 16 and now.minute == 50 and now.weekday() < 5:
            if not has_run_thai_evening:
                has_run_thai_evening = True
                threading.Thread(target=fetch_thai_evening_fast, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 16:30 น. (หวยหุ้นสิงคโปร์)
        if now.hour == 16 and now.minute == 30 and now.weekday() < 5:
            if not has_run_singapore:
                has_run_singapore = True
                threading.Thread(target=fetch_singapore_fast, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 18:40 น. (หวยมาเลย์ - อังคาร(พิเศษ), พุธ, เสาร์, อาทิตย์)
        if now.hour == 18 and now.minute == 45 and now.weekday() in [1, 2, 5, 6]:
            if not has_run_malay:
                has_run_malay = True
                threading.Thread(target=fetch_malay_magnum, daemon=True).start()
                time.sleep(2)

                # 🕒 รอบ 17:11 น. (หวยหุ้นสิงคโปร์ VIP) 
        if now.hour == 17 and now.minute == 12:
            if not has_run_singapore_vip:
                has_run_singapore_vip = True
                threading.Thread(target=fetch_singapore_vip_fast, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 17:30 น. (หวยหุ้นอินเดีย) 
        if now.hour == 17 and now.minute == 12 and now.weekday() < 5: # จันทร์-ศุกร์
            if not has_run_india:
                has_run_india = True
                threading.Thread(target=fetch_india_stock_fast, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 23:00 น. (หวยหุ้นเยอรมัน - ช่วงฤดูร้อน) 
        if now.hour == 23 and now.minute == 0 and now.weekday() < 5:
            if not has_run_germany_normal:
                has_run_germany_normal = True
                threading.Thread(target=fetch_germany_normal, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 23:05 น. (หวยหุ้นรัสเซีย) 
        if now.hour == 23 and now.minute == 0 and now.weekday() < 5:
            if not has_run_russia_normal:
                has_run_russia_normal = True
                threading.Thread(target=fetch_russia_normal, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 04:10 น. (หวยหุ้นดาวโจนส์ ปกติ) 
        if now.hour == 4 and now.minute == 10 and now.weekday() < 5: # จันทร์-ศุกร์ (เช้ามืด อังคาร-เสาร์)
            if not has_run_dowjones_normal:
                has_run_dowjones_normal = True
                threading.Thread(target=fetch_dowjones_normal, daemon=True).start()
                time.sleep(2)


        time.sleep(30)

# ==========================================
# 🚀 5. เริ่มการทำงานทั้งหมด
# ==========================================
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    threading.Thread(target=time_checker, daemon=True).start()
    print("Bot is up and running with 9 lotteries...")
    bot.infinity_polling()

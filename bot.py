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
# 🇱🇦 ดึงผล: ลาว Extra (08:30)
# ==========================================
def fetch_lao_extra(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    url = "https://api.laoextra.com/result"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยลาว Extra งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                
                data_node = json_data.get("data", json_data) if isinstance(json_data, dict) else json_data
                api_date = str(data_node.get("lotto_date", "")).strip()
                
                if api_date == today_str_api:
                    results_node = data_node.get("results", {})
                    digit5 = str(results_node.get("digit5") or "").strip()
                    
                    # 🛡️ ดักจับความถูกต้อง: ต้องยาว 5 ตัวและเป็นตัวเลขล้วน
                    if len(digit5) == 5 and digit5.isdigit():
                        top_3 = digit5[-3:]    
                        bottom_2 = digit5[:2]  
                        
                        msg = (f"🇱🇦 ผลหวยลาว Extra 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return 
        except Exception as e:
            print(f"[Error] ลาว Extra: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ลาว Extra: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇯🇵 ดึงผล: นิเคอิเช้า VIP
# ==========================================
def fetch_nikkei_morning_vip(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    timestamp = int(datetime.now().timestamp() * 1000)

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยนิเคอิเช้า VIP งวดวันที่ {today_str_display} ครับ...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }

    attempts = 0
    while True:
        attempts += 1
        try:
            if offset_days == 0:
                url = f"https://api.nikkeivipstock.com/api/jp?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    
                    if json_data.get("status") == "success":
                        prices_list = json_data.get("data", {}).get("prices", [])
                        
                        for item in prices_list:
                            if item.get("note") == "Morning-Close":
                                price = str(item.get("price") or "0")
                                diff = str(item.get("diff") or "0")
                                
                                try:
                                    price_str = f"{float(price):.2f}"
                                    diff_str = f"{float(diff):.2f}"
                                    
                                    integer_part, decimal_part = price_str.split('.')
                                    top_3 = integer_part[-1] + decimal_part
                                    bottom_2 = diff_str.replace('-', '').replace('+', '').split('.')[1]
                                    
                                    if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                        msg = (f"🇯🇵 ผลหวยนิเคอิเช้า VIP 🇯🇵\n📅 วันที่: {today_str_display}\n\n"
                                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                        bot.send_message(GROUP_CHAT_ID, msg)
                                        return
                                except ValueError:
                                    pass

            else:
                url = f"https://api.nikkeivipstock.com/api/history/jp?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    if json_data.get("status") == "success":
                        for item in json_data.get("data", []):
                            if item.get("date") == today_str_api:
                                r1_data = item.get("r1", {})
                                top_3 = str(r1_data.get("prize_1st", "")).strip()
                                bottom_2 = str(r1_data.get("prize_2nd", "")).strip()
                                
                                if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                    msg = (f"🇯🇵 ผลหวยนิเคอิเช้า VIP 🇯🇵\n📅 วันที่: {today_str_display}\n\n"
                                           f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                    bot.send_message(GROUP_CHAT_ID, msg)
                                    return
                                    
        except Exception as e:
            print(f"[Error] นิเคอิเช้า VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ นิเคอิเช้า VIP: ไม่พบผลของวันที่ {today_str_display} (API อาจจะยังไม่อัปเดต)")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇯🇵 ดึงผล: นิเคอิเช้า (ปกติ)
# ==========================================
def fetch_nikkei_morning_normal(offset_days=0, is_auto=True):
    import requests
    from bs4 import BeautifulSoup
    from datetime import datetime, timedelta
    import re
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    thai_months = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
    thai_day = target_date.day
    thai_month = thai_months[target_date.month]
    thai_year = target_date.year + 543
    thai_date_str = f"{thai_day} {thai_month} {thai_year}"
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยนิเคอิเช้า (ปกติ) งวดวันที่ {today_str_display} ครับ...")

    url = "https://saihuay.com/historical?lotto=nikkei_morning&lang=th"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                table = soup.find("table")
                if table:
                    tbody = table.find("tbody")
                    if tbody:
                        first_row = tbody.find("tr")
                        if first_row:
                            cells = first_row.find_all("td")
                            if len(cells) >= 3:
                                row_date = cells[0].get_text(strip=True)
                                
                                if thai_date_str in row_date:
                                    top3 = cells[1].get_text(strip=True)
                                    bot2 = cells[2].get_text(strip=True)
                                    
                                    # 🛡️ ดักจับความบริสุทธิ์ของตัวเลขด้วย re.fullmatch
                                    if not (re.fullmatch(r"\d+", top3) and re.fullmatch(r"\d+", bot2)):
                                        if not is_auto and attempts >= 2:
                                            bot.send_message(GROUP_CHAT_ID, f"⏳ นิเคอิเช้า (ปกติ): ผลรางวัลกำลังออกครับ (รอเว็บอัปเดตตัวเลข)")
                                            return
                                    else:
                                        msg = (f"🇯🇵 ผลหวยนิเคอิเช้า (ปกติ) 🇯🇵\n📅 วันที่: {today_str_display}\n\n"
                                               f"🎯 3 ตัวบน: {top3}\n👇 2 ตัวล่าง: {bot2}\n")
                                        bot.send_message(GROUP_CHAT_ID, msg)
                                        return
                                else:
                                    if not is_auto and attempts >= 2:
                                        bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {thai_date_str} ยังไม่ออกครับ (หน้าเว็บยังเป็นงวด {row_date})")
                                        return
                                        
        except Exception as e:
            print(f"[Error] นิเคอิเช้า (ปกติ) สายหวย Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ นิเคอิเช้า (ปกติ): ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇻🇳 ดึงผล: ฮานอยอาเซียน
# ==========================================
def fetch_hanoi_asean(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time

    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d")
    today_str_display = target_date.strftime("%d-%m-%Y")

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล ฮานอยอาเซียน งวดวันที่ {today_str_display}...")

    url = "https://gg.hanoiasean.com/api/result"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                json_data = res.json()
                
                if json_data.get("status") == "success":
                    data = json_data.get("data", {})
                    api_date = data.get("lotto_date", "")
                    
                    if api_date == today_str_api:
                        results = data.get("results", {})
                        
                        prize_1st = str(results.get("prize_1st") or "").strip()
                        prize_2nd = str(results.get("prize_2nd") or "").strip()
                        
                        # 🛡️ ดักบั๊ก "one" และค่าว่างด้วย .isdigit()
                        if len(prize_1st) >= 3 and len(prize_2nd) >= 2 and prize_1st.isdigit() and prize_2nd.isdigit():
                            top_3 = prize_1st[-3:]
                            bottom_2 = prize_2nd[-2:]
                            
                            msg = (f"🇻🇳 ผลหวยฮานอยอาเซียน 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n"
                                   f"👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return
                        else:
                            if not is_auto and attempts >= 2:
                                bot.send_message(GROUP_CHAT_ID, f"⏳ ฮานอยอาเซียน: กำลังรอผลรางวัลอัปเดตครับ")
                                return
                    else:
                        if not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {today_str_display} ยังไม่ออกครับ (หน้าเว็บยังเป็นงวด {api_date})")
                            return
                else:
                    print(f"[Error] ฮานอยอาเซียน: สถานะ API ไม่สำเร็จ")
            else:
                print(f"[Error] ฮานอยอาเซียน: ตอบกลับสถานะ {res.status_code}")
                
        except Exception as e:
            print(f"[Error] ฮานอยอาเซียน Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮานอยอาเซียน: ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇨🇳 ดึงผล: จีนเช้า VIP
# ==========================================
def fetch_china_morning_vip(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยจีนเช้า VIP งวดวันที่ {today_str_display}...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(datetime.now().timestamp() * 1000)
        
        try:
            if offset_days == 0:
                url = f"https://api.shenzhenindex.com/api/cn?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    
                    if json_data.get("status") == "success":
                        prices_list = json_data.get("data", {}).get("prices", [])
                        
                        for item in prices_list:
                            if item.get("note") == "Morning-Close":
                                price = str(item.get("price") or "0")
                                diff = str(item.get("diff") or "0")
                                
                                try:
                                    price_str = f"{float(price):.2f}"
                                    diff_str = f"{float(diff):.2f}"
                                    
                                    integer_part, decimal_part = price_str.split('.')
                                    top_3 = integer_part[-1] + decimal_part
                                    bottom_2 = diff_str.replace('-', '').replace('+', '').split('.')[1]
                                    
                                    if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                        msg = (f"🇨🇳 ผลหวยจีนเช้า VIP 🇨🇳\n📅 วันที่: {today_str_display}\n\n"
                                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                        bot.send_message(GROUP_CHAT_ID, msg)
                                        return
                                except ValueError:
                                    pass

            else:
                url = f"https://api.shenzhenindex.com/api/history/cn?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    if json_data.get("status") == "success":
                        for item in json_data.get("data", []):
                            if item.get("date") == today_str_api:
                                r1_data = item.get("r1", {})
                                top_3 = str(r1_data.get("prize_1st", "")).strip()
                                bottom_2 = str(r1_data.get("prize_2nd", "")).strip()
                                
                                if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                    msg = (f"🇨🇳 ผลหวยจีนเช้า VIP 🇨🇳\n📅 วันที่: {today_str_display}\n\n"
                                           f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                    bot.send_message(GROUP_CHAT_ID, msg)
                                    return
                                    
        except Exception as e:
            print(f"[Error] จีนเช้า VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ จีนเช้า VIP: ไม่พบผลของวันที่ {today_str_display} (ตลาดอาจจะยังไม่ปิดรอบเช้า)")
            return
            
       # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇨🇳 ดึงผล: หุ้นจีนเช้า (ปกติ)
# ==========================================
def fetch_china_morning_normal(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time
    import random
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d")
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยหุ้นจีนเช้า (ปกติ) งวดวันที่ {today_str_display}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.szse.cn/",
        "Accept": "application/json"
    }

    attempts = 0
    while True:
        attempts += 1
        rand_val = random.random()
        url = f"https://www.szse.cn/api/market/ssjjhq/getTimeData?random={rand_val}&marketId=1&code=399001"
        
        try:
            res = requests.get(url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                json_data = res.json()
                
                if str(json_data.get("code")) == "0":
                    data = json_data.get("data", {})
                    market_time = data.get("marketTime", "")
                    
                    if today_str_api in market_time:
                        picupdata = data.get("picupdata", [])
                        found_result = False
                        
                        for item in picupdata:
                            if item[0] == "11:30":
                                found_result = True
                                price_str = str(item[1]).replace(",", "")
                                diff_str = str(item[2]).replace(",", "").replace("+", "").replace("-", "")
                                
                                try:
                                    price_val = f"{float(price_str):.2f}"
                                    diff_val = f"{float(diff_str):.2f}"
                                    
                                    integer_part, decimal_part = price_val.split('.')
                                    top_3 = integer_part[-1] + decimal_part
                                    bottom_2 = diff_val.split('.')[1]
                                    
                                    # 🛡️ ดักจับความถูกต้องของตัวเลข
                                    if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                        msg = (f"🇨🇳 ผลหวยหุ้นจีนเช้า (ปกติ) 🇨🇳\n📅 วันที่: {today_str_display}\n\n"
                                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                        bot.send_message(GROUP_CHAT_ID, msg)
                                        return
                                except ValueError:
                                    pass
                        
                        if not found_result:
                            if not is_auto and attempts >= 2:
                                bot.send_message(GROUP_CHAT_ID, f"⏳ จีนเช้า (ปกติ): ตลาดยังไม่ปิดรอบเช้า (รอระบบอัปเดตตัวเลข 11:30 น.)")
                                return
                    else:
                        if not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {today_str_display} ยังไม่ออกครับ (ข้อมูลในเว็บยังเป็นงวด {market_time[:10]})")
                            return
                else:
                    print(f"[Error] จีนเช้า (ปกติ): ระบบแจ้ง Code {json_data.get('code')}")
            else:
                print(f"[Error] จีนเช้า (ปกติ): ตอบกลับสถานะ {res.status_code}")
                
        except Exception as e:
            print(f"[Error] จีนเช้า (ปกติ) Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ จีนเช้า (ปกติ): ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇱🇦 ดึงผล: ลาวทีวี
# ==========================================
def fetch_lao_tv(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d")
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล ลาวทีวี งวดวันที่ {today_str_display}...")

    url = "https://api.lao-tv.com/result"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    attempts = 0
    while True:
        attempts += 1
        try:
            timestamp = int(datetime.now().timestamp() * 1000)
            res = requests.get(f"{url}?_={timestamp}", headers=headers, timeout=15)
            
            if res.status_code == 200:
                json_data = res.json()
                data = json_data.get("data", {})
                api_date = data.get("lotto_date", "")
                
                if api_date == today_str_api:
                    results = data.get("results", {})
                    digit5 = str(results.get("digit5", "")).strip()
                    
                    # 🛡️ ดักจับความถูกต้อง: ต้องยาว 5 ตัวและเป็นตัวเลขล้วน
                    if len(digit5) == 5 and digit5.isdigit():
                        top_3 = digit5[-3:]
                        bottom_2 = digit5[:2]
                        
                        msg = (f"🇱🇦 ผลหวยลาวทีวี 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return
                    else:
                        if not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⏳ ลาวทีวี: ผลรางวัลกำลังออก (รอตัวเลขครบ 5 ตัว)")
                            return
                else:
                    if not is_auto and attempts >= 2:
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {today_str_display} ยังไม่ออกครับ (หน้าเว็บยังเป็นงวด {api_date})")
                        return
            else:
                 print(f"[Error] ลาวทีวี: ตอบกลับสถานะ {res.status_code}")
                    
        except Exception as e:
            print(f"[Error] ลาวทีวี Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ลาวทีวี: ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇭🇰 ดึงผล: ฮั่งเส็งเช้า VIP
# ==========================================
def fetch_hangseng_morning_vip(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยฮั่งเส็งเช้า VIP งวดวันที่ {today_str_display}...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(datetime.now().timestamp() * 1000)
        
        try:
            if offset_days == 0:
                url = f"https://api.stocks-vip.com/api/hk?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    
                    if json_data.get("status") == "success":
                        data = json_data.get("data", {})
                        api_date = data.get("date", "")
                        
                        if api_date == today_str_api:
                            r1 = data.get("results", {}).get("r1", {})
                            price = str(r1.get("price") or "")
                            diff = str(r1.get("diff") or "")
                            
                            if price and diff:
                                try:
                                    price_str = f"{float(price):.2f}"
                                    diff_str = f"{float(diff):.2f}"
                                    
                                    integer_part, decimal_part = price_str.split('.')
                                    top_3 = integer_part[-1] + decimal_part
                                    bottom_2 = diff_str.replace('-', '').replace('+', '').split('.')[1]
                                    
                                    if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                        msg = (f"🇭🇰 ผลหวยฮั่งเส็งเช้า VIP 🇭🇰\n📅 วันที่: {today_str_display}\n\n"
                                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                        bot.send_message(GROUP_CHAT_ID, msg)
                                        return
                                except ValueError:
                                    pass
                        else:
                            if not is_auto and attempts >= 2:
                                bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {today_str_display} ยังไม่ออกครับ (หน้าเว็บยังเป็นงวด {api_date})")
                                return

            else:
                url = f"https://api.stocks-vip.com/api/history/hk?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    if json_data.get("status") == "success":
                        for item in json_data.get("data", []):
                            if item.get("date") == today_str_api:
                                r1_data = item.get("r1", {})
                                top_3 = str(r1_data.get("prize_1st", "")).strip()
                                bottom_2 = str(r1_data.get("prize_2nd", "")).strip()
                                
                                if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                    msg = (f"🇭🇰 ผลหวยฮั่งเส็งเช้า VIP 🇭🇰\n📅 วันที่: {today_str_display}\n\n"
                                           f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                    bot.send_message(GROUP_CHAT_ID, msg)
                                    return
                                    
        except Exception as e:
            print(f"[Error] ฮั่งเส็งเช้า VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮั่งเส็งเช้า VIP: กำลังรอผลรางวัลอัปเดตเข้าระบบครับ")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇻🇳 ดึงผล: ฮานอยHD
# ==========================================
def fetch_hanoi_hd(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d")
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยฮานอยHD งวดวันที่ {today_str_display}...")

    url = "https://api.xosohd.com/result" 
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    attempts = 0
    while True:
        attempts += 1
        try:
            timestamp = int(datetime.now().timestamp() * 1000)
            res = requests.get(f"{url}?_={timestamp}", headers=headers, timeout=15)
            
            if res.status_code == 200:
                json_data = res.json()
                
                if json_data.get("status") == "success":
                    data = json_data.get("data", {})
                    api_date = data.get("lotto_date", "")
                    
                    if api_date == today_str_api:
                        results = data.get("results", {})
                        prize_1st = str(results.get("prize_1st", "")).strip()
                        prize_2nd = str(results.get("prize_2nd", "")).strip()
                        
                        # 🛡️ ดักจับความถูกต้องด้วย .isdigit()
                        if len(prize_1st) >= 3 and len(prize_2nd) >= 2 and prize_1st.isdigit() and prize_2nd.isdigit():
                            top_3 = prize_1st[-3:]
                            bottom_2 = prize_2nd[-2:]
                            
                            msg = (f"🇻🇳 ผลหวยฮานอยHD 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return
                        else:
                            if not is_auto and attempts >= 2:
                                bot.send_message(GROUP_CHAT_ID, f"⏳ ฮานอยHD: กำลังรอผลรางวัลอัปเดตครับ")
                                return
                    else:
                        if not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {today_str_display} ยังไม่ออกครับ (หน้าเว็บยังเป็นงวด {api_date})")
                            return
                else:
                    print("[Error] ฮานอยHD: สถานะ API ไม่สำเร็จ")
            else:
                 print(f"[Error] ฮานอยHD: ตอบกลับสถานะ {res.status_code}")
                    
        except Exception as e:
            print(f"[Error] ฮานอยHD Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮานอยHD: ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇹🇼 ดึงผล: หุ้นไต้หวัน VIP
# ==========================================
def fetch_taiwan_vip(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยหุ้นไต้หวัน VIP งวดวันที่ {today_str_display}...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(datetime.now().timestamp() * 1000)
        
        try:
            if offset_days == 0:
                url = f"https://api.tsecvipindex.com/api/tw?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    
                    if json_data.get("status") == "success":
                        prices_list = json_data.get("data", {}).get("prices", [])
                        
                        for item in prices_list:
                            if item.get("note") == "Close":
                                price = str(item.get("price") or "0")
                                diff = str(item.get("diff") or "0")
                                
                                try:
                                    price_str = f"{float(price):.2f}"
                                    diff_str = f"{float(diff):.2f}"
                                    
                                    integer_part, decimal_part = price_str.split('.')
                                    top_3 = integer_part[-1] + decimal_part
                                    bottom_2 = diff_str.replace('-', '').replace('+', '').split('.')[1]
                                    
                                    if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                        msg = (f"🇹🇼 ผลหวยหุ้นไต้หวัน VIP 🇹🇼\n📅 วันที่: {today_str_display}\n\n"
                                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                        bot.send_message(GROUP_CHAT_ID, msg)
                                        return
                                except ValueError:
                                    pass

            else:
                url = f"https://api.tsecvipindex.com/api/history/tw?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    if json_data.get("status") == "success":
                        for item in json_data.get("data", []):
                            if item.get("date") == today_str_api:
                                r1_data = item.get("r1", {})
                                top_3 = str(r1_data.get("prize_1st", "")).strip()
                                bottom_2 = str(r1_data.get("prize_2nd", "")).strip()
                                
                                if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                    msg = (f"🇹🇼 ผลหวยหุ้นไต้หวัน VIP 🇹🇼\n📅 วันที่: {today_str_display}\n\n"
                                           f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                    bot.send_message(GROUP_CHAT_ID, msg)
                                    return
                                    
        except Exception as e:
            print(f"[Error] ไต้หวัน VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"⏳ ไต้หวัน VIP: กำลังรอผลรางวัลอัปเดตเข้าระบบครับ")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇻🇳 ดึงผล: ฮานอยสตาร์ (12:30)
# ==========================================
def fetch_hanoi_star(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time

    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d")
    today_str_display = target_date.strftime("%d-%m-%Y")

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยฮานอยสตาร์ งวดวันที่ {today_str_display} ครับ...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }

    attempts = 0
    while True:
        attempts += 1
        # แนบเวลาไปใน URL เพื่อป้องกันเว็บแคชข้อมูลเก่า (แก้ปัญหา Status 304)
        timestamp = int(time.time() * 1000)
        url = f"https://api.minhngocstar.com/result?t={timestamp}" 

        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code in [200, 304]: 
                json_data = res.json()
                
                if json_data.get("status") == "success":
                    data_node = json_data.get("data", {})
                    api_date = str(data_node.get("lotto_date", "")).strip()
                    
                    if api_date == today_str_api:
                        results = data_node.get("results", {})
                        
                        prize_1st = str(results.get("prize_1st") or "").strip()
                        prize_2nd = str(results.get("prize_2nd") or "").strip()
                        
                        if len(prize_1st) >= 3 and len(prize_2nd) >= 2 and prize_1st.isdigit() and prize_2nd.isdigit():
                            top_3 = prize_1st[-3:]
                            bottom_2 = prize_2nd[-2:]
                            
                            msg = (f"🇻🇳 ผลหวยฮานอยสตาร์ 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
                    elif not is_auto and attempts == 1 and api_date != "":
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ ฮานอยสตาร์: ข้อมูลใน API ตอนนี้เป็นของวันที่ {api_date}")
                        return
        except Exception as e:
            print(f"[Error] ฮานอยสตาร์: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮานอยสตาร์: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
            
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง)
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการครับ)")
            return

# ==========================================
# 🇹🇼 ดึงผล: หุ้นไต้หวัน (ปกติ)
# ==========================================
def fetch_taiwan_normal(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time

    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y/%m/%d")
    today_str_display = target_date.strftime("%d-%m-%Y")

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยหุ้นไต้หวัน (ปกติ) งวดวันที่ {today_str_display}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.twse.com.tw/",
        "Accept": "application/json"
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(time.time() * 1000)
        url = f"https://www.twse.com.tw/res/data/zh/home/marquee.json?_={timestamp}"

        try:
            res = requests.get(url, headers=headers, timeout=15)

            if res.status_code == 200:
                data = res.json()
                taiex = data.get("mi", {}).get("taiex", {})
                dt = taiex.get("datetime", "")

                if dt.startswith(today_str_api):
                    time_part = dt.split(" ")[1] if " " in dt else ""

                    if time_part >= "13:33:00":
                        price = str(taiex.get("index", ""))
                        diff = str(taiex.get("diff", ""))

                        if price and diff:
                            try:
                                price_str = f"{float(price):.2f}"
                                diff_str = f"{float(diff):.2f}"

                                integer_part, decimal_part = price_str.split('.')
                                top_3 = integer_part[-1] + decimal_part
                                bottom_2 = diff_str.replace('-', '').replace('+', '').split('.')[1]

                                # 🛡️ ดักจับความถูกต้องด้วย .isdigit()
                                if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                    msg = (f"🇹🇼 ผลหวยหุ้นไต้หวัน (ปกติ) 🇹🇼\n📅 วันที่: {today_str_display}\n\n"
                                           f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                    bot.send_message(GROUP_CHAT_ID, msg)
                                    return
                            except ValueError:
                                pass
                    else:
                        if not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⏳ ไต้หวัน (ปกติ): ตลาดยังไม่ปิด (เวลาเซิร์ฟเวอร์ไต้หวันล่าสุด {time_part} รอผลสรุปตอน 13:33 น.)")
                            return
                else:
                    if not is_auto and attempts >= 2:
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {today_str_display} ยังไม่ออกครับ (ข้อมูลเว็บเป็นของงวด {dt})")
                        return
            else:
                print(f"[Error] ไต้หวัน (ปกติ): ตอบกลับสถานะ {res.status_code}")

        except Exception as e:
            print(f"[Error] ไต้หวัน (ปกติ) Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ไต้หวัน (ปกติ): ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return

        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return
        
# ==========================================
# 🇰🇷 ดึงผล: หุ้นเกาหลี VIP
# ==========================================
def fetch_korea_vip(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยหุ้นเกาหลี VIP งวดวันที่ {today_str_display}...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(datetime.now().timestamp() * 1000)
        
        try:
            if offset_days == 0:
                url = f"https://api.ktopvipindex.com/api/kr?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    
                    if json_data.get("status") == "success":
                        data = json_data.get("data", {})
                        api_date = data.get("date", "")
                        
                        if api_date == today_str_api:
                            prices = data.get("prices", {})
                            
                            if prices.get("note") == "Close":
                                price = str(prices.get("price") or "0")
                                diff = str(prices.get("diff") or "0")
                                
                                try:
                                    price_str = f"{float(price):.2f}"
                                    diff_str = f"{float(diff):.2f}"
                                    
                                    integer_part, decimal_part = price_str.split('.')
                                    top_3 = integer_part[-1] + decimal_part
                                    bottom_2 = diff_str.replace('-', '').replace('+', '').split('.')[1]
                                    
                                    if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                        msg = (f"🇰🇷 ผลหวยหุ้นเกาหลี VIP 🇰🇷\n📅 วันที่: {today_str_display}\n\n"
                                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                        bot.send_message(GROUP_CHAT_ID, msg)
                                        return
                                except ValueError:
                                    pass
                        else:
                            if not is_auto and attempts >= 2:
                                bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {today_str_display} ยังไม่ออกครับ (ข้อมูลเว็บเป็นของงวด {api_date})")
                                return

            else:
                url = f"https://api.ktopvipindex.com/api/history/kr?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    if json_data.get("status") == "success":
                        for item in json_data.get("data", []):
                            if item.get("date") == today_str_api:
                                r1_data = item.get("r1", {})
                                top_3 = str(r1_data.get("prize_1st", "")).strip()
                                bottom_2 = str(r1_data.get("prize_2nd", "")).strip()
                                
                                if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                    msg = (f"🇰🇷 ผลหวยหุ้นเกาหลี VIP 🇰🇷\n📅 วันที่: {today_str_display}\n\n"
                                           f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                    bot.send_message(GROUP_CHAT_ID, msg)
                                    return
                                    
        except Exception as e:
            print(f"[Error] เกาหลี VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"⏳ เกาหลี VIP: กำลังรอผลรางวัลอัปเดตเข้าระบบครับ")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇰🇷 ดึงผล: หุ้นเกาหลี (ปกติ)
# ==========================================
def fetch_korea_normal(offset_days=0, is_auto=True):
    import requests
    from bs4 import BeautifulSoup
    from datetime import datetime, timedelta
    import re
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    thai_months = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
    thai_day = target_date.day
    thai_month = thai_months[target_date.month]
    thai_year = target_date.year + 543
    thai_date_str = f"{thai_day} {thai_month} {thai_year}"
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยหุ้นเกาหลี (ปกติ) งวดวันที่ {today_str_display} ครับ...")

    url = "https://saihuay.com/historical?lotto=korea&lang=th"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    attempts = 0
    start_time = datetime.now(tz)
    
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                table = soup.find("table")
                if table:
                    tbody = table.find("tbody")
                    if tbody:
                        first_row = tbody.find("tr")
                        if first_row:
                            cells = first_row.find_all("td")
                            if len(cells) >= 3:
                                row_date = cells[0].get_text(strip=True)
                                
                                if thai_date_str in row_date:
                                    top3 = cells[1].get_text(strip=True)
                                    bot2 = cells[2].get_text(strip=True)
                                    
                                    if not (re.fullmatch(r"\d+", top3) and re.fullmatch(r"\d+", bot2)):
                                        if not is_auto and attempts >= 2:
                                            bot.send_message(GROUP_CHAT_ID, f"⏳ เกาหลี (ปกติ): ผลรางวัลกำลังออกครับ (รอเว็บอัปเดตตัวเลข)")
                                            return
                                    else:
                                        msg = (f"🇰🇷 ผลหวยหุ้นเกาหลี (ปกติ) 🇰🇷\n📅 วันที่: {today_str_display}\n\n"
                                               f"🎯 3 ตัวบน: {top3}\n👇 2 ตัวล่าง: {bot2}\n")
                                        bot.send_message(GROUP_CHAT_ID, msg)
                                        return
                                else:
                                    if not is_auto and attempts >= 2:
                                        bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {thai_date_str} ยังไม่ออกครับ (หน้าเว็บยังเป็นงวด {row_date})")
                                        return
                                        
        except Exception as e:
            print(f"[Error] เกาหลี (ปกติ) สายหวย Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ เกาหลี (ปกติ): ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        if is_auto and (datetime.now(tz) - start_time).total_seconds() > 10800:
            return  
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇯🇵 ดึงผล: หุ้นนิเคอิ (บ่าย)
# ==========================================
def fetch_nikkei_afternoon(offset_days=0, is_auto=True):
    import requests
    from bs4 import BeautifulSoup
    from datetime import datetime, timedelta
    import re
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    thai_months = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
    thai_day = target_date.day
    thai_month = thai_months[target_date.month]
    thai_year = target_date.year + 543
    thai_date_str = f"{thai_day} {thai_month} {thai_year}"
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยหุ้นนิเคอิ (บ่าย) งวดวันที่ {today_str_display} ครับ...")

    url = "https://saihuay.com/historical?lotto=nikkei_afternoon&lang=th"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    attempts = 0
    start_time = datetime.now(tz)
    
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                table = soup.find("table")
                if table:
                    tbody = table.find("tbody")
                    if tbody:
                        first_row = tbody.find("tr")
                        if first_row:
                            cells = first_row.find_all("td")
                            if len(cells) >= 3:
                                row_date = cells[0].get_text(strip=True)
                                
                                if thai_date_str in row_date:
                                    top3 = cells[1].get_text(strip=True)
                                    bot2 = cells[2].get_text(strip=True)
                                    
                                    if not (re.fullmatch(r"\d+", top3) and re.fullmatch(r"\d+", bot2)):
                                        if not is_auto and attempts >= 2:
                                            bot.send_message(GROUP_CHAT_ID, f"⏳ นิเคอิ (บ่าย): ผลรางวัลกำลังออกครับ (รอเว็บอัปเดตตัวเลข)")
                                            return
                                    else:
                                        msg = (f"🇯🇵 ผลหวยหุ้นนิเคอิ (บ่าย) 🇯🇵\n📅 วันที่: {today_str_display}\n\n"
                                               f"🎯 3 ตัวบน: {top3}\n👇 2 ตัวล่าง: {bot2}\n")
                                        bot.send_message(GROUP_CHAT_ID, msg)
                                        return
                                else:
                                    if not is_auto and attempts >= 2:
                                        bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {thai_date_str} ยังไม่ออกครับ (หน้าเว็บยังเป็นงวด {row_date})")
                                        return
                                        
        except Exception as e:
            print(f"[Error] นิเคอิ (บ่าย) สายหวย Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ นิเคอิ (บ่าย): ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        if is_auto and (datetime.now(tz) - start_time).total_seconds() > 10800:
            return  
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇯🇵 ดึงผล: นิเคอิบ่าย VIP
# ==========================================
def fetch_nikkei_vip_afternoon(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยนิเคอิบ่าย VIP งวดวันที่ {today_str_display}...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(datetime.now().timestamp() * 1000)
        
        try:
            if offset_days == 0:
                url = f"https://api.nikkeivipstock.com/api/jp?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    
                    if json_data.get("status") == "success":
                        prices_list = json_data.get("data", {}).get("prices", [])
                        
                        for item in prices_list:
                            item_time = item.get("time", "")
                            if item.get("note") == "Close" and item_time.startswith("15:"):
                                price = str(item.get("price") or "0")
                                diff = str(item.get("diff") or "0")
                                
                                try:
                                    price_str = f"{float(price):.2f}"
                                    diff_str = f"{float(diff):.2f}"
                                    
                                    integer_part, decimal_part = price_str.split('.')
                                    top_3 = integer_part[-1] + decimal_part
                                    bottom_2 = diff_str.replace('-', '').replace('+', '').split('.')[1]
                                    
                                    if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                        msg = (f"🇯🇵 ผลหวยนิเคอิบ่าย VIP 🇯🇵\n📅 วันที่: {today_str_display}\n\n"
                                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                        bot.send_message(GROUP_CHAT_ID, msg)
                                        return
                                except ValueError:
                                    pass

            else:
                url = f"https://api.nikkeivipstock.com/api/history/jp?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    if json_data.get("status") == "success":
                        for item in json_data.get("data", []):
                            if item.get("date") == today_str_api:
                                r2_data = item.get("r2", {})
                                top_3 = str(r2_data.get("prize_1st", "")).strip()
                                bottom_2 = str(r2_data.get("prize_2nd", "")).strip()
                                
                                if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                    msg = (f"🇯🇵 ผลหวยนิเคอิบ่าย VIP 🇯🇵\n📅 วันที่: {today_str_display}\n\n"
                                           f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                    bot.send_message(GROUP_CHAT_ID, msg)
                                    return
                                    
        except Exception as e:
            print(f"[Error] นิเคอิบ่าย VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"⏳ นิเคอิบ่าย VIP: กำลังรอผลรางวัลอัปเดตเข้าระบบครับ")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return
            
# ==========================================
# 🇱🇦 ดึงผล: หวยลาวHD
# ==========================================
def fetch_laos_hd(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d")
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยลาวHD งวดวันที่ {today_str_display}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(datetime.now().timestamp() * 1000)
        
        try:
            url_main = f"https://api.laoshd.com/api/result?t={timestamp}"
            res_main = requests.get(url_main, headers=headers, timeout=15)
            
            main_matched = False
            
            if res_main.status_code == 200:
                json_data = res_main.json()
                if json_data.get("status") == "success":
                    data = json_data.get("data", {})
                    api_date = data.get("lotto_date", "")
                    
                    if api_date == today_str_api:
                        main_matched = True
                        results = data.get("results", {})
                        digit5 = str(results.get("digit5", "")).strip()
                        digit3 = str(results.get("digit3", "")).strip()
                        digit2_bottom = str(results.get("digit2_bottom", "")).strip()
                        
                        # 🛡️ เช็คความถูกต้องด้วย .isdigit()
                        if len(digit5) == 5 and digit5.isdigit() and digit3.isdigit() and digit2_bottom.isdigit():
                            msg = (f"🇱🇦 ผลหวยลาวHD 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {digit3}\n"
                                   f"👇 2 ตัวล่าง: {digit2_bottom}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return
                        else:
                            if not is_auto and attempts >= 2:
                                bot.send_message(GROUP_CHAT_ID, f"⏳ ลาวHD: กำลังรอผลรางวัลอัปเดตให้ครบถ้วนครับ")
                                return
                                
                    elif offset_days == 0:
                        if not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {today_str_display} ยังไม่ออกครับ (หน้าเว็บยังเป็นงวด {api_date})")
                            return

            if offset_days > 0 and not main_matched:
                url_hist = f"https://api.laoshd.com/api/history?t={timestamp}"
                res_hist = requests.get(url_hist, headers=headers, timeout=15)
                
                if res_hist.status_code == 200:
                    json_data = res_hist.json()
                    if json_data.get("status") == "success":
                        found = False
                        for item in json_data.get("data", []):
                            if item.get("lotto_date") == today_str_api:
                                found = True
                                results = item.get("results", {})
                                digit5 = str(results.get("digit5", "")).strip()
                                digit3 = str(results.get("digit3", "")).strip()
                                digit2_bottom = str(results.get("digit2_bottom", "")).strip()
                                
                                if len(digit5) == 5 and digit5.isdigit() and digit3.isdigit() and digit2_bottom.isdigit():
                                    msg = (f"🇱🇦 ผลหวยลาวHD 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                           f"🎯 3 ตัวบน: {digit3}\n"
                                           f"👇 2 ตัวล่าง: {digit2_bottom}\n")
                                    bot.send_message(GROUP_CHAT_ID, msg)
                                    return
                        
                        if not found and not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⚠️ ไม่พบประวัติผลหวยลาวHD ของวันที่ {today_str_display} ในระบบครับ")
                            return
                                
        except Exception as e:
            print(f"[Error] ลาวHD Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ลาวHD: ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇨🇳 ดึงผล: หุ้นจีน (บ่าย) - Official API (SZSE)
# ==========================================
def fetch_china_afternoon(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time
    import random
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d")
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if offset_days > 0:
        if not is_auto:
            bot.send_message(GROUP_CHAT_ID, "⚠️ จีน (บ่าย): API ของเว็บทางการดึงได้เฉพาะผลของวันล่าสุด ไม่สามารถดึงย้อนหลังได้ครับ")
        return
        
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยหุ้นจีน (บ่าย) งวดวันที่ {today_str_display}...")

    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8",
        "Referer": "https://www.szse.cn/",
        "X-Request-Type": "ajax",
        "X-Requested-With": "XMLHttpRequest"
    }
    session.headers.update(headers)

    attempts = 0
    while True:
        attempts += 1
        try:
            rand_val = random.random()
            url = f"https://www.szse.cn/api/market/ssjjhq/getTimeData?random={rand_val}&marketId=1&code=399001"
            
            res = session.get(url, timeout=15)
            
            if res.status_code == 200:
                try:
                    json_data = res.json()
                except Exception:
                    if not is_auto and attempts >= 2:
                        bot.send_message(GROUP_CHAT_ID, f"❌ จีน (บ่าย): ถูกระบบป้องกันของ SZSE บล็อคครับ")
                        return
                    time.sleep(10)
                    continue

                api_datetime = json_data.get("datetime", "")
                
                if today_str_api in api_datetime:
                    api_time = api_datetime.split(" ")[1] if " " in api_datetime else ""
                    
                    if api_time >= "15:00":
                        data = json_data.get("data", {})
                        now_price = str(data.get("now", "0")).replace(",", "")
                        delta_price = str(data.get("delta", "0")).replace(",", "").replace("+", "").replace("-", "")
                        
                        try:
                            integer_part, decimal_part = f"{float(now_price):.2f}".split('.')
                            top_3 = integer_part[-1] + decimal_part
                            bottom_2 = f"{float(delta_price):.2f}".split('.')[1]
                            
                            # 🛡️ ดักจับความถูกต้องด้วย .isdigit()
                            if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                msg = (f"🇨🇳 ผลหวยหุ้นจีน (บ่าย) 🇨🇳\n📅 วันที่: {today_str_display}\n\n"
                                       f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                bot.send_message(GROUP_CHAT_ID, msg)
                                return
                        except ValueError:
                            pass
                    else:
                        if not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⏳ จีน (บ่าย): ตลาดยังไม่ปิด (สถานะล่าสุด: {api_datetime})")
                            return
                else:
                    if not is_auto and attempts >= 2:
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ จีน (บ่าย): เว็บไซต์ยังไม่อัปเดตข้อมูลของวันที่ {today_str_display} (ล่าสุด: {api_datetime})")
                        return
            else:
                if not is_auto and attempts >= 2:
                    bot.send_message(GROUP_CHAT_ID, f"❌ จีน (บ่าย): เว็บปฏิเสธการเชื่อมต่อ (Status Code: {res.status_code})")
                    return
                    
        except Exception as e:
            print(f"[Error] จีน (บ่าย) Exception: {e}")
            if not is_auto and attempts >= 2:
                bot.send_message(GROUP_CHAT_ID, f"❌ จีน (บ่าย): เซิร์ฟเวอร์เชื่อมต่อไม่สำเร็จ")
                return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇻🇳 ดึงผล: ฮานอยทีวี
# ==========================================
def fetch_hanoi_tv(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time

    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d")
    today_str_display = target_date.strftime("%d-%m-%Y")

    if offset_days > 0:
        if not is_auto:
            bot.send_message(GROUP_CHAT_ID, "⚠️ ฮานอยทีวี: ระบบนี้ดึงได้เฉพาะผลล่าสุด ไม่สามารถดึงย้อนหลังได้ครับ")
        return

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยฮานอยทีวี งวดวันที่ {today_str_display}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(datetime.now().timestamp() * 1000)
        url = f"https://api.minhngoctv.com/result?t={timestamp}"
        
        try:
            res = requests.get(url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                json_data = res.json()
                
                if json_data.get("status") == "success":
                    data = json_data.get("data", {})
                    api_date = data.get("lotto_date", "")
                    
                    if api_date == today_str_api:
                        results = data.get("results", {})
                        
                        prize_1st = str(results.get("prize_1st") or "").strip()
                        prize_2nd = str(results.get("prize_2nd") or "").strip()
                        
                        if len(prize_1st) >= 3 and len(prize_2nd) >= 2 and prize_1st.isdigit() and prize_2nd.isdigit():
                            top_3 = prize_1st[-3:]
                            bottom_2 = prize_2nd[-2:]
                            
                            msg = (f"🇻🇳 ผลหวยฮานอยทีวี 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return
                        else:
                            if not is_auto and attempts >= 2:
                                bot.send_message(GROUP_CHAT_ID, f"⏳ ฮานอยทีวี: กำลังรอผลรางวัลอัปเดตครับ")
                                return
                    else:
                        if not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {today_str_display} ยังไม่ออกครับ (หน้าเว็บยังเป็นงวด {api_date})")
                            return
                else:
                    print(f"[Error] ฮานอยทีวี: สถานะ API ไม่สำเร็จ")
            else:
                print(f"[Error] ฮานอยทีวี: ตอบกลับสถานะ {res.status_code}")
                
        except Exception as e:
            print(f"[Error] ฮานอยทีวี Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮานอยทีวี: ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇨🇳 ดึงผล: จีนบ่าย VIP
# ==========================================
def fetch_china_vip_afternoon(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time

    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยจีนบ่าย VIP งวดวันที่ {today_str_display}...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(datetime.now().timestamp() * 1000)
        
        try:
            if offset_days == 0:
                url = f"https://api.shenzhenindex.com/api/cn?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    
                    if json_data.get("status") == "success":
                        prices_list = json_data.get("data", {}).get("prices", [])
                        
                        for item in prices_list:
                            item_time = item.get("time", "")
                            if item.get("note") == "Close" and item_time.startswith("15:"):
                                price = str(item.get("price") or "0")
                                diff = str(item.get("diff") or "0")
                                
                                try:
                                    price_str = f"{float(price):.2f}"
                                    diff_str = f"{float(diff):.2f}"
                                    
                                    integer_part, decimal_part = price_str.split('.')
                                    top_3 = integer_part[-1] + decimal_part
                                    bottom_2 = diff_str.replace('-', '').replace('+', '').split('.')[1]
                                    
                                    if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                        msg = (f"🇨🇳 ผลหวยจีนบ่าย VIP 🇨🇳\n📅 วันที่: {today_str_display}\n\n"
                                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                        bot.send_message(GROUP_CHAT_ID, msg)
                                        return
                                except ValueError:
                                    pass

            else:
                url = f"https://api.shenzhenindex.com/api/history/cn?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    if json_data.get("status") == "success":
                        for item in json_data.get("data", []):
                            if item.get("date") == today_str_api:
                                r2_data = item.get("r2", {})
                                top_3 = str(r2_data.get("prize_1st", "")).strip()
                                bottom_2 = str(r2_data.get("prize_2nd", "")).strip()
                                
                                if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                    msg = (f"🇨🇳 ผลหวยจีนบ่าย VIP 🇨🇳\n📅 วันที่: {today_str_display}\n\n"
                                           f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                    bot.send_message(GROUP_CHAT_ID, msg)
                                    return
                                    
        except Exception as e:
            print(f"[Error] จีนบ่าย VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"⏳ จีนบ่าย VIP: กำลังรอผลรางวัลอัปเดตเข้าระบบครับ")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇭🇰 ดึงผล: ฮั่งเส็งบ่าย (ปกติ)
# ==========================================
def fetch_hangseng_afternoon_normal(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time

    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d")
    today_str_display = target_date.strftime("%d-%m-%Y")

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยฮั่งเส็งบ่าย (ปกติ) งวดวันที่ {today_str_display}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.hsi.com.hk/",
        "Accept": "application/json"
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(time.time() * 1000)
        url = f"https://www.hsi.com.hk/data/eng/rt/index-series/hsi/performance.do?_={timestamp}"

        try:
            res = requests.get(url, headers=headers, timeout=15)

            if res.status_code == 200:
                data = res.json()
                index_series_list = data.get("indexSeriesList", [])
                
                for series in index_series_list:
                    if series.get("seriesCode") == "hsi":
                        for idx in series.get("indexList", []):
                            if idx.get("indexName") == "Hang Seng Index":
                                last_update = str(idx.get("lastUpdate", ""))
                                
                                if last_update.startswith(today_str_api):
                                    time_part = last_update.split(" ")[1] if " " in last_update else ""
                                    
                                    if time_part >= "16:08:00":
                                        price_str = str(idx.get("indexValue", "")).replace(",", "")
                                        diff_str = str(idx.get("changeValue", "")).replace(",", "")
                                        
                                        try:
                                            price_val = f"{float(price_str):.2f}"
                                            diff_val = f"{float(diff_str):.2f}"
                                            
                                            integer_part, decimal_part = price_val.split('.')
                                            top_3 = integer_part[-1] + decimal_part
                                            bottom_2 = diff_str.replace('-', '').replace('+', '').split('.')[1]
                                            
                                            if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                                msg = (f"🇭🇰 ผลหวยฮั่งเส็งบ่าย (ปกติ) 🇭🇰\n📅 วันที่: {today_str_display}\n\n"
                                                       f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                                bot.send_message(GROUP_CHAT_ID, msg)
                                                return
                                        except ValueError:
                                            pass
                                    else:
                                        if not is_auto and attempts >= 2:
                                            bot.send_message(GROUP_CHAT_ID, f"⏳ ฮั่งเส็งบ่าย (ปกติ): ตลาดยังไม่ปิดสนิท (เวลาล่าสุด {time_part})")
                                            return
                                else:
                                    if not is_auto and attempts >= 2:
                                        bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {today_str_display} ยังไม่ออกครับ (ข้อมูลเว็บเป็นของงวด {last_update})")
                                        return
            else:
                print(f"[Error] ฮั่งเส็งบ่าย (ปกติ): ตอบกลับสถานะ {res.status_code}")
                
        except Exception as e:
            print(f"[Error] ฮั่งเส็งบ่าย (ปกติ) Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮั่งเส็งบ่าย (ปกติ): ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇭🇰 ดึงผล: ฮั่งเส็งบ่าย VIP
# ==========================================
def fetch_hangseng_vip_afternoon(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time

    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยฮั่งเส็งบ่าย VIP งวดวันที่ {today_str_display}...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(datetime.now().timestamp() * 1000)
        
        try:
            if offset_days == 0:
                url = f"https://api.stocks-vip.com/api/hk?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    
                    if json_data.get("status") == "success":
                        prices_data = json_data.get("data", {}).get("prices", {})
                        
                        item_time = prices_data.get("time", "")
                        item_note = prices_data.get("note", "")
                        
                        if item_note == "Close" and item_time >= "16:00":
                            price = str(prices_data.get("price") or "0")
                            diff = str(prices_data.get("diff") or "0")
                            
                            price_val = price.replace(",", "")
                            diff_val = diff.replace(",", "").replace("+", "").replace("-", "")
                            
                            try:
                                price_str = f"{float(price_val):.2f}"
                                diff_str = f"{float(diff_val):.2f}"
                                
                                integer_part, decimal_part = price_str.split('.')
                                top_3 = integer_part[-1] + decimal_part
                                bottom_2 = diff_str.split('.')[1]
                                
                                if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                    msg = (f"🇭🇰 ผลหวยฮั่งเส็งบ่าย VIP 🇭🇰\n📅 วันที่: {today_str_display}\n\n"
                                           f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                    bot.send_message(GROUP_CHAT_ID, msg)
                                    return
                            except ValueError:
                                pass 

            else:
                url = f"https://api.stocks-vip.com/api/history/hk?t={timestamp}"
                res = requests.get(url, headers=headers, timeout=15)
                
                if res.status_code == 200:
                    json_data = res.json()
                    if json_data.get("status") == "success":
                        for item in json_data.get("data", []):
                            if item.get("date") == today_str_api:
                                r2_data = item.get("results", {}).get("r2", {})
                                
                                price = str(r2_data.get("price") or "0")
                                diff = str(r2_data.get("diff") or "0")
                                
                                price_val = price.replace(",", "")
                                diff_val = diff.replace(",", "").replace("+", "").replace("-", "")
                                
                                try:
                                    price_str = f"{float(price_val):.2f}"
                                    diff_str = f"{float(diff_val):.2f}"
                                    
                                    integer_part, decimal_part = price_str.split('.')
                                    top_3 = integer_part[-1] + decimal_part
                                    bottom_2 = diff_str.split('.')[1]
                                    
                                    if len(top_3) == 3 and len(bottom_2) == 2 and top_3.isdigit() and bottom_2.isdigit():
                                        msg = (f"🇭🇰 ผลหวยฮั่งเส็งบ่าย VIP 🇭🇰\n📅 วันที่: {today_str_display}\n\n"
                                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                                        bot.send_message(GROUP_CHAT_ID, msg)
                                        return
                                except ValueError:
                                    pass
                                    
        except Exception as e:
            print(f"[Error] ฮั่งเส็งบ่าย VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"⏳ ฮั่งเส็งบ่าย VIP: กำลังรอผลรางวัลอัปเดตเข้าระบบครับ")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇱🇦 ดึงผล: หวยลาวสตาร์
# ==========================================
def fetch_laos_star(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d")
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยลาวสตาร์ งวดวันที่ {today_str_display}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(datetime.now().timestamp() * 1000)
        
        try:
            url_main = f"https://api.laostars.com/result?t={timestamp}"
            res_main = requests.get(url_main, headers=headers, timeout=15)
            
            main_matched = False
            
            if res_main.status_code == 200:
                json_data = res_main.json()
                if json_data.get("status") == "success":
                    data = json_data.get("data", {})
                    api_date = data.get("lotto_date", "")
                    
                    if api_date == today_str_api:
                        main_matched = True
                        results = data.get("results", {})
                        
                        digit5 = str(results.get("digit5") or "").strip()
                        digit3 = str(results.get("digit3") or "").strip()
                        digit2_bottom = str(results.get("digit2_bottom") or "").strip()
                        
                        if len(digit5) == 5 and digit5.isdigit() and digit3.isdigit() and digit2_bottom.isdigit():
                            msg = (f"🇱🇦 ผลหวยลาวสตาร์ 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {digit3}\n"
                                   f"👇 2 ตัวล่าง: {digit2_bottom}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return
                        else:
                            if not is_auto and attempts >= 2:
                                bot.send_message(GROUP_CHAT_ID, f"⏳ ลาวสตาร์: กำลังรอผลรางวัลอัปเดตให้ครบถ้วนครับ")
                                return
                                
                    elif offset_days == 0:
                        if not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {today_str_display} ยังไม่ออกครับ (หน้าเว็บยังเป็นงวด {api_date})")
                            return

            if offset_days > 0 and not main_matched:
                url_hist = f"https://api.laostars.com/history?t={timestamp}"
                res_hist = requests.get(url_hist, headers=headers, timeout=15)
                
                if res_hist.status_code == 200:
                    json_data = res_hist.json()
                    if json_data.get("status") == "success":
                        found = False
                        for item in json_data.get("data", []):
                            if item.get("lotto_date") == today_str_api:
                                found = True
                                results = item.get("results", {})
                                
                                digit5 = str(results.get("digit5") or "").strip()
                                digit3 = str(results.get("digit3") or "").strip()
                                digit2_bottom = str(results.get("digit2_bottom") or "").strip()
                                
                                if len(digit5) == 5 and digit5.isdigit() and digit3.isdigit() and digit2_bottom.isdigit():
                                    msg = (f"🇱🇦 ผลหวยลาวสตาร์ 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                           f"🎯 3 ตัวบน: {digit3}\n"
                                           f"👇 2 ตัวล่าง: {digit2_bottom}\n")
                                    bot.send_message(GROUP_CHAT_ID, msg)
                                    return
                        
                        if not found and not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⚠️ ไม่พบประวัติผลหวยลาวสตาร์ ของวันที่ {today_str_display} ในระบบครับ")
                            return
                                
        except Exception as e:
            print(f"[Error] ลาวสตาร์ Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ลาวสตาร์: ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇻🇳 ดึงผล: ฮานอยกาชาด
# ==========================================
def fetch_hanoi_redcross(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time

    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d")
    today_str_display = target_date.strftime("%d-%m-%Y")

    if offset_days > 0:
        if not is_auto:
            bot.send_message(GROUP_CHAT_ID, "⚠️ ฮานอยกาชาด: ระบบนี้ดึงได้เฉพาะผลล่าสุด ไม่สามารถดึงย้อนหลังได้ครับ")
        return

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยฮานอยกาชาด งวดวันที่ {today_str_display}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    attempts = 0
    while True:
        attempts += 1
        timestamp = int(datetime.now().timestamp() * 1000)
        url = f"https://api.xosoredcross.com/result?t={timestamp}"
        
        try:
            res = requests.get(url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                json_data = res.json()
                
                if json_data.get("status") == "success":
                    data = json_data.get("data", {})
                    api_date = data.get("lotto_date", "")
                    
                    if api_date == today_str_api:
                        results = data.get("results", {})
                        
                        prize_1st = str(results.get("prize_1st") or "").strip()
                        prize_2nd = str(results.get("prize_2nd") or "").strip()
                        
                        if len(prize_1st) >= 3 and len(prize_2nd) >= 2 and prize_1st.isdigit() and prize_2nd.isdigit():
                            top_3 = prize_1st[-3:]
                            bottom_2 = prize_2nd[-2:]
                            
                            msg = (f"🇻🇳 ผลหวยฮานอยกาชาด 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return
                        else:
                            if not is_auto and attempts >= 2:
                                bot.send_message(GROUP_CHAT_ID, f"⏳ ฮานอยกาชาด: กำลังรอผลรางวัลอัปเดตครับ")
                                return
                    else:
                        if not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {today_str_display} ยังไม่ออกครับ (หน้าเว็บยังเป็นงวด {api_date})")
                            return
                else:
                    print(f"[Error] ฮานอยกาชาด: สถานะ API ไม่สำเร็จ")
            else:
                print(f"[Error] ฮานอยกาชาด: ตอบกลับสถานะ {res.status_code}")
                
        except Exception as e:
            print(f"[Error] ฮานอยกาชาด Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮานอยกาชาด: ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🎰 2.1 ดึงผล: ฮานอยพิเศษ (17:30)
# ==========================================
def fetch_hanoi_special(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str = target_date.strftime("%d-%m-%Y")
    url = "https://www.xsthm.com/result"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยฮานอยพิเศษ งวดวันที่ {today_str} ครับ...")

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
                        # 🐞 ดักค่าว่าง
                        prize_1 = str(numbers[0] or "").strip()
                        prize_special = str(numbers[-1] or "").strip()
                        
                        # 🛡️ เช็คความยาวและต้องเป็นตัวเลขล้วน
                        if len(prize_special) >= 3 and len(prize_1) >= 2 and prize_special.isdigit() and prize_1.isdigit():
                            top_3 = prize_special[-3:] 
                            bottom_2 = prize_1[-2:]    
                            
                            msg = (f"🇻🇳 ผลหวยฮานอยพิเศษ 🇻🇳\n📅 วันที่: {api_date}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
        except Exception as e:
            print(f"[Error] ฮานอยพิเศษ: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮานอยพิเศษ: ไม่พบข้อมูลวันที่ {today_str}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇸🇬 ดึงผลหวยหุ้นสิงคโปร์ VIP
# ==========================================
def fetch_singapore_vip_fast(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล หวยหุ้นสิงคโปร์ VIP งวดวันที่ {today_str_display} ครับ...")

    base_url = "https://api.stocks-vip.com/api/sg"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    try:
        timestamp = int(datetime.now().timestamp() * 1000)
        url = f"{base_url}?t={timestamp}"
        
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            raw_data = res.json()
            
            if raw_data.get("status") == "success":
                prices_list = raw_data.get("data", {}).get("prices", [])
                
                if prices_list and len(prices_list) > 0:
                    latest_data = prices_list[-1]
                    
                    price = latest_data.get("price", 0)
                    diff = latest_data.get("diff", "0")
                    
                    price_str = f"{float(price):.2f}"
                    diff_str = f"{float(diff):.2f}"
                    
                    integer_part, decimal_part = price_str.split('.')
                    top_3 = integer_part[-1] + decimal_part 
                    bottom_2 = diff_str.replace('-', '').split('.')[1] 
                    
                    msg = (f"🇸🇬 ผลหวยหุ้นสิงคโปร์ VIP 🇸🇬\n📅 วันที่: {today_str_display}\n\n"
                           f"📊 SGX VIP: {price_str} ({float(diff):+.2f})\n\n"
                           f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                    bot.send_message(GROUP_CHAT_ID, msg)
                    return
    except Exception as e:
        print(f"[Error] หวยหุ้นสิงคโปร์ VIP: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ หวยหุ้นสิงคโปร์ VIP: ไม่สามารถดึงข้อมูลได้ในขณะนี้")

# ==========================================
# 🇪🇬 ดึงผลหวยหุ้นอียิปต์
# ==========================================
def fetch_egypt_stock_fast(offset_days=0, is_auto=True):
    import requests
    from bs4 import BeautifulSoup
    from datetime import datetime, timedelta
    import re
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    thai_months = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
    thai_day = target_date.day
    thai_month = thai_months[target_date.month]
    thai_year = target_date.year + 543
    thai_date_str = f"{thai_day} {thai_month} {thai_year}"
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยหุ้นอียิปต์ งวดวันที่ {today_str_display} ครับ...")

    url = "https://saihuay.com/historical?lotto=egypt&lang=th"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                top3, bot2 = None, None
                
                table = soup.find("table")
                if table:
                    tbody = table.find("tbody")
                    if tbody:
                        first_row = tbody.find("tr")
                        if first_row:
                            cells = first_row.find_all("td")
                            if len(cells) >= 3:
                                row_date = cells[0].get_text(strip=True)
                                
                                if thai_date_str in row_date:
                                    top3 = cells[1].get_text(strip=True)
                                    bot2 = cells[2].get_text(strip=True)
                                    
                                    if top3 == "" or bot2 == "":
                                        if not is_auto and attempts >= 2:
                                            bot.send_message(GROUP_CHAT_ID, f"⏳ หวยหุ้นอียิปต์: งวดวันที่ {thai_date_str} กำลังรอออกรางวัลครับ (หน้าเว็บกำลังโหลด)")
                                            return
                                            
                                    elif "pending" not in top3.lower() and "pending" not in bot2.lower():
                                        if re.fullmatch(r"\d+", top3) and re.fullmatch(r"\d+", bot2):
                                            msg = (f"🇪🇬 ผลหวยหุ้นอียิปต์ 🇪🇬\n📅 วันที่: {today_str_display}\n\n"
                                                   f"🎯 3 ตัวบน: {top3}\n👇 2 ตัวล่าง: {bot2}\n")
                                            bot.send_message(GROUP_CHAT_ID, msg)
                                            return
                                        else:
                                            if not is_auto:
                                                bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลล่าสุดที่พบยังไม่ใช่ตัวเลขที่สมบูรณ์ (บน: {top3}, ล่าง: {bot2})")
                                            return
                                else:
                                    if not is_auto and attempts >= 2:
                                        bot.send_message(GROUP_CHAT_ID, f"⚠️ ผลของวันที่ {thai_date_str} ยังไม่ออกครับ (หน้าเว็บยังเป็นงวด {row_date})")
                                        return
                                        
        except Exception as e:
            print(f"[Error] Saihuay (Egypt) Exception: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ หวยหุ้นอียิปต์: ไม่สามารถดึงข้อมูลได้ในขณะนี้")
            return
            
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇮🇳 IN ดึงผลหวยหุ้นอินเดีย
# ==========================================
def fetch_india_stock_fast(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล หวยหุ้นอินเดีย งวดวันที่ {today_str_display} ครับ...")

    url = "https://api.bseindia.com/BseIndiaAPI/api/IndexMovers/w"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.bseindia.com/" 
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        
        if res.status_code == 200:
            data = res.json()
            table_data = data.get("Table", [])
            
            if table_data and len(table_data) > 0:
                sensex_data = next((item for item in table_data if item.get("indexName") == "BSE SENSEX"), None)
                
                if sensex_data:
                    current_price = float(sensex_data.get("LTP", 0))
                    change_val = float(sensex_data.get("change", 0))
                    
                    price_formatted = f"{current_price:.2f}"
                    change_formatted = f"{change_val:.2f}"
                    
                    integer_part, decimal_part = price_formatted.split('.')
                    top_3 = integer_part[-1] + decimal_part
                    bottom_2 = change_formatted.replace('-', '').split('.')[1]
                    
                    msg = (f"🇮🇳 ผลหวยหุ้นอินเดีย 🇮🇳\n📅 วันที่: {today_str_display}\n\n"
                           f"📊 BSE SENSEX: {price_formatted} ({change_val:+.2f})\n\n"
                           f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                    bot.send_message(GROUP_CHAT_ID, msg)
                    return
                else:
                    print("[Error] BSE India: ไม่พบ indexName 'BSE SENSEX'")
    except Exception as e:
        print(f"[Error] BSE India Exception: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ หวยหุ้นอินเดีย: ไม่สามารถดึงข้อมูลจาก API ได้ในขณะนี้")

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
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยฮานอยสามัคคี งวดวันที่ {today_str_display} ครับ...")

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
                        # 🐞 ดักค่าว่าง
                        prize_special = str(results_node.get("prize_1st") or "").strip()
                        prize_1 = str(results_node.get("prize_2nd") or "").strip()
                        
                        # 🛡️ เช็คความยาวและต้องเป็นตัวเลขล้วน
                        if len(prize_special) >= 3 and len(prize_1) >= 2 and prize_special.isdigit() and prize_1.isdigit():
                            top_3 = prize_special[-3:] 
                            bottom_2 = prize_1[-2:]    
                            msg = (f"🇻🇳 ผลหวยฮานอยสามัคคี 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
        except Exception as e:
            print(f"[Error] ฮานอยสามัคคี: {e}")
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮานอยสามัคคี: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇻🇳 ดึงผล: ฮานอยปกติ (18:30)
# ==========================================
def fetch_hanoi_normal(offset_days=0, is_auto=True):
    import requests
    from bs4 import BeautifulSoup
    from datetime import datetime, timedelta
    import time
    
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    today_str_html = target_date.strftime("%d/%m/%Y") 
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล หวยฮานอยปกติ งวดวันที่ {today_str_display} ครับ...")

    url = "https://www.minhngoc.net.vn/xo-so-mien-bac.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    }

    attempts = 0
    max_attempts = 30

    while attempts < max_attempts:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')

            page_title = soup.find('h1', class_='pagetitle')
            box_title = soup.find('div', class_='title')
            
            is_correct_date = False
            if page_title and today_str_html in page_title.text:
                is_correct_date = True
            elif box_title and today_str_html in box_title.text:
                is_correct_date = True

            if is_correct_date:
                prize_special = soup.find('td', class_='giaidb')
                prize_1 = soup.find('td', class_='giai1')

                if prize_special and prize_1:
                    text_db = str(prize_special.text).replace(" ", "").replace("-", "").strip()
                    text_1 = str(prize_1.text).replace(" ", "").replace("-", "").strip()

                    # 🛡️ มี isdigit อยู่แล้ว
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
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮานอยปกติ: ไม่พบข้อมูลวันที่ {today_str_display} หรือผลยังไม่ออก")
            return
            
        time.sleep(10)

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏰ ฮานอยปกติ: ดึงข้อมูลนานเกินเวลาที่กำหนด กรุณากดเช็คด้วยตัวเองอีกครั้งผ่าน /test_normal")
        
# ==========================================
# 🎰 2.4 ดึงผล: ฮานอย VIP (19:30)
# ==========================================
def fetch_hanoi_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str = target_date.strftime("%d-%m-%Y")
    url = "https://www.mlnhngoc.net/mlnhngoc"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยฮานอย VIP งวดวันที่ {today_str} ครับ...")

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
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮานอย VIP: ไม่พบข้อมูลวันที่ {today_str}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

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
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยฮานอยพัฒนา งวดวันที่ {today_str_display} ครับ...")

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
                        # 🐞 ดักค่าว่าง
                        prize_special = str(results_node.get("prize_1st") or "").strip()
                        prize_1 = str(results_node.get("prize_2nd") or "").strip()
                        
                        # 🛡️ เช็คความยาวและตัวเลข
                        if len(prize_special) >= 3 and len(prize_1) >= 2 and prize_special.isdigit() and prize_1.isdigit():
                            top_3 = prize_special[-3:] 
                            bottom_2 = prize_1[-2:]    
                            msg = (f"🇻🇳 ผลหวยฮานอยพัฒนา 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
        except Exception as e:
            print(f"[Error] ฮานอยพัฒนา: {e}")
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮานอยพัฒนา: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

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
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยลาวสามัคคี งวดวันที่ {today_str_display} ครับ...")

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
                        # 🐞 ดักค่าว่าง
                        digit4 = str(results_node.get("digit4") or "").strip()
                        
                        # 🛡️ เช็คความยาวและตัวเลข
                        if len(digit4) == 4 and digit4.isdigit():
                            top_3 = digit4[-3:]  
                            bottom_2 = digit4[:2]  
                            msg = (f"🇱🇦 ผลหวยลาวสามัคคี 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
        except Exception as e:
            print(f"[Error] ลาวสามัคคี: {e}")
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ลาวสามัคคี: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

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
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยลาวอาเซียน งวดวันที่ {today_str_display} ครับ...")

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
                    # 🐞 ดักค่าว่าง
                    digit5 = str(results_node.get("digit5") or "").strip()
                    
                    # 🛡️ เช็คความยาวและตัวเลข
                    if len(digit5) == 5 and digit5.isdigit():
                        top_3 = digit5[-3:]  
                        bottom_2 = digit5[:2]  
                        msg = (f"🇱🇦 ผลหวยลาวอาเซียน 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return 
        except Exception as e:
            print(f"[Error] ลาวอาเซียน: {e}")
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ลาวอาเซียน: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

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
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยลาว VIP งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code in [200, 304]: 
                data = res.json()
                api_date = str(data.get("date", "")).strip()
                
                if api_date == today_str_api:
                    # 🐞 ดักค่าว่าง
                    l1 = str(data.get("lotto_1") or "").strip()
                    l2 = str(data.get("lotto_2") or "").strip()
                    l3 = str(data.get("lotto_3") or "").strip()
                    l4 = str(data.get("lotto_4") or "").strip()
                    
                    if l1 and l2 and l3 and l4:
                        digit4 = l1 + l2 + l3 + l4
                        
                        # 🛡️ เช็คตัวเลข
                        if len(digit4) == 4 and digit4.isdigit():
                            top_3 = digit4[-3:]  
                            bottom_2 = digit4[:2] 
                            
                            msg = (f"🇱🇦 ผลหวยลาว VIP 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
        except Exception as e:
            print(f"[Error] ลาว VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ลาว VIP: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🎰 2.9 ดึงผล: ลาวสามัคคี VIP (21:30)
# ==========================================
def fetch_lao_samakkhi_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    url = "https://api.laounionvip.com/result"
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
    }

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยลาวสามัคคี VIP งวดวันที่ {today_str_display} ครับ...")

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
            bot.send_message(GROUP_CHAT_ID, f"❌ ลาวสามัคคี VIP: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🎰 2.10 ดึงผล: ลาวสตาร์ VIP (22:00)
# ==========================================
def fetch_lao_star_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    url = "https://api.laostars-vip.com/result"
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
    }

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยลาวสตาร์ VIP งวดวันที่ {today_str_display} ครับ...")

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
            bot.send_message(GROUP_CHAT_ID, f"❌ ลาวสตาร์ VIP: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🎰 2.11 ดึงผล: อังกฤษ VIP (21:50)
# ==========================================
def fetch_england_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    url = f"https://gcp.lottosuperrich.com/result?date={today_str_api}"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยอังกฤษ VIP งวดวันที่ {today_str_display} ครับ...")

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
                        p1 = str(results.get("prize_1st") or "").strip()
                        p2 = str(results.get("prize_2nd") or "").strip()
                        
                        if len(p1) >= 3 and len(p2) >= 2 and p1.isdigit() and p2.isdigit():
                            msg = (f"🇬🇧 ผลหวยอังกฤษ VIP 🇬🇧\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {p1[-3:]}\n👇 2 ตัวล่าง: {p2[-2:]}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
                    elif not is_auto and attempts == 1 and api_date != "":
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ อังกฤษ VIP: ข้อมูลใน API ตอนนี้เป็นของวันที่ {api_date}")
                        return
        except Exception as e:
            print(f"[Error] อังกฤษ VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ อังกฤษ VIP: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🎰 2.12 ดึงผล: เยอรมัน VIP (22:50)
# ==========================================
def fetch_germany_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    url = f"https://gcp.lottosuperrich.com/result?date={today_str_api}"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยเยอรมัน VIP งวดวันที่ {today_str_display} ครับ...")

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
                        p1 = str(results.get("prize_1st") or "").strip()
                        p2 = str(results.get("prize_2nd") or "").strip()
                        
                        if len(p1) >= 3 and len(p2) >= 2 and p1.isdigit() and p2.isdigit():
                            msg = (f"🇩🇪 ผลหวยเยอรมัน VIP 🇩🇪\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {p1[-3:]}\n👇 2 ตัวล่าง: {p2[-2:]}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
                    elif not is_auto and attempts == 1 and api_date != "":
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ เยอรมัน VIP: ข้อมูลใน API ตอนนี้เป็นของวันที่ {api_date}")
                        return
        except Exception as e:
            print(f"[Error] เยอรมัน VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ เยอรมัน VIP: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🎰 2.13 ดึงผล: รัสเซีย VIP (23:50)
# ==========================================
def fetch_russia_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    url = f"https://gcp.lottosuperrich.com/result?date={today_str_api}"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยรัสเซีย VIP งวดวันที่ {today_str_display} ครับ...")

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
                        p1 = str(results.get("prize_1st") or "").strip()
                        p2 = str(results.get("prize_2nd") or "").strip()
                        
                        if len(p1) >= 3 and len(p2) >= 2 and p1.isdigit() and p2.isdigit():
                            msg = (f"🇷🇺 ผลหวยรัสเซีย VIP 🇷🇺\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {p1[-3:]}\n👇 2 ตัวล่าง: {p2[-2:]}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
                    elif not is_auto and attempts == 1 and api_date != "":
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ รัสเซีย VIP: ข้อมูลใน API ตอนนี้เป็นของวันที่ {api_date}")
                        return
        except Exception as e:
            print(f"[Error] รัสเซีย VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ รัสเซีย VIP: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
       # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🎰 2.14 ดึงผล: ฮานอย EXTRA (22:30)
# ==========================================
def fetch_hanoi_extra(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    url = f"https://api.xosoextra.com/result?date={today_str_api}"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยฮานอย EXTRA งวดวันที่ {today_str_display} ครับ...")

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
                        prize_1st = str(results.get("prize_1st") or "").strip()
                        prize_2digits = str(results.get("prize_2nd") or "").strip()
                        
                        if len(prize_1st) >= 3 and len(prize_2digits) >= 2 and prize_1st.isdigit() and prize_2digits.isdigit():
                            top_3 = prize_1st[-3:]
                            bottom_2 = prize_2digits[-2:]
                            
                            msg = (f"🇻🇳 ผลหวยฮานอย EXTRA 🇻🇳\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
                    elif not is_auto and attempts == 1 and api_date != "":
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ ฮานอย EXTRA: ข้อมูลใน API ตอนนี้เป็นของวันที่ {api_date}")
                        return
        except Exception as e:
            print(f"[Error] ฮานอย EXTRA: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ฮานอย EXTRA: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🎰 2.15 ดึงผล: ลาวกาชาด (23:30)
# ==========================================
def fetch_lao_redcross(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_api = target_date.strftime("%Y-%m-%d") 
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    url = f"https://api.lao-redcross.com/result?date={today_str_api}"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยลาวกาชาด งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                
                data_node = json_data.get("data") if "data" in json_data else json_data
                api_date = str(data_node.get("lotto_date", "")).strip()
                
                if api_date == today_str_api:
                    results = data_node.get("results", {})
                    digit5 = str(results.get("digit5") or "").strip()
                    
                    if len(digit5) == 5 and digit5.isdigit():
                        top_3 = digit5[-3:]
                        bottom_2 = digit5[:2]
                        
                        msg = (f"🇱🇦 ผลหวยลาวกาชาด 🇱🇦\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return 
                elif not is_auto and attempts == 1 and api_date != "":
                    bot.send_message(GROUP_CHAT_ID, f"⚠️ ลาวกาชาด: ข้อมูลใน API ตอนนี้เป็นของวันที่ {api_date}")
                    return
        except Exception as e:
            print(f"[Error] ลาวกาชาด: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ลาวกาชาด: ไม่พบข้อมูลวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🎰 2.16 ดึงผล: ดาวโจนส์ VIP (00:30)
# ==========================================
def fetch_dowjones_vip(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    draw_date = target_date - timedelta(days=1)
    draw_str_api = draw_date.strftime("%Y-%m-%d")
    
    url = f"https://api.dowjonespowerball.com/result?draw={draw_str_api}"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หวยดาวโจนส์ VIP งวดวันที่ {today_str_display} ครับ...")

    attempts = 0
    while True:
        attempts += 1
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                
                if json_data.get("status") == "success":
                    data_node = json_data.get("data", {})
                    api_lotto_date = str(data_node.get("lotto_date", "")).strip()
                    
                    if api_lotto_date == draw_str_api:
                        results = data_node.get("results", {})
                        p1 = str(results.get("prize_1st") or "").strip()
                        p2 = str(results.get("prize_2nd") or "").strip()
                        
                        if len(p1) >= 3 and len(p2) >= 2 and p1.isdigit() and p2.isdigit():
                            top_3 = p1[-3:]
                            bottom_2 = p2[-2:]
                            
                            msg = (f"🇺🇸 ผลหวยดาวโจนส์ VIP 🇺🇸\n📅 วันที่: {today_str_display}\n\n"
                                   f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                            bot.send_message(GROUP_CHAT_ID, msg)
                            return 
                    elif not is_auto and attempts == 1 and api_lotto_date != "":
                        bot.send_message(GROUP_CHAT_ID, f"⚠️ ดาวโจนส์ VIP: ข้อมูลใน API ตอนนี้เป็นงวด {api_lotto_date}")
                        return
        except Exception as e:
            print(f"[Error] ดาวโจนส์ VIP: {e}")
            
        if not is_auto and attempts >= 2:
            bot.send_message(GROUP_CHAT_ID, f"❌ ดาวโจนส์ VIP: ไม่พบข้อมูลงวดวันที่ {today_str_display}")
            return
        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇸🇬 ดึงผลหวยหุ้นสิงคโปร์ (ปกติ)
# ==========================================
def fetch_singapore_fast(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล หวยหุ้นสิงคโปร์ งวดวันที่ {today_str_display} ครับ...")

    url = "https://api.sgx.com/indices/v1.0/pid/.STI/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            data_list = data.get("data", [])
            
            if data_list and len(data_list) > 0:
                latest_data = data_list[0]
                
                current_price = latest_data.get("lp", 0)
                change = latest_data.get("c", 0)
                
                price_str = f"{float(current_price):.2f}"
                change_str = f"{float(change):.2f}"
                
                integer_part, decimal_part = price_str.split('.')
                top_3 = integer_part[-1] + decimal_part 
                bottom_2 = change_str.replace('-', '').split('.')[1] 
                
                msg = (f"🇸🇬 ผลหวยหุ้นสิงคโปร์ 🇸🇬\n📅 วันที่: {today_str_display}\n\n"
                       f"📊 STI: {price_str} ({float(change):+.2f})\n\n"
                       f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                bot.send_message(GROUP_CHAT_ID, msg)
                return
    except Exception as e:
        print(f"[Error] หวยหุ้นสิงคโปร์: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ หวยหุ้นสิงคโปร์: ไม่สามารถดึงข้อมูลได้ในขณะนี้")

# ==========================================
# 🇹🇭 ดึงผล: หุ้นไทยเย็น
# ==========================================
def fetch_thai_evening_fast(offset_days=0, is_auto=True):
    import requests
    from datetime import datetime, timedelta
    import time

    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if offset_days > 0:
        if not is_auto:
            bot.send_message(GROUP_CHAT_ID, "⚠️ หุ้นไทยเย็น: ระบบนี้ดึงได้เฉพาะผลล่าสุด ไม่สามารถดึงย้อนหลังได้ครับ")
        return

    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มรอผล หุ้นไทยเย็น งวดวันที่ {today_str_display}...")

    url_set = "https://query1.finance.yahoo.com/v8/finance/chart/^SET.BK?interval=1d&range=1d"
    url_set50 = "https://query1.finance.yahoo.com/v8/finance/chart/^SET50.BK?interval=1d&range=1d"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    attempts = 0
    while True:
        attempts += 1
        try:
            timestamp = int(time.time() * 1000)
            res_set = requests.get(f"{url_set}&_={timestamp}", headers=headers, timeout=15)
            res_set50 = requests.get(f"{url_set50}&_={timestamp}", headers=headers, timeout=15)

            if res_set.status_code == 200 and res_set50.status_code == 200:
                data_set = res_set.json()
                data_set50 = res_set50.json()

                meta_set = data_set.get("chart", {}).get("result", [{}])[0].get("meta", {})
                meta_set50 = data_set50.get("chart", {}).get("result", [{}])[0].get("meta", {})

                if meta_set and meta_set50:
                    reg_time_set = meta_set.get("regularMarketTime", 0)
                    reg_time_set50 = meta_set50.get("regularMarketTime", 0)

                    dt_set = datetime.fromtimestamp(reg_time_set, tz)
                    dt_set50 = datetime.fromtimestamp(reg_time_set50, tz)

                    is_today = (dt_set.date() == target_date.date())
                    is_closed = (dt_set.hour == 16 and dt_set.minute >= 35) or (dt_set.hour >= 17)

                    if is_today and is_closed:
                        set_last = meta_set.get("regularMarketPrice", 0)
                        set_prev = meta_set.get("chartPreviousClose", 0)
                        set_change = set_last - set_prev

                        set50_last = meta_set50.get("regularMarketPrice", 0)

                        set_last_str = f"{set_last:.2f}"
                        set_change_str = f"{set_change:.2f}"
                        set50_last_str = f"{set50_last:.2f}"

                        set50_last_digit = set50_last_str[-1]
                        set_decimals = set_last_str.split('.')[1]
                        top_3 = set50_last_digit + set_decimals

                        bottom_2 = set_change_str.replace('-', '').replace('+', '').split('.')[1]

                        msg = (f"🇹🇭 ผลหวยหุ้นไทยเย็น 🇹🇭\n📅 วันที่: {today_str_display}\n\n"
                               f"📊 SET: {set_last_str} ({set_change_str})\n"
                               f"📊 SET50: {set50_last_str}\n\n"
                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return
                    else:
                        if not is_auto and attempts >= 2:
                            bot.send_message(GROUP_CHAT_ID, f"⏳ ไทยเย็น: เว็บยังไม่อัปเดตผลปิดตลาดครับ (ข้อมูลล่าสุดในเว็บคือเวลา {dt_set.strftime('%H:%M:%S')})")
                            return
                else:
                    print("[Error] Yahoo Finance: ดึงโครงสร้าง Meta ไม่สำเร็จ")
            else:
                if not is_auto and attempts >= 2:
                    bot.send_message(GROUP_CHAT_ID, f"❌ ไทยเย็น: เชื่อมต่อ Yahoo Finance ไม่สำเร็จ (Status: {res_set.status_code})")
                    return

        except Exception as e:
            print(f"[Error] Yahoo Finance Exception: {e}")
            if not is_auto and attempts >= 2:
                bot.send_message(GROUP_CHAT_ID, f"❌ ไทยเย็น: เกิดข้อผิดพลาดในการดึงข้อมูล")
                return

        # 💤 บอทพักหายใจ 10 วินาที
        time.sleep(10)
        
        # 🛑 ระบบตัดจบ (Timeout): ถ้ารอเกิน 1,080 รอบ (ประมาณ 3 ชั่วโมง) ให้ยกเลิกการรอ
        if attempts > 1080:
            if not is_auto:
                bot.send_message(GROUP_CHAT_ID, f"⚠️ ยกเลิกการรอผล งวดวันที่ {today_str_display} (ตลาดอาจจะปิดทำการ หรือเป็นวันหยุดครับ)")
            return

# ==========================================
# 🇲🇾 ดึงผลหวยมาเลย์ (Magnum 4D)
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
                    return 
                    
                if is_auto:
                    bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล หวยมาเลย์ งวดวันที่ {today_str_display} ครับ...")
                    
                t1_letter = results.get("T1", "") 
                t2_letter = results.get("T2", "") 
                
                if t1_letter and t2_letter:
                    t1_idx = ord(t1_letter.upper()) - 64
                    t2_idx = ord(t2_letter.upper()) - 64
                    
                    key_1st = f"S{t1_idx:02d}"
                    key_2nd = f"S{t2_idx:02d}"
                    
                    # 🐞 ดักค่าว่าง
                    prize_1st = str(results.get(key_1st) or "").strip()
                    prize_2nd = str(results.get(key_2nd) or "").strip()
                    
                    # 🛡️ เช็คความยาวและตัวเลขล้วน
                    if len(prize_1st) >= 3 and len(prize_2nd) >= 2 and prize_1st.isdigit() and prize_2nd.isdigit():
                        top_3 = prize_1st[-3:]
                        bottom_2 = prize_2nd[-2:]
                        
                        msg = (f"🇲🇾 ผลหวยมาเลย์ (Magnum 4D) 🇲🇾\n📅 วันที่: {today_str_display}\n\n"
                               f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                        bot.send_message(GROUP_CHAT_ID, msg)
                        return
                        
    except Exception as e:
        print(f"[Error] หวยมาเลย์: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ หวยมาเลย์: ไม่พบผลรางวัลของวันที่ {today_str_display} (อาจไม่มีรอบ Special Draw)")

# ==========================================
# 🇬🇧 ดึงผลหวยหุ้นอังกฤษ
# ==========================================
def fetch_england_stock_fast(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล หวยหุ้นอังกฤษ งวดวันที่ {today_str_display} (จากกระดานหุ้นโลก) ครับ...")

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
                
                price_str = f"{current_price:.2f}"
                change_str = f"{change:.2f}"
                
                integer_part, decimal_part = price_str.split('.')
                top_3 = integer_part[-1] + decimal_part 
                bottom_2 = change_str.split('.')[1]
                
                msg = (f"🇬🇧 ผลหวยหุ้นอังกฤษ 🇬🇧\n📅 วันที่: {today_str_display}\n\n"
                       f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                bot.send_message(GROUP_CHAT_ID, msg)
                return
    except Exception as e:
        print(f"[Error] หวยหุ้นอังกฤษ: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ หวยหุ้นอังกฤษ: ไม่สามารถดึงข้อมูลได้ในขณะนี้")

# ==========================================
# 🇩🇪 ดึงผลหวยหุ้นเยอรมัน (DAX)
# ==========================================
def fetch_germany_normal(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล หวยหุ้นเยอรมัน งวดวันที่ {today_str_display} ครับ...")

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
                
                price_str = f"{current_price:.2f}"
                change_str = f"{change:.2f}"
                
                integer_part, decimal_part = price_str.split('.')
                top_3 = integer_part[-1] + decimal_part 
                bottom_2 = change_str.replace('-', '').split('.')[1] 
                
                msg = (f"🇩🇪 ผลหวยหุ้นเยอรมัน (DAX) 🇩🇪\n📅 วันที่: {today_str_display}\n\n"
                       f"📊 DAX: {price_str} ({change:+.2f})\n\n"
                       f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                bot.send_message(GROUP_CHAT_ID, msg)
                return
    except Exception as e:
        print(f"[Error] หวยหุ้นเยอรมัน: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ หวยหุ้นเยอรมัน: ไม่สามารถดึงข้อมูลได้ในขณะนี้")

# ==========================================
# 🇷🇺 ดึงผลหวยหุ้นรัสเซีย
# ==========================================
def fetch_russia_normal(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล หวยหุ้นรัสเซีย งวดวันที่ {today_str_display} ครับ...")

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
                    
                    integer_part, decimal_part = price_str.split('.')
                    top_3 = integer_part[-1] + decimal_part 
                    bottom_2 = change_str.replace('-', '').split('.')[1] 
                    
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
        bot.send_message(GROUP_CHAT_ID, f"❌ หวยหุ้นรัสเซีย: ไม่สามารถดึงข้อมูลได้ในขณะนี้")

# ==========================================
# 🇺🇸 ดึงผลหวยหุ้นดาวโจนส์ (ปกติ)
# ==========================================
def fetch_dowjones_normal(offset_days=0, is_auto=True):
    target_date = datetime.now(tz) - timedelta(days=offset_days)
    today_str_display = target_date.strftime("%d-%m-%Y")
    
    if is_auto:
        bot.send_message(GROUP_CHAT_ID, f"⏳ เริ่มดึงผล หวยหุ้นดาวโจนส์ งวดวันที่ {today_str_display} ครับ...")

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
                
                price_str = f"{current_price:.2f}"
                change_str = f"{change:.2f}"
                
                integer_part, decimal_part = price_str.split('.')
                top_3 = integer_part[-1] + decimal_part 
                bottom_2 = change_str.replace('-', '').split('.')[1] 
                
                msg = (f"🇺🇸 ผลหวยหุ้นดาวโจนส์ (ปกติ) 🇺🇸\n📅 วันที่: {today_str_display}\n\n"
                       f"📊 Dow Jones: {price_str} ({change:+.2f})\n\n"
                       f"🎯 3 ตัวบน: {top_3}\n👇 2 ตัวล่าง: {bottom_2}\n")
                bot.send_message(GROUP_CHAT_ID, msg)
                return
    except Exception as e:
        print(f"[Error] หวยหุ้นดาวโจนส์: {e}")
        
    if not is_auto:
        bot.send_message(GROUP_CHAT_ID, f"❌ หวยหุ้นดาวโจนส์: ไม่สามารถดึงข้อมูลได้ในขณะนี้")
        
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
        "- 08:30 น. : ลาว Extra /test_lao_extra\n"
        "- 09:06 น. : นิเคอิเช้า VIP /test_nikkei_morning_vip\n"
        "- 09:30 น. : นิเคอิเช้า ปกติ /test_nikkei_morning_normal\n"
        "- 09:30 น. : ฮานอยอาเซียน /test_hanoi_asean\n"
        "- 10:05 น. : จีนเช้า VIP /test_china_morning_vip\n"
        "- 10:30 น. : จีนเช้า ปกติ /test_china_morning_normal\n"
        "- 10:30 น. : ลาวทีวี /test_lao_tv\n"
        "- 10:35 น. : หุ้นฮั่งเส็งเช้า VIP /test_hangseng_morning_vip\n"
        "- 11:30 น. : ฮานอยHD /test_hanoi_hd\n"
        "- 11:35 น. : ไต้หวัน VIP /test_taiwan_vip\n"
        "- 12:30 น. : ฮานอยสตาร์ /test_hanoi_star\n"
        "- 12:30 น. : ไต้หวัน ปกติ /test_taiwan_normal\n"
        "- 11:35 น. : เกาหลี VIP /test_korea_vip\n"
        "- 13:25 น. : นิเคอิบ่าย VIP /test_nikkei_vip_afternoon\n"
        "- 13:30 น. : เกาหลี ปกติ /test_korea_normal\n"
        "- 13:30 น. : นิเคอิ บ่าย /test_nikkei_afternoon\n"
        "- 13:45 น. : ลาวHD /test_laos_hd\n"
        "- 14:00 น. : จีน บ่าย /test_china_afternoon\n"
        "- 14:25 น. : จีนบ่าย VIP /test_china_vip_afternoon\n"
        "- 14:30 น. : ฮานอยทีวี /test_hanoi_tv\n"
        "- 15:09 น. : หุ้นฮั่งเส็งบ่าย ปกติ /test_hangseng_afternoon_normal\n"
        "- 15:25 น. : หุ้นฮั่งเส็งบ่าย VIP /test_hangseng_vip_afternoon\n"
        "- 15:45 น. : ลาวสตาร์ /test_laos_star\n"
        "- 16:30 น. : ฮานอยกาชาด /test_hanoi_redcross\n"
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
        "- 19:50 น. : อียิปต์ /test_egypt\n"
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

# ==========================================
# 📚 ลิสต์ฟังก์ชันหวยทั้งหมด (49 รายการ อ้างอิงตามตารางเวลา)
# ==========================================
ALL_LOTTERY_FUNCTIONS = [
    fetch_lao_extra,
    fetch_nikkei_morning_vip,
    fetch_nikkei_morning_normal,
    fetch_hanoi_asean,
    fetch_china_morning_vip,
    fetch_china_morning_normal,
    fetch_lao_tv,
    fetch_hangseng_morning_vip,
    fetch_hanoi_hd,
    fetch_taiwan_vip,
    fetch_taiwan_normal,
    fetch_korea_vip,
    fetch_nikkei_vip_afternoon,
    fetch_hanoi_star,
    fetch_korea_normal,
    fetch_nikkei_afternoon,
    fetch_laos_hd,
    fetch_china_afternoon,
    fetch_china_vip_afternoon,
    fetch_hanoi_tv,
    fetch_hangseng_afternoon_normal,
    fetch_hangseng_vip_afternoon,
    fetch_laos_star,
    fetch_hanoi_redcross,
    fetch_singapore_fast,
    fetch_thai_evening_fast,
    fetch_india_stock_fast,
    fetch_singapore_vip_fast,
    fetch_hanoi_special,
    fetch_hanoi_samakkhi,
    fetch_hanoi_normal,
    fetch_malay_magnum,
    fetch_hanoi_vip,
    fetch_hanoi_develop,
    fetch_egypt_stock_fast,
    fetch_lao_samakkhi,
    fetch_lao_asean,
    fetch_lao_vip,
    fetch_lao_samakkhi_vip,
    fetch_england_vip,
    fetch_lao_star_vip,
    fetch_hanoi_extra,
    fetch_germany_vip,
    fetch_england_stock_fast,
    fetch_germany_normal,
    fetch_russia_normal,
    fetch_lao_redcross,
    fetch_russia_vip,
    fetch_dowjones_vip,
    fetch_dowjones_normal,
]

# ==========================================
# 🛠️ คำสั่ง: ดึงผลย้อนหลัง 1 วัน (สำหรับทุกหวย)
# ==========================================
@bot.message_handler(commands=['yesterday'])
def test_all_yesterday(message):
    bot.reply_to(message, "🛠 กำลังดึงผลย้อนหลัง 1 วัน สำหรับทุกหวย กรุณารอสักครู่ครับ...\n(หมายเหตุ: หวยบางตัวอาจไม่มีระบบย้อนหลังในหน้า API บอทจะแจ้งเตือนให้ทราบครับ)")
    
    import threading
    for func in ALL_LOTTERY_FUNCTIONS:
        # ส่งค่า (1, False) หมายถึง: offset_days=1 (เมื่อวาน) และ is_auto=False
        threading.Thread(target=func, args=(1, False), daemon=True).start()

# ==========================================
# 🛠️ คำสั่ง: ดึงผลวันนี้ทั้งหมด (เช็คสถานะหวยทั้งหมดของวันนี้)
# ==========================================
@bot.message_handler(commands=['today', 'all'])
def fetch_all_today_cmd(message):
    bot.reply_to(message, "🔄 กำลังดึงข้อมูลผลหวยของ วันนี้ ทั้งหมด กรุณารอสักครู่ครับ...\n(ระบบจะส่งผลที่ออกแล้ว และแจ้งสถานะหวยที่กำลังรอผล)")
    
    import threading
    for func in ALL_LOTTERY_FUNCTIONS:
        # ส่งค่า (0, False) หมายถึง: offset_days=0 (วันนี้) และ is_auto=False
        threading.Thread(target=func, args=(0, False), daemon=True).start()
                
@bot.message_handler(commands=['test_lao_extra'])
def test_lao_extra_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ลาว Extra**{txt}...")
    threading.Thread(target=fetch_lao_extra, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_nikkei_morning_vip'])
def test_nikkei_morning_vip_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **นิเคอิเช้า VIP**{txt}...")
    threading.Thread(target=fetch_nikkei_morning_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_nikkei_morning_normal'])
def test_nikkei_morning_normal_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **นิเคอิเช้า (ปกติ)**{txt}...")
    
    import threading
    threading.Thread(target=fetch_nikkei_morning_normal, args=(offset, False), daemon=True).start()

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

@bot.message_handler(commands=['test_egypt'])
def test_egypt_cmd(message):
    bot.reply_to(message, "🛠️ สั่งทดสอบดึงผล **หวยหุ้นอียิปต์ (EGX30)** ล่าสุด...")
    threading.Thread(target=fetch_egypt_stock_fast, args=(0, False), daemon=True).start()

@bot.message_handler(commands=['test_hanoi_asean'])
def test_hanoi_asean_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮานอยอาเซียน**{txt}...")
    import threading
    threading.Thread(target=fetch_hanoi_asean, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_china_morning_vip'])
def test_china_morning_vip_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **จีนเช้า VIP**{txt}...")
    
    import threading
    threading.Thread(target=fetch_china_morning_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_china_morning_normal'])
def test_china_morning_normal_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **หุ้นจีนเช้า (ปกติ)**{txt}...")
    import threading
    threading.Thread(target=fetch_china_morning_normal, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_lao_tv'])
def test_lao_tv_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ลาวทีวี**{txt}...")
    import threading
    threading.Thread(target=fetch_lao_tv, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_hangseng_morning_vip'])
def test_hangseng_morning_vip_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮั่งเส็งเช้า VIP**{txt}...")
    import threading
    threading.Thread(target=fetch_hangseng_morning_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_hangseng_afternoon_normal'])
def test_hangseng_afternoon_normal_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮั่งเส็งบ่าย (ปกติ)**{txt}...")
    import threading
    threading.Thread(target=fetch_hangseng_afternoon_normal, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_hanoi_hd'])
def test_hanoi_hd_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮานอยHD**{txt}...")
    import threading
    threading.Thread(target=fetch_hanoi_hd, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_taiwan_vip'])
def test_taiwan_vip_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ไต้หวัน VIP**{txt}...")
    import threading
    threading.Thread(target=fetch_taiwan_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_taiwan_normal'])
def test_taiwan_normal_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ไต้หวัน (ปกติ)**{txt}...")
    import threading
    threading.Thread(target=fetch_taiwan_normal, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_korea_vip'])
def test_korea_vip_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **เกาหลี VIP**{txt}...")
    import threading
    threading.Thread(target=fetch_korea_vip, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_korea_normal'])
def test_korea_normal_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **เกาหลี (ปกติ)**{txt}...")
    import threading
    threading.Thread(target=fetch_korea_normal, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_nikkei_afternoon'])
def test_nikkei_afternoon_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **นิเคอิ (บ่าย)**{txt}...")
    import threading
    threading.Thread(target=fetch_nikkei_afternoon, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_nikkei_vip_afternoon'])
def test_nikkei_vip_afternoon_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **นิเคอิบ่าย VIP**{txt}...")
    import threading
    threading.Thread(target=fetch_nikkei_vip_afternoon, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_laos_hd'])
def test_laos_hd_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ลาวHD**{txt}...")
    import threading
    threading.Thread(target=fetch_laos_hd, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_china_afternoon'])
def test_china_afternoon_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **จีน (บ่าย)**{txt}...")
    import threading
    threading.Thread(target=fetch_china_afternoon, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_hanoi_tv'])
def test_hanoi_tv_cmd(message):
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮานอยทีวี**...")
    import threading
    threading.Thread(target=fetch_hanoi_tv, args=(0, False), daemon=True).start()

@bot.message_handler(commands=['test_china_vip_afternoon'])
def test_china_vip_afternoon_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **จีนบ่าย VIP**{txt}...")
    import threading
    threading.Thread(target=fetch_china_vip_afternoon, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_hangseng_vip_afternoon'])
def test_hangseng_vip_afternoon_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮั่งเส็งบ่าย VIP**{txt}...")
    import threading
    threading.Thread(target=fetch_hangseng_vip_afternoon, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_laos_star'])
def test_laos_star_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ลาวสตาร์**{txt}...")
    import threading
    threading.Thread(target=fetch_laos_star, args=(offset, False), daemon=True).start()

@bot.message_handler(commands=['test_hanoi_redcross'])
def test_hanoi_redcross_cmd(message):
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล **ฮานอยกาชาด**...")
    import threading
    threading.Thread(target=fetch_hanoi_redcross, args=(0, False), daemon=True).start()

@bot.message_handler(commands=['test_hanoi_star'])
def test_hanoi_star_cmd(message):
    offset = get_offset(message)
    txt = f" (ย้อนหลัง {offset} วัน)" if offset > 0 else ""
    bot.reply_to(message, f"🛠️ สั่งทดสอบดึงผล ฮานอยสตาร์{txt}...")
    threading.Thread(target=fetch_hanoi_star, args=(offset, False), daemon=True).start()
    
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
    has_run_egypt = False
    has_run_lao_extra = False
    has_run_nikkei_morning_vip = False
    has_run_nikkei_morning_normal = False
    has_run_hanoi_asean = False
    has_run_china_morning_vip = False
    has_run_china_morning_normal = False
    has_run_lao_tv = False
    has_run_hangseng_morning_vip = False
    has_run_hangseng_afternoon_normal = False
    has_run_hanoi_hd = False
    has_run_taiwan_vip = False
    has_run_taiwan_normal = False
    has_run_korea_vip = False
    has_run_korea_normal = False
    has_run_nikkei_afternoon = False
    has_run_nikkei_vip_afternoon = False
    has_run_laos_hd = False
    has_run_china_afternoon = False
    has_run_hanoi_tv = False
    has_run_china_vip_afternoon = False
    has_run_hangseng_vip_afternoon = False
    has_run_laos_star = False
    has_run_hanoi_redcross = False
    has_run_hanoi_star = False
    
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
            has_run_egypt = False
            has_run_lao_extra = False
            has_run_nikkei_morning_vip = False
            has_run_nikkei_morning_normal = False
            has_run_hanoi_asean = False
            has_run_china_morning_vip = False
            has_run_china_morning_normal = False
            has_run_lao_tv = False
            has_run_hangseng_morning_vip = False
            has_run_hangseng_afternoon_normal = False
            has_run_hanoi_hd = False
            has_run_taiwan_vip = False
            has_run_taiwan_normal = False
            has_run_korea_vip = False
            has_run_korea_normal = False
            has_run_nikkei_afternoon = False
            has_run_nikkei_vip_afternoon = False
            has_run_laos_hd = False
            has_run_china_afternoon = False
            has_run_hanoi_tv = False
            has_run_china_vip_afternoon = False
            has_run_hangseng_vip_afternoon = False
            has_run_laos_star = False
            has_run_hanoi_redcross = False
            has_run_hanoi_star = False

            last_check_date = current_date

        # 🕒 รอบ 08:30 น. - หวยลาว Extra
        if now.hour == 8 and now.minute == 30 and not has_run_lao_extra:
            has_run_lao_extra = True
            threading.Thread(target=fetch_lao_extra, daemon=True).start()

        # 🕒 รอบ 09:06 น. - นิเคอิเช้า VIP
        if now.hour == 9 and now.minute == 6 and not has_run_nikkei_morning_vip:
            has_run_nikkei_morning_vip = True
            threading.Thread(target=fetch_nikkei_morning_vip, daemon=True).start()

        # 🕒 รอบ 09:30 น. - ฮานอยอาเซียน
        if now.hour == 9 and now.minute == 30 and not has_run_hanoi_asean:
            has_run_hanoi_asean = True
            threading.Thread(target=fetch_hanoi_asean, daemon=True).start()

        # 🕒 รอบ 09:32 น. - นิเคอิเช้า (ปกติ) [รอให้ตลาดปิดสนิทและตัวเลขนิ่ง 100%]
        if now.hour == 9 and now.minute == 32 and now.weekday() < 5 and not has_run_nikkei_morning_normal:
            has_run_nikkei_morning_normal = True
            threading.Thread(target=fetch_nikkei_morning_normal, daemon=True).start()

        # 🕒 รอบ 10:05 น. - จีนเช้า VIP
        if now.hour == 10 and now.minute == 5 and not has_run_china_morning_vip:
            has_run_china_morning_vip = True
            threading.Thread(target=fetch_china_morning_vip, daemon=True).start()

        # 🕒 รอบ 10:30 น. - จีนเช้า (ปกติ)
        if now.hour == 10 and now.minute == 30 and now.weekday() < 5 and not has_run_china_morning_normal:
            has_run_china_morning_normal = True
            threading.Thread(target=fetch_china_morning_normal, daemon=True).start()

        # 🕒 รอบ 10:30 น. - ลาวทีวี
        if now.hour == 10 and now.minute == 30 and not has_run_lao_tv:
            has_run_lao_tv = True
            threading.Thread(target=fetch_lao_tv, daemon=True).start()

        # 🕒 รอบ 10:35 น. - ฮั่งเส็งเช้า VIP
        if now.hour == 10 and now.minute == 35 and not has_run_hangseng_morning_vip:
            has_run_hangseng_morning_vip = True
            threading.Thread(target=fetch_hangseng_morning_vip, daemon=True).start()

        # 🕒 รอบ 11:30 น. - ฮานอยHD
        if now.hour == 11 and now.minute == 30 and not has_run_hanoi_hd:
            has_run_hanoi_hd = True
            threading.Thread(target=fetch_hanoi_hd, daemon=True).start()

        # 🕒 รอบ 11:35 น. - ไต้หวัน VIP
        if now.hour == 11 and now.minute == 35 and not has_run_taiwan_vip:
            has_run_taiwan_vip = True
            threading.Thread(target=fetch_taiwan_vip, daemon=True).start()

        # 🕒 รอบ 12:32 น. - ไต้หวัน (ปกติ)
        if now.hour == 12 and now.minute == 32 and now.weekday() < 5 and not has_run_taiwan_normal:
            has_run_taiwan_normal = True
            threading.Thread(target=fetch_taiwan_normal, daemon=True).start()

        # 🕒 รอบ 12:35 น. - เกาหลี VIP
        if now.hour == 12 and now.minute == 35 and not has_run_korea_vip:
            has_run_korea_vip = True
            threading.Thread(target=fetch_korea_vip, daemon=True).start()

        # 🕒 รอบ 13:25 น. - นิเคอิบ่าย VIP
        if now.hour == 13 and now.minute == 25 and not has_run_nikkei_vip_afternoon:
            has_run_nikkei_vip_afternoon = True
            threading.Thread(target=fetch_nikkei_vip_afternoon, daemon=True).start()

        # 🕒 รอบ 13:30 น. - นิเคอิ (บ่าย)
        if now.hour == 13 and now.minute == 30 and now.weekday() < 5 and not has_run_nikkei_afternoon:
            has_run_nikkei_afternoon = True
            threading.Thread(target=fetch_nikkei_afternoon, daemon=True).start()

        # 🕒 รอบ 13:32 น. - เกาหลี (ปกติ) (เผื่อเวลาให้ตลาดปิดสมบูรณ์)
        if now.hour == 13 and now.minute == 32 and now.weekday() < 5 and not has_run_korea_normal:
            has_run_korea_normal = True
            threading.Thread(target=fetch_korea_normal, daemon=True).start()

        # 🕒 รอบ 13:45 น. - ลาวHD
        if now.hour == 13 and now.minute == 45 and not has_run_laos_hd:
            has_run_laos_hd = True
            threading.Thread(target=fetch_laos_hd, daemon=True).start()

        # 🕒 รอบ 14:00 น. - จีน (บ่าย)
        if now.hour == 14 and now.minute == 0 and now.weekday() < 5 and not has_run_china_afternoon:
            has_run_china_afternoon = True
            threading.Thread(target=fetch_china_afternoon, daemon=True).start()

        # 🕒 รอบ 14:25 น. - จีนบ่าย VIP
        if now.hour == 14 and now.minute == 25 and not has_run_china_vip_afternoon:
            has_run_china_vip_afternoon = True
            threading.Thread(target=fetch_china_vip_afternoon, daemon=True).start()

        # 🕒 รอบ 14:30 น. - ฮานอยทีวี
        if now.hour == 14 and now.minute == 30 and not has_run_hanoi_tv:
            has_run_hanoi_tv = True
            threading.Thread(target=fetch_hanoi_tv, daemon=True).start()

        # 🕒 รอบ 15:10 น. - ฮั่งเส็งบ่าย (ปกติ)
        if now.hour == 15 and now.minute == 10 and now.weekday() < 5 and not has_run_hangseng_afternoon_normal:
            has_run_hangseng_afternoon_normal = True
            threading.Thread(target=fetch_hangseng_afternoon_normal, daemon=True).start()

        # 🕒 รอบ 15:25 น. - ฮั่งเส็งบ่าย VIP
        if now.hour == 15 and now.minute == 25 and not has_run_hangseng_vip_afternoon:
            has_run_hangseng_vip_afternoon = True
            threading.Thread(target=fetch_hangseng_vip_afternoon, daemon=True).start()

        # 🕒 รอบ 15:45 น. - ลาวสตาร์
        if now.hour == 15 and now.minute == 45 and not has_run_laos_star:
            has_run_laos_star = True
            threading.Thread(target=fetch_laos_star, daemon=True).start()

        # 🕒 รอบ 16:30 น. - หวยหุ้นสิงคโปร์
        if now.hour == 16 and now.minute == 30 and now.weekday() < 5:
            if not has_run_singapore:
                has_run_singapore = True
                threading.Thread(target=fetch_singapore_fast, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 16:30 น. - ฮานอยกาชาด
        if now.hour == 16 and now.minute == 30 and not has_run_hanoi_redcross:
            has_run_hanoi_redcross = True
            threading.Thread(target=fetch_hanoi_redcross, daemon=True).start()

        # 🕒 รอบ 16:50 น. - หวยหุ้นไทยรอบเย็น
        if now.hour == 16 and now.minute == 50 and now.weekday() < 5:
            if not has_run_thai_evening:
                has_run_thai_evening = True
                threading.Thread(target=fetch_thai_evening_fast, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 17:12 น. - หวยหุ้นสิงคโปร์ VIP
        if now.hour == 17 and now.minute == 12:
            if not has_run_singapore_vip:
                has_run_singapore_vip = True
                threading.Thread(target=fetch_singapore_vip_fast, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 17:14 น. - หวยหุ้นอินเดีย
        if now.hour == 17 and now.minute == 14 and now.weekday() < 5: # จันทร์-ศุกร์
            if not has_run_india:
                has_run_india = True
                threading.Thread(target=fetch_india_stock_fast, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 17:30 น. - ฮานอยพิเศษ และ ฮานอยสามัคคี
        if now.hour == 17 and now.minute == 30:
            if not has_run_special:
                has_run_special = True
                threading.Thread(target=fetch_hanoi_special, daemon=True).start()
                time.sleep(2)
                
            if not has_run_samakkhi:
                has_run_samakkhi = True
                threading.Thread(target=fetch_hanoi_samakkhi, daemon=True).start()

        # 🕒 รอบ 18:30 น. - ฮานอยปกติ
        if now.hour == 18 and now.minute == 30 and not has_run_normal:
            has_run_normal = True
            threading.Thread(target=fetch_hanoi_normal, daemon=True).start()

        # 🕒 รอบ 18:45 น. - หวยมาเลย์ (อังคาร(พิเศษ), พุธ, เสาร์, อาทิตย์)
        if now.hour == 18 and now.minute == 45 and now.weekday() in [1, 2, 5, 6]:
            if not has_run_malay:
                has_run_malay = True
                threading.Thread(target=fetch_malay_magnum, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 19:30 น. - ฮานอย VIP และ ฮานอยพัฒนา
        if now.hour == 19 and now.minute == 30:
            if not has_run_vip:
                has_run_vip = True
                threading.Thread(target=fetch_hanoi_vip, daemon=True).start()
                time.sleep(2) # 📌 หน่วงเวลาคั่น
                
            if not has_run_develop:
                has_run_develop = True
                threading.Thread(target=fetch_hanoi_develop, daemon=True).start()

        # 🕒 รอบ 19:50 น. - หวยหุ้นอียิปต์ (ทำงานทุกวัน ยกเว้นวันเสาร์)
        if now.hour == 19 and now.minute == 50 and now.weekday() != 5:
            if not has_run_egypt:
                has_run_egypt = True
                threading.Thread(target=fetch_egypt_stock_fast, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 20:30 น. - ลาวสามัคคี
        if now.hour == 20 and now.minute == 30 and not has_run_lao_samakkhi:
            has_run_lao_samakkhi = True
            threading.Thread(target=fetch_lao_samakkhi, daemon=True).start()

        # 🕒 รอบ 21:00 น. - ลาวอาเซียน
        if now.hour == 21 and now.minute == 00 and not has_run_lao_asean:
            has_run_lao_asean = True
            threading.Thread(target=fetch_lao_asean, daemon=True).start()

        # 🕒 รอบ 21:30 น. - ลาว VIP และ ลาวสามัคคี VIP
        if now.hour == 21 and now.minute == 30:
            if not has_run_lao_vip:
                has_run_lao_vip = True
                threading.Thread(target=fetch_lao_vip, daemon=True).start()
                time.sleep(2) # 📌 หน่วงเวลาคั่น
                
            if not has_run_lao_samakkhi_vip:
                has_run_lao_samakkhi_vip = True
                threading.Thread(target=fetch_lao_samakkhi_vip, daemon=True).start()

        # 🕒 รอบ 21:50 น. - อังกฤษ VIP
        if now.hour == 21 and now.minute == 50 and not has_run_england_vip:
            has_run_england_vip = True
            threading.Thread(target=fetch_england_vip, daemon=True).start()

        # 🕒 รอบ 22:00 น. - ลาวสตาร์ VIP
        if now.hour == 22 and now.minute == 00 and not has_run_lao_star_vip:
            has_run_lao_star_vip = True
            threading.Thread(target=fetch_lao_star_vip, daemon=True).start()

        # 🕒 รอบ 22:30 น. - ฮานอย EXTRA
        if now.hour == 22 and now.minute == 30 and not has_run_hanoi_extra:
            has_run_hanoi_extra = True
            threading.Thread(target=fetch_hanoi_extra, daemon=True).start()

        # 🕒 รอบ 22:50 น. - เยอรมัน VIP
        if now.hour == 22 and now.minute == 50 and not has_run_germany_vip:
            has_run_germany_vip = True
            threading.Thread(target=fetch_germany_vip, daemon=True).start()

        # 🕒 รอบ 23:00 น. - หวยหุ้นอังกฤษ
        if now.hour == 23 and now.minute == 0 and now.weekday() < 5:
            if not has_run_england_normal:
                has_run_england_normal = True
                threading.Thread(target=fetch_england_stock_fast, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 23:00 น. - หวยหุ้นเยอรมัน (ช่วงฤดูร้อน) 
        if now.hour == 23 and now.minute == 0 and now.weekday() < 5:
            if not has_run_germany_normal:
                has_run_germany_normal = True
                threading.Thread(target=fetch_germany_normal, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 23:05 น. - หวยหุ้นรัสเซีย
        if now.hour == 23 and now.minute == 5 and now.weekday() < 5:
            if not has_run_russia_normal:
                has_run_russia_normal = True
                threading.Thread(target=fetch_russia_normal, daemon=True).start()
                time.sleep(2)

        # 🕒 รอบ 23:30 น. - ลาวกาชาด
        if now.hour == 23 and now.minute == 30 and not has_run_lao_redcross:
            has_run_lao_redcross = True
            threading.Thread(target=fetch_lao_redcross, daemon=True).start()

        # 🕒 รอบ 23:50 น. - รัสเซีย VIP
        if now.hour == 23 and now.minute == 50 and not has_run_russia_vip:
            has_run_russia_vip = True
            threading.Thread(target=fetch_russia_vip, daemon=True).start()

        # 🕒 รอบ 00:30 น. - ดาวโจนส์ VIP
        if now.hour == 0 and now.minute == 30 and not has_run_dowjones_vip:
            has_run_dowjones_vip = True
            threading.Thread(target=fetch_dowjones_vip, daemon=True).start()

        # 🕒 รอบ 04:10 น. - หวยหุ้นดาวโจนส์ ปกติ
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

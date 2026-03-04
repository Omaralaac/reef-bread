from flask import Flask, request
import requests
from openpyxl import Workbook, load_workbook
import os
import openpyxl
app = Flask(__name__)

# ===== Load tokens =====

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WHOLESALE_TELEGRAM_BOT_TOKEN = os.getenv("WHOLESALE_TELEGRAM_BOT_TOKEN")
WHOLESALE_TELEGRAM_CHAT_ID = os.getenv("WHOLESALE_TELEGRAM_CHAT_ID")
TRACKING_BOT_TOKEN = os.getenv("TRACKING_BOT_TOKEN")
TRACKING_CHAT_ID = os.getenv("TRACKING_CHAT_ID")

import sqlite3

DB_FILE = "orders.db"  # اسم ملف قاعدة البيانات

def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            province TEXT,
            area TEXT,
            street TEXT,
            building TEXT,
            apartment TEXT,
            phone TEXT,
            alt_phone TEXT,
            order_text TEXT,
            total_price TEXT,
            delivery TEXT,
            gift TEXT
        )
        """)
        conn.commit()
        conn.close()
        print(f"✅ قاعدة البيانات {DB_FILE} جاهزة")
        
# استدعاء الدالة عند تشغيل البوت
init_db()
# ===== Products =====
PRODUCTS = {
    "خبز الشعير": 53,
    "خبز بذور الكتان": 54,
    "خبز الشوفان": 62,
    "خبز بذور الشيا": 62,
    "الخبز الاسمر": 54,
    "خبز عالي الألياف": 56,
    "خبز عالي البروتين": 69
}

# ===== Users =====
USER_ORDERS = {}
# في أعلى ملف الكود مع الإعدادات الأخرى
EXCEL_FILE = "orders.xlsx"  # استبدل orders.xlsx باسم ملفك الحقيقي

def ensure_excel_exists():
    if not os.path.exists(EXCEL_FILE):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Orders"
        # رؤوس الأعمدة بناءً على الصورة التي أرسلتها بالترتيب الصحيح
        headers = [
            "الاسم ثلاثي", "اسم المحافظة", "اسم المنطقة", 
            "اسم الشارع + علامة مميزة", "رقم العمارة", "رقم الشقة", 
            "رقم هاتف ويفضل يكون عليه واتساب", "رقم هاتف اخر (ان وجد)", 
            "الطلب", "الإجمالي بشحن", "التوصيل", "ه+A1:L2دية"
        ]
        ws.append(headers)
        wb.save(EXCEL_FILE)
        print(f"✅ تم إنشاء ملف جديد باسم {EXCEL_FILE}")

# استدعاء الدالة عند تشغيل البوت
ensure_excel_exists()
# ===== Bread Ingredients =====
BREAD_INGREDIENTS = {
    "خبز الشعير": "🟦 خبز الشعير → 53 سعر حراري\nدقيق الشعير\nدقيق القمح حبة كاملة\nخميرة طبيعية\nأملاح البحر بنسبة قليلة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة",
    "خبز الشوفان": "🟦 خبز الشوفان → 74 سعر حراري\nدقيق الشوفان\nدقيق القمح حبة كاملة\nخميرة طبيعية\nأملاح البحر بنسبة قليلة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة",
    "خبز الشيا": "🟦 خبز الشيا → 74 سعر حراري\nدقيق بذور الشيا\nدقيق القمح حبة كاملة\nخميرة طبيعية\nأملاح البحر بنسبة قليلة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة",
    "خبز الكتان": "🟪 خبز بذور الكتان → 77 سعر حراري\nدقيق بذور الكتان\nدقيق القمح حبة كاملة\nخميرة طبيعية\nأملاح البحر بنسبة قليلة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة",
    "الخبز الاسمر": "🟩 خبز أسمر → 70 سعر حراري\nدقيق القمح حبة كاملة\nنخالة القمح\nقليل من أملاح البحر والخميرة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة",
    "خبز عالي الألياف": "🟥 خبز عالي الألياف → 61 سعر حراري\nدقيق القمح حبة كاملة\nنخالة القمح\nقليل من أملاح البحر والخميرة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة",
    "خبز عالي البروتين": "🟧 خبز عالي البروتين → 58 سعر حراري\nبذور الكينوا\nدقيق جوز الهند\nدقيق اللوز\nدقيق القمح حبة كاملة\nقليل من أملاح البحر والخميرة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة"
}

def send_telegram_notification(message, bot_token=None, chat_id=None):
    # استخدام المتغيرات اللي أنت عرفتها في أول الكود كقيم افتراضية
    FINAL_TOKEN = bot_token if bot_token else TELEGRAM_BOT_TOKEN
    FINAL_CHAT_ID = chat_id if chat_id else TELEGRAM_CHAT_ID
    
    url = f"https://api.telegram.org/bot{FINAL_TOKEN}/sendMessage"
    payload = {
        "chat_id": FINAL_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        import requests
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"❌ فشل إرسال إشعار تليجرام: {e}")
def get_user_data_by_phone(phone_number):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, province, area, street, building, apartment, phone, alt_phone, order_text, total_price, delivery, gift
        FROM orders
        WHERE phone = ?
        ORDER BY id DESC
        LIMIT 1
    """, (phone_number,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "الاسم ثلاثي": row[0],
            "اسم المحافظة": row[1],
            "اسم المنطقة": row[2],
            "اسم الشارع + علامة مميزة": row[3],
            "رقم العمارة": row[4],
            "رقم الشقة": row[5],
            "رقم هاتف ويفضل يكون عليه واتساب": row[6],
            "رقم هاتف اخر (ان وجد)": row[7],
            "الطلب": row[8],
            "الإجمالي بشحن": row[9],
            "التوصيل": row[10],
            "هدية": row[11]
        }
    return None
def update_order_by_phone(phone_number, order_text=None, total_price=None, delivery=None, gift=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    fields = []
    values = []
    if order_text is not None:
        fields.append("order_text = ?")
        values.append(order_text)
    if total_price is not None:
        fields.append("total_price = ?")
        values.append(total_price)
    if delivery is not None:
        fields.append("delivery = ?")
        values.append(delivery)
    if gift is not None:
        fields.append("gift = ?")
        values.append(gift)
    
    if fields:
        values.append(phone_number)
        cursor.execute(f"""
            UPDATE orders SET {', '.join(fields)}
            WHERE phone = ?
        """, values)
        conn.commit()
    
    conn.close()
# ===== Save Order To Excel =====
import openpyxl

def save_order(customer_data, order_text, total_price, delivery_text, gift_text):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders 
        (name, province, area, street, building, apartment, phone, alt_phone, order_text, total_price, delivery, gift)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_data.get("الاسم ثلاثي", ""),
        customer_data.get("اسم المحافظة", ""),
        customer_data.get("اسم المنطقة", ""),
        customer_data.get("اسم الشارع + علامة مميزة", ""),
        customer_data.get("رقم العمارة", ""),
        customer_data.get("رقم الشقة", ""),
        customer_data.get("رقم هاتف ويفضل يكون عليه واتساب", ""),
        customer_data.get("رقم هاتف اخر (ان وجد)", ""),
        order_text,
        total_price,
        delivery_text,
        gift_text
    ))
    conn.commit()
    conn.close()
    print("✅ تم الحفظ في SQLite")
# --- دوال التعامل مع الإكسيل ---


def find_order_row_by_phone(phone_number):
    file_name = "orders.xlsx"
    if not os.path.exists(file_name): return None
    wb = load_workbook(file_name)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=False))
    # البحث من الأحدث (الأسفل) للأقدم لضمان الوصول لآخر أوردر للعميل
    for i in range(len(rows) - 1, 0, -1):
        if str(rows[i][6].value) == str(phone_number):
            return i + 1  # يرجع رقم السطر الفعلي في الإكسيل
    return None

def delete_order_from_excel(row_index):
    try:
        wb = load_workbook("orders.xlsx")
        ws = wb.active
        ws.delete_rows(row_index)
        wb.save("orders.xlsx")
        return True
    except Exception as e:
        print(f"Error deleting row: {e}")
        return False
    


def send_wholesale_telegram_notification(text):
    # استخدم التوكن الجديد الخاص ببوت الجملة
    url = f"https://api.telegram.org/bot{WHOLESALE_TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": WHOLESALE_TELEGRAM_CHAT_ID, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending wholesale telegram: {e}")


# ===== Wholesale Logic (معدلة للإرسال الفوري) =====
def save_wholesale_to_excel(data):
    file_name = "Wholesale.xlsx"
    if not os.path.exists(file_name):
        wb = Workbook()
        ws = wb.active
        ws.append(["الاسم", "المحافظة", "المنطقة", "محل أم أون لاين", "رقم التليفون"])
        wb.save(file_name)

    wb = load_workbook(file_name)
    ws = wb.active
    ws.append([data.get("الاسم"), data.get("المحافظة"), data.get("المنطقة"), data.get("محل أم أون لاين"), data.get("رقم التليفون")])
    wb.save(file_name)
    
    # إرسال الإشعار فوراً لبوت الجملة
    admin_msg = (
    "🏢 **طلب انضمام لعملاء الجملة**\n\n"
    f"👤 الاسم: {data.get('الاسم')}\n"
    f"📞 الهاتف: {data.get('رقم الهاتف')}\n"
    f"💼 النشاط: {data.get('نوع النشاط')}\n"
    f"📦 الكمية: {data.get('الكمية المطلوبة تقريبا')}"
    )
    send_telegram_notification(admin_msg)
####################################
def send_tracking_telegram_notification(text):
    print("--- محاولة إرسال إشعار للمتابعة ---") # عشان نتأكد إن الدالة اشتغلت أصلاً
    url = f"https://api.telegram.org/bot{TRACKING_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TRACKING_CHAT_ID, 
        "text": text
    }
    try:
        response = requests.post(url, json=payload)
        # السطر ده هو اللي هيقولنا "مبعتش ليه"
        print(f"نتيجة تليجرام: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ خطأ تقني في الاتصال: {e}")
####################################
def normalize_text(text):
    if not text: return ""
    text = text.strip().replace(" ", "") # حذف المسافات
    replacements = {
        "أ": "ا", "إ": "ا", "آ": "ا",
        "ة": "ه", "ى": "ي",
        "ال": "" # حذف ال التعريف للبحث المرن
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def get_distributors(city_input):
    city = normalize_text(city_input)
    
    # --- الفئة الأولى: محافظات التوصيل المباشر (بدون موزعين) ---
    if any(x in city for x in ["قاهره", "جيزه", "اكتوبر", "تجمع", "شروق"]):
        return "DIRECT_DELIVERY_ONLY" # علامة عشان نرد عليه برد التوصيل المباشر

    # --- الفئة الثانية: المحافظات اللي ليها موزعين (الداتا اللي بعتها) ---
    # المنصورة
    if any(x in city for x in ["منصوره", "دقهليه"]):
        return ("📍 المنصورة (الماركت - العنوان):\n"
                "🏪 قناة السويس - برج الميرلاند\n🏪 المختلط - ش فريدة حسان\n🏪 هايبر مارت - ش سعد زغلول\n🏪 الامام محمد عبده - امام بلاتوه\n🏪 المشاية السفلية - امام جزيرة الورد\n"
                "🏪 الترعة - ش الخلفاء الراشدين\n🏪 طلخا (1،2،3) - ش صلاح سالم والبحر الأعظم\n🏪 أجا - ش بورسعيد\n🏪 بلقاس - خلف بنك مصر\n🏪 شربين - بجوار المركز\n🏪 السنبلاوين - (برايم مارت، نص مشكل)")

    elif "دمياط" in city:
        if "جديده" in city:
            return ("📍 دمياط الجديدة:\n🏪 أسواق القوس (الدولي، المركزية، محبوب)\n🏪 أسواق الحياة - المركزية\n🏪 العمدة - 17\n🏪 أبو عمار - ش أبو الخير\n🏪 البوادي - الأولى\n🏪 السنبايطي - ش باب الحارة")
        else:
            return ("📍 دمياط القديمة:\n🏪 جوهرة هايبر - الشرباصي\n🏪 السيسي/تاج سحل - ش وزير\n🏪 أبو العينين - خلف المحطة\n🏪 الجيار - الشعبية\n🏪 الكانتو/فودة - ش نافع\n🏪 الزيدي - السنانية")

    elif any(x in city for x in ["اسكندريه", "عجمي", "بيطاش", "هانوفيل"]):
        # الإسكندرية فيها الحالتين، هنعرض الموزعين ونقوله متاح توصيل برضه
        return ("📍 الإسكندرية (الموزعين المعتمدين بالطلبات الخارجية):\n1️⃣ هيلثي العجمي\n2️⃣ بيت الجملة (الحديد والصلب)\n3️⃣ زهران (البيطاش)\n4️⃣ فتح الله (ستار، الهانوفيل، أبو يوسف)\n5️⃣ أبو الفضل (عين شمس، السماليهي)\n6️⃣ كارفور العروبة\n\n💡 علماً بأن خدمة التوصيل للمنازل متاحة أيضاً في الإسكندرية.")

    elif "اسماعيليه" in city:
        return "📍 الإسماعيلية:\n🏪 (العمدة، أهل الصفقة، نقاوة، بيتي وان، التعارف، ستار، سلمى، زياد، خديجة، عيد، الحياة، رينا، الحجاز، الفلسطيني، باندا، الغنيمي، العائلة، الدنيا بخير، الوفاء)"

    elif any(x in city for x in ["قليوبيه", "بنها", "طوخ", "قناطر", "منوفيه", "شبين", "سادات", "اشمون"]):
        return "📍 القليوبية والمنوفية:\n📞 للتواصل مع الموزع المعتمد: 01090468901"

    elif "محله" in city: return "📍 المحلة: هيبي سايد"
    elif "دسوق" in city or "كفر الشيخ" in city: return "📍 كفر الشيخ:\n🏪 دسوق (هيبي فود)\n🏪 كفر الشيخ (هيبي ميك)\n📞 خدمة التوصيل: 01113398933"
    elif "اسيوط" in city: return "📍 أسيوط: هيبي لايف / ثلاجة الحرمين"
    elif "بني سويف" in city: return "📍 بني سويف: بن سليمان"
    elif "بورسعيد" in city: return "📍 بورسعيد: أون سبورت"
    elif "ميت غمر" in city: return "📍 ميت غمر: الكانت"
    elif "شرم" in city: return "📍 شرم الشيخ: All In One Market"
    elif "سيناء" in city or "عريش" in city: return "📍 شمال سيناء:\n🏪 منفذ العريش (بجوار مسجد النصر)\n📞 التواصل: 01098949491 / 01221346226"
    elif "قنا" in city: return "📍 قنا:\n📞 أرقام خدمة التوصيل: 01553344300 / 01015401540"
    elif "بحيره" in city: return "📍 البحيرة:\n📞 رقم الموزع: 01558830006"

    # --- الفئة الثالثة: خارج النطاق ---
    return "OUT_OF_SCOPE"
import sqlite3

DB_FILE = "orders.db"

# ===== Verify webhook =====
@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

# ===== Webhook POST =====
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event["sender"]["id"]
            if sender_id not in USER_ORDERS:
                USER_ORDERS[sender_id] = {
                    "items": {},
                    "data_fields": [
                        "الاسم ثلاثي", "اسم المحافظة", "اسم المنطقة", 
                        "اسم الشارع + علامة مميزة", "رقم العمارة", "رقم الشقة", 
                        "رقم هاتف ويفضل يكون عليه واتساب", "رقم هاتف اخر (ان وجد)"
                    ],
                    "wholesale_fields": ["الاسم", "المحافظة", "المنطقة", "محل أم أون لاين", "رقم التليفون"],
                    "current_question": 0,
                    "current_wholesale_question": 0,
                    "customer_data": {},
                    "wholesale_data": {},
                    "stage": "welcome"
                }

            if "message" in event and not event["message"].get("is_echo", False):
                if "quick_reply" in event["message"]:
                    payload = event["message"]["quick_reply"]["payload"]
                    handle_postback(sender_id, {"payload": payload})
                else:
                    handle_message(sender_id, event["message"])
            elif "postback" in event:
                handle_postback(sender_id, event["postback"])
    return "ok", 200

# ===== Database helpers =====
def get_user_data_by_phone(phone):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE phone=? ORDER BY id DESC LIMIT 1", (phone,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "الاسم ثلاثي": row[1],
            "اسم المحافظة": row[2],
            "اسم المنطقة": row[3],
            "اسم الشارع + علامة مميزة": row[4],
            "رقم العمارة": row[5],
            "رقم الشقة": row[6],
            "رقم هاتف ويفضل يكون عليه واتساب": row[7],
            "رقم هاتف اخر (ان وجد)": row[8],
            "الطلب": row[9],
            "الإجمالي بشحن": row[10],
            "التوصيل": row[11],
            "هدية": row[12]
        }
    return None

def save_order_to_db(customer_data, order_text, total_price, delivery_text, gift_text):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders
        (name, province, area, street, building, apartment, phone, alt_phone, order_text, total, delivery, gift)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_data.get("الاسم ثلاثي", ""),
        customer_data.get("اسم المحافظة", ""),
        customer_data.get("اسم المنطقة", ""),
        customer_data.get("اسم الشارع + علامة مميزة", ""),
        customer_data.get("رقم العمارة", ""),
        customer_data.get("رقم الشقة", ""),
        customer_data.get("رقم هاتف ويفضل يكون عليه واتساب", ""),
        customer_data.get("رقم هاتف اخر (ان وجد)", ""),
        order_text,
        total_price,
        delivery_text,
        gift_text
    ))
    conn.commit()
    conn.close()

def update_order_by_phone(phone, order_text=None, total_price=None, delivery=None, gift=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = "UPDATE orders SET "
    params = []
    if order_text: 
        query += "order_text=?, "
        params.append(order_text)
    if total_price:
        query += "total=?, "
        params.append(total_price)
    if delivery:
        query += "delivery=?, "
        params.append(delivery)
    if gift:
        query += "gift=?, "
        params.append(gift)
    query = query.rstrip(", ") + " WHERE phone=?"
    params.append(phone)
    cursor.execute(query, tuple(params))
    conn.commit()
    conn.close()

def save_wholesale_to_db(data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO wholesale 
        (name, province, area, shop, phone)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data.get("الاسم", ""),
        data.get("المحافظة", ""),
        data.get("المنطقة", ""),
        data.get("محل أم أون لاين", ""),
        data.get("رقم التليفون", "")
    ))
    conn.commit()
    conn.close()
    send_wholesale_telegram_notification("🏢 طلب جديد لعملاء الجملة!")

# ===== send_message & quick replies (كما هو) =====
def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    requests.post(url, json={"recipient": {"id": recipient_id}, "message": {"text": text}})

def send_quick_replies(recipient_id, text, quick_replies):
    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    requests.post(url, json={"recipient": {"id": recipient_id}, "message": {"text": text, "quick_replies": quick_replies}})

# ===== باقي الكود: send_welcome, send_main_menu, handle_message, handle_inquiry =====
# يبقى كما هو مع استدعاء الدوال الجديدة save_order_to_db, get_user_data_by_phone, update_order_by_phone
# ... (الدوال السابقة مثل send_message و save_order_to_excel)

# ===== دوال معالجة الطلبات =====
def process_order_action(sender_id, action_type):
    user = USER_ORDERS.get(sender_id, {})
    data = user.get("customer_data", {})

    header_emoji = "⚠️" if action_type == "إلغاء" else "❓"
    admin_msg = (
        f"{header_emoji} **طلب {action_type} أوردر قائم!**\n\n"
        "👤 **بيانات العميل:**\n"
        f"الاسم ثلاثي: {data.get('الاسم ثلاثي', '')}\n"
        f"اسم المحافظة: {data.get('اسم المحافظة', '')}\n"
        f"اسم المنطقة: {data.get('اسم المنطقة', '')}\n"
        f"اسم الشارع + علامة مميزة: {data.get('اسم الشارع + علامة مميزة', '')}\n"
        f"رقم العمارة: {data.get('رقم العمارة', '')}\n"
        f"رقم الشقة: {data.get('رقم الشقة', '')}\n"
        f"رقم هاتف ويفضل يكون عليه واتساب: {data.get('رقم هاتف ويفضل يكون عليه واتساب', '')}\n"
        f"رقم هاتف اخر (ان وجد): {data.get('رقم هاتف اخر (ان وجد)', '')}\n\n"
        "📦 **تفاصيل الأوردر الأخير:**\n"
        f"{data.get('الطلب', 'غير متوفر')}\n"
        "-----------------\n"
        f"🛠️ **نوع الإجراء المطلوب:** {action_type}"
    )

    send_telegram_notification(admin_msg, TRACKING_BOT_TOKEN, TRACKING_CHAT_ID)

    response_text = (
        "✅ تم إرسال طلب الإلغاء للإدارة، وسيتم التأكيد معك قريباً. 💚"
        if action_type == "إلغاء" else
        "✅ تم إرسال استفسارك لقسم المتابعة، وسيتم الرد عليك فوراً. 💚"
    )
    send_message(sender_id, response_text)

    user["stage"] = "welcome"
    send_main_menu(sender_id)


# ===== دالة handle_postback =====
def handle_postback(sender_id, postback):
    payload = postback.get("payload")
    user = USER_ORDERS[sender_id]

    if payload == "START_ORDER":
        USER_ORDERS[sender_id] = {
            "items": {},
            "data_fields": [
                "رقم هاتف ويفضل يكون عليه واتساب",
                "الاسم ثلاثي",
                "اسم المحافظة",
                "اسم المنطقة",
                "اسم الشارع + علامة مميزة",
                "رقم العمارة",
                "رقم الشقة",
                "رقم هاتف اخر (ان وجد)"
            ],
            "current_question": 0,
            "customer_data": {},
            "stage": "collecting_data"
        }
        ask_next_question(sender_id)

    elif payload == "USE_OLD_DATA":
        user["stage"] = "ordering"
        send_products(sender_id)

    elif payload == "RE-ENTER_DATA":
        user["current_question"] = 1
        user["stage"] = "collecting_data"
        ask_next_question(sender_id)

    elif payload == "TRACK_ORDER_MENU":
        user["stage"] = "track_ask_phone"
        send_message(sender_id, "من فضلك أدخل رقم الهاتف الذي قمت بعمل الطلب به (11 رقم):")

    elif payload == "TRACK_INQUIRY":
        user["stage"] = "processing_track_inquiry"
        process_order_action(sender_id, "استفسار")

    elif payload == "MODIFY_ORDER_MENU":
        quick_replies = [
            {"content_type": "text", "title": "➕ إضافة منتج", "payload": "ADD_TO_EXISTING"},
            {"content_type": "text", "title": "🔄 تغيير الأوردر بالكامل", "payload": "CHANGE_ENTIRE_ORDER"}
        ]
        send_quick_replies(sender_id, "هل تود إضافة منتج جديد للطلب أم تغيير الأصناف الحالية؟", quick_replies)

    elif payload == "ADD_TO_EXISTING":
        user["stage"] = "adding_to_existing"
        user["items"] = {}
        send_message(sender_id, "قائمة الإضافات المتاحة 👇")
        send_products(sender_id)

    elif payload == "CHANGE_ENTIRE_ORDER":
        user["stage"] = "ordering"
        user["items"] = {}
        send_products(sender_id)

    elif payload == "CANCEL_EXISTING_ORDER":
        process_order_action(sender_id, "إلغاء")

    elif payload == "INQUIRY_MENU":
        send_inquiry_options(sender_id)

    elif payload.startswith("INQ_"):
        handle_inquiry(sender_id, payload)

    elif payload.startswith("ING_"):
        bread_name = payload.replace("ING_", "")
        if bread_name in BREAD_INGREDIENTS:
            send_message(sender_id, BREAD_INGREDIENTS[bread_name])
            quick_replies = [
                {"content_type": "text", "title": "🛒 طلب أوردر", "payload": "START_ORDER"},
                {"content_type": "text", "title": "🔙 القائمة السابقة", "payload": "INQUIRY_MENU"},
                {"content_type": "text", "title": "🏠 القائمة الرئيسية", "payload": "MAIN_MENU"}
            ]
            send_quick_replies(sender_id, "اختر أحد الخيارات:", quick_replies)

    elif payload.startswith("PRODUCT_"):
        product = payload.replace("PRODUCT_", "")
        user["selected_product"] = product
        send_quantity_menu(sender_id, product)

    elif payload.startswith("QTY_"):
        qty = int(payload.split("_")[1])
        product = user["selected_product"]
        user["items"][product] = user["items"].get(product, 0) + qty
        send_after_product_menu(sender_id)

    elif payload == "ADD_MORE":
        send_products(sender_id)

    elif payload == "FINISH_ORDER":
        show_final_summary(sender_id)

    elif payload == "CONFIRM_ORDER":
        confirm_order(sender_id)

    elif payload == "CANCEL_ORDER":
        cancel_order(sender_id)

    elif payload == "FIND_DISTRIBUTORS":
        user["stage"] = "search_distributor"
        send_message(sender_id, "من فضلك اكتب اسم المحافظة للبحث عن أقرب موزع لك:")

    elif payload == "MAIN_MENU":
        send_main_menu(sender_id)


# ===== أسئلة جمع البيانات =====
def ask_next_question(sender_id):
    user = USER_ORDERS[sender_id]
    index = user["current_question"]
    if index < len(user["data_fields"]):
        field = user["data_fields"][index]
        send_message(sender_id, f"من فضلك اكتب {field}:")
    else:
        user["stage"] = "ordering"
        send_products(sender_id)


# ===== عرض المنتجات =====
def send_products(sender_id):
    quick_replies = [
        {"content_type": "text", "title": f"{name} - {price}ج", "payload": f"PRODUCT_{name}"}
        for name, price in PRODUCTS.items()
    ]
    send_quick_replies(sender_id, "اختر المنتج:", quick_replies)


def send_quantity_menu(sender_id, product):
    quick_replies = [
        {"content_type": "text", "title": str(i), "payload": f"QTY_{i}"}
        for i in range(1, 11)
    ]
    send_quick_replies(sender_id, f"كم عدد أكياس {product}؟", quick_replies)


def send_after_product_menu(sender_id):
    quick_replies = [
        {"content_type": "text", "title": "➕ طلب منتج اخر", "payload": "ADD_MORE"},
        {"content_type": "text", "title": "✅ إنهاء الأوردر", "payload": "FINISH_ORDER"}
    ]
    send_quick_replies(sender_id, "تم إضافة المنتج 👌", quick_replies)


# ===== ملخص الأوردر =====
def show_final_summary(sender_id):
    user = USER_ORDERS.get(sender_id)
    if not user: return

    order = user.get("items", {})
    if not order:
        send_message(sender_id, "لم يتم اختيار أي منتجات بعد.")
        return

    new_items_qty = sum(order.values())
    new_items_price = sum(PRODUCTS[name] * qty for name, qty in order.items())
    details = "\n".join([f"✨ {name} x{qty} = {PRODUCTS[name]*qty}ج" for name, qty in order.items()])

    if user.get("stage") == "adding_to_existing":
        combined_text, combined_price, _, _ = update_existing_order_with_new_items(sender_id)
        summary = f"🧾 **ملخص تحديث الطلب:**\n\n{combined_text}\n💰 الإجمالي الجديد: {combined_price}ج"
    else:
        delivery = 0 if new_items_qty >= 5 else 30
        total_price = new_items_price + delivery
        delivery_text = "مجاني" if delivery == 0 else f"{delivery}ج"
        summary = (
            "🧾 **ملخص طلبك:**\n\n"
            f"{details}\n"
            "-----------------\n"
            f"المجموع: {new_items_price}ج\n"
            f"التوصيل: {delivery_text}\n"
            f"الإجمالي: {total_price}ج"
        )

    quick_replies = [
        {"content_type": "text", "title": "✅ تأكيد وإرسال", "payload": "CONFIRM_ORDER"},
        {"content_type": "text", "title": "❌ إلغاء", "payload": "CANCEL_ORDER"}
    ]
    send_quick_replies(sender_id, summary, quick_replies)


# ===== تأكيد الأوردر =====
def confirm_order(sender_id):
    user = USER_ORDERS.get(sender_id)
    if not user: return

    if user.get("stage") == "adding_to_existing":
        combined_text, combined_price, _, _ = update_existing_order_with_new_items(sender_id)
        tracking_text = (
            f"🔄 **تعديل طلب قائم (إضافة منتجات)**\n\n"
            f"👤 العميل: {user['customer_data'].get('الاسم ثلاثي')}\n"
            f"📞 الهاتف: {user.get('temp_phone')}\n"
            f"📝 الطلب الكامل بعد الإضافة: {combined_text}\n"
            f"💰 الإجمالي الجديد: {combined_price}ج"
        )
        send_telegram_notification(tracking_text)
        send_message(sender_id, "🎉 تم تحديث طلبك بنجاح بإضافة المنتجات الجديدة!\nسيصلك الأوردر كاملاً 🚚💚")

    else:
        order = user.get("items", {})
        total_qty = sum(order.values())
        items_price = sum(PRODUCTS[name]*qty for name, qty in order.items())
        delivery_cost = 0 if total_qty >= 5 else 30
        total_price = items_price + delivery_cost
        delivery_text = "مجاني" if delivery_cost == 0 else f"{delivery_cost}ج"
        gift = "🎁 كيس هدية" if total_qty >= 8 else "لا يوجد"

        excel_order_details = " | ".join([f"{name} x{qty}" for name, qty in order.items()])
        save_order_to_excel(user["customer_data"], excel_order_details, total_price, delivery_text, gift)

        special_area = user["customer_data"].get("اسم المنطقة","")
        if special_area in ["حلوان","15 مايو"]:
            text = "🎉 تم تأكيد طلب حضرتك بنجاح!\nطلبك هيوصل حضرتك يوم الثلاثاء القادم 🚚💚"
        else:
            text = "🎉 تم تأكيد طلب حضرتك بنجاح!\nطلبك هيوصل حضرتك في خلال 48 ساعة 🚚💚"
        send_message(sender_id, text)

    USER_ORDERS[sender_id] = {
        "items": {},
        "data_fields": user.get("data_fields", []),
        "current_question": 0,
        "customer_data": {},
        "stage": "welcome"
    }
    send_main_menu(sender_id)


# ===== إلغاء الأوردر =====
def cancel_order(sender_id):
    send_message(sender_id, "تم إلغاء الطلب بنجاح ❌")
    USER_ORDERS[sender_id]["items"] = {}
    USER_ORDERS[sender_id]["stage"] = "welcome"
    send_welcome(sender_id)


# ===== Run Flask =====
if __name__ == "__main__":
    app.run()

import os
import sys
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# ---------------------------------------------------
# 1. Configuration & Setup
# ---------------------------------------------------
app = Flask(__name__)

# ดึงค่าจาก Environment Variable เพื่อความปลอดภัย (ไม่ Hardcode ในโค้ด)
# คุณต้องตั้งค่าเหล่านี้ใน Server หรือไฟล์ .env
CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', 'YOUR_ACCESS_TOKEN_HERE')
CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', 'YOUR_CHANNEL_SECRET_HERE')

if channel_secret == 'YOUR_CHANNEL_SECRET_HERE':
    print("Warning: Please set LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN environment variables.")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ---------------------------------------------------
# 2. Logic: Validation Function
# ส่วนตรวจสอบข้อมูลเลือกตั้ง (แยกฟังก์ชันออกมาเพื่อให้ Clean และ Test ง่าย)
# ---------------------------------------------------
def validate_election_report(text: str) -> list[str]:
    """
    ตรวจสอบว่าข้อความมีหัวข้อครบถ้วนหรือไม่
    Returns: รายชื่อหัวข้อที่ขาดหายไป (List of missing fields)
    """
    # กำหนดคำสำคัญที่ 'ต้องมี' ในการรายงานผลเลือกตั้งปี 69
    required_fields = [
        "หน่วยที่",       # ระบุหน่วยเลือกตั้ง
        "ผู้มาใช้สิทธิ์",   # จำนวนคนมาเลือกตั้ง
        "คะแนนรวม",      # ผลคะแนน
        "สถานการณ์",      # ปกติ/ไม่ปกติ
        "ผู้รายงาน"       # ชื่อผู้ส่ง
    ]
    
    missing_fields = []
    
    # ตรวจสอบว่ามีคำสำคัญเหล่านี้อยู่ในข้อความหรือไม่
    for field in required_fields:
        if field not in text:
            missing_fields.append(field)
            
    return missing_fields

# ---------------------------------------------------
# 3. Webhook Endpoint
# จุดเชื่อมต่อที่ LINE จะส่งข้อมูลเข้ามา
# ---------------------------------------------------
@app.route("/callback", methods=['POST'])
def callback():
    # รับ X-Line-Signature header
    signature = request.headers.get('X-Line-Signature')
    # รับ body ของ request เป็น text
    body = request.get_data(as_text=True)

    # Log ข้อมูล (ควรใช้ logging library ใน production จริง)
    app.logger.info("Request body: " + body)

    # ตรวจสอบ Signature (Safety Check)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        # หาก Signature ไม่ถูกต้อง ให้ตัดการทำงานทันที (Security Best Practice)
        abort(400)

    return 'OK'

# ---------------------------------------------------
# 4. Message Handler
# ฟังก์ชันตอบกลับเมื่อได้รับข้อความ
# ---------------------------------------------------
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.strip()
    
    # ข้ามข้อความสั้นๆ หรือการทักทายทั่วไป เพื่อไม่ให้บอทรบกวนเกินไป
    if len(user_text) < 5:
        return

    # เรียกใช้ฟังก์ชันตรวจสอบข้อมูล
    missing_items = validate_election_report(user_text)
    
    if not missing_items:
        # กรณีข้อมูลครบถ้วน (Clean & Complete)
        reply_msg = "✅ ได้รับรายงานเลือกตั้งครบถ้วน ขอบคุณครับ"
        # ตรงนี้สามารถเพิ่มโค้ดบันทึกลง Database หรือ Google Sheets ได้ในอนาคต
    else:
        # กรณีข้อมูลไม่ครบ (Incomplete)
        missing_str = "\n- ".join(missing_items)
        reply_msg = (
            f"⚠️ รายงานยังไม่ครบถ้วนครับ\n"
            f"กรุณาระบุข้อมูลต่อไปนี้ให้ครบ:\n"
            f"- {missing_str}\n\n"
            f"(ตัวอย่าง: หน่วยที่ 5, ผู้มาใช้สิทธิ์ 100, คะแนนรวม 95, สถานการณ์ ปกติ, ผู้รายงาน สมชาย)"
        )

    # ส่งข้อความตอบกลับ
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_msg)
    )

if __name__ == "__main__":
    # รันเซิร์ฟเวอร์
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

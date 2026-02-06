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
CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', 'YOUR_ACCESS_TOKEN_HERE')
CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', 'YOUR_CHANNEL_SECRET_HERE')

if CHANNEL_SECRET == 'YOUR_CHANNEL_SECRET_HERE' or CHANNEL_ACCESS_TOKEN == 'YOUR_ACCESS_TOKEN_HERE':
    print("Error: Please set LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN environment variables.")
    sys.exit(1)

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ---------------------------------------------------
# 2. Logic: Validation Function
# ---------------------------------------------------
def validate_election_report(text: str) -> list[str]:
    """
    ตรวจสอบว่าข้อความมีหัวข้อครบถ้วนหรือไม่
    Returns: รายชื่อหัวข้อที่ขาดหายไป
    """
    required_fields = [
        "หน่วยที่",
        "ผู้มาใช้สิทธิ์",
        "คะแนนรวม",
        "สถานการณ์",
        "ผู้รายงาน"
    ]

    missing_fields = []
    for field in required_fields:
        if field not in text:
            missing_fields.append(field)

    return missing_fields

# ---------------------------------------------------
# 3. Webhook Endpoint
# ---------------------------------------------------
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# ---------------------------------------------------
# 4. Message Handler
# ---------------------------------------------------
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.strip()

    # ต้องขึ้นต้นด้วย #รายงาน เพื่อแยกการสนทนาทั่วไปออก
    if not user_text.startswith("#รายงาน"):
        return

    # ตัด prefix ออกก่อน validate
    report_text = user_text.replace("#รายงาน", "", 1).strip()

    missing_items = validate_election_report(report_text)

    if not missing_items:
        reply_msg = "✅ ได้รับรายงานเลือกตั้งครบถ้วน ขอบคุณครับ"
    else:
        missing_str = "\n- ".join(missing_items)
        reply_msg = (
            f"⚠️ รายงานยังไม่ครบถ้วนครับ\n"
            f"กรุณาระบุข้อมูลต่อไปนี้ให้ครบ:\n"
            f"- {missing_str}\n\n"
            f"ตัวอย่าง:\n"
            f"#รายงาน หน่วยที่ 5 ผู้มาใช้สิทธิ์ 100 คะแนนรวม 95 สถานการณ์ ปกติ ผู้รายงาน สมชาย"
        )

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_msg)
        )
    except Exception as e:
        app.logger.error(f"Reply failed: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

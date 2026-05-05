import os
from flask import Flask, request, abort
from dotenv import load_dotenv

# นำเข้าไลบรารีเวอร์ชันใหม่
from google import genai
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage as LineTextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent  # เปลี่ยนจาก TextMessage เป็น TextMessageContent
)

# โหลดค่าจากไฟล์ .env
load_dotenv()

app = Flask(__name__)

# ตั้งค่า LINE API
configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# ตั้งค่า Gemini API
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent) # เปลี่ยนตรงนี้ด้วยเช่นกัน
def handle_message(event):
    user_message = event.message.text
    
    # กำหนดขอบเขตให้ AI ตอบเฉพาะเรื่องในนนทบุรี
    system_instruction = (
        "คุณคือผู้ช่วยอัจฉริยะสำหรับนักเดินทางด้วยรถยนต์ในจังหวัดนนทบุรี "
        "ทำหน้าที่แนะนำสถานที่ท่องเที่ยว ร้านอาหาร คาเฟ่ และจุดจอดรถยนต์ในจังหวัดนนทบุรีเท่านั้น "
        "หากผู้ใช้ถามเรื่องนอกเหนือจากจังหวัดนนทบุรี ให้แจ้งอย่างสุภาพว่าระบบรองรับเฉพาะพื้นที่จังหวัดนนทบุรีเท่านั้น"
    )
    
    try:
        # ใช้คำสั่งของ genai (เวอร์ชันใหม่)
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"{system_instruction}\n\nคำถาม: {user_message}",
        )
        reply_message = response.text
    except Exception as e:
        reply_message = "ขออภัย เกิดข้อผิดพลาดในการเชื่อมต่อกับ AI กรุณาลองใหม่อีกครั้ง"
    
    # ส่งข้อความตอบกลับ LINE
    with ApiClient(configuration) as api_client:
        line_api = MessagingApi(api_client)
        line_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[LineTextMessage(text=reply_message)]
            )
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
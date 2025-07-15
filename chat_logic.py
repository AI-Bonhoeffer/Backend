import os
import time
import re
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from db import load_vector_store

load_dotenv()

vector_store = load_vector_store()

qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model_name="gpt-4o", temperature=0),
    retriever=vector_store.as_retriever()
)

def process_user_input(user_input, is_verified=False):
    responses = []
    current_time = time.time()
    user_input_lower = user_input.lower()

    # ✅ 1. Login Check
    if "8448298087" in user_input and "123456" in user_input:
        responses.append("✅ You are verified. Valid for 24 hours.")
        return responses, True
    elif "8448298087" in user_input or "123456" in user_input:
        responses.append("❌ Wrong Client ID or Password.")
        return responses, False

    # 🔐 2. Check if user is trying to access protected info
    protected_keywords = ["price", "cost", "rate", "invoice", "packaging list", "packing list"]
    if any(keyword in user_input_lower for keyword in protected_keywords):
        if not is_verified:
            responses.append("🔒 Please enter your Client ID and Password to access this information.")
            return responses, False

    # ✅ 3. Price query (specific 4-digit model code)
    if len(user_input.strip()) == 4 and user_input.strip().isalnum():
        query = f"What is the price of model ending with {user_input}?"
        responses.append(qa_chain.run(query))

    # ✅ 4. Generic question with protected keywords (already verified)
    elif any(keyword in user_input_lower for keyword in protected_keywords):
        # Try extracting model code if present
        match = re.search(r"\b([A-Za-z0-9]{4})\b", user_input)
        code = match.group(1) if match else user_input
        query = f"What is the {user_input_lower} for model ending with {code}?"
        responses.append(qa_chain.run(query))

    # ✅ 5. Production/Lead time
    elif any(word in user_input_lower for word in ["production time", "lead time"]):
        responses.append("Production time is 90 days.")

    # ✅ 6. General fallback query
    else:
        responses.append(qa_chain.run(user_input))

    return responses, is_verified

# ✅ Twilio Webhook Flask server (Render-compatible)
if __name__ == "__main__":
    from flask import Flask, request
    from twilio.twiml.messaging_response import MessagingResponse

    app = Flask(__name__)

    @app.route("/whatsapp", methods=["POST"])
    def whatsapp_webhook():
        incoming_msg = request.form.get("Body", "").strip()
        sender = request.form.get("From", "")
        responses, _ = process_user_input(incoming_msg)
        twilio_resp = MessagingResponse()
        for msg in responses:
            twilio_resp.message(msg)
        return str(twilio_resp)

    # ✅ Use Render's dynamic PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

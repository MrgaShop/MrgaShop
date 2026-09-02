import os
import sqlite3
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1365662137")
DB = "orders.db"


def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            items TEXT NOT NULL,
            total INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


@app.get("/")
def home():
    return send_from_directory("static", "index.html")


@app.post("/api/orders")
def create_order():
    data = request.get_json() or {}

    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    address = str(data.get("address", "")).strip()
    items = data.get("items", [])

    if not name or not phone or not address or not items:
        return jsonify({
            "ok": False,
            "error": "Լրացրու բոլոր դաշտերը։"
        }), 400

    total = sum(int(item["price"]) for item in items)

    item_text = "\n".join(
        f"• {item['name']} — {int(item['price']):,} ֏"
        for item in items
    )

    conn = sqlite3.connect(DB)

    cursor = conn.execute(
        """
        INSERT INTO orders
        (name, phone, address, items, total)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, phone, address, item_text, total)
    )

    order_id = cursor.lastrowid

    conn.commit()
    conn.close()

    message = (
        f"🛒 ՆՈՐ ՊԱՏՎԵՐ #{order_id}\n\n"
        f"{item_text}\n\n"
        f"💰 Ընդամենը՝ {total:,} ֏\n\n"
        f"👤 Անուն՝ {name}\n"
        f"📞 Հեռախոս՝ {phone}\n"
        f"📍 Հասցե՝ {address}"
    )

    if not TOKEN:
        return jsonify({
            "ok": False,
            "error": "Telegram Bot-ը դեռ միացված չէ։",
            "order_id": order_id
        }), 503

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=10
        )

        if not response.ok:
            return jsonify({
                "ok": False,
                "error": "Պատվերը պահպանվեց, բայց Telegram ուղարկելը չստացվեց։",
                "order_id": order_id
            }), 502

    except requests.RequestException:
        return jsonify({
            "ok": False,
            "error": "Telegram-ին միանալ չստացվեց։",
            "order_id": order_id
        }), 502

    return jsonify({
        "ok": True,
        "order_id": order_id
    })


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))

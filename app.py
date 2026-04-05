from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import smtplib
from email.mime.text import MIMEText
import os

app = Flask(__name__)
CORS(app)

# ============================================================
#  DATABASE CONFIG — update these values
#  Run setup.sql in MySQL Workbench first (see setup.sql file)
# ============================================================
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",            # your MySQL Workbench username
    "password": "root",   # your MySQL Workbench password
    "database": "portfolio_db"
}

# ============================================================
#  EMAIL NOTIFICATION CONFIG (optional but recommended)
#  Use a Gmail App Password — NOT your real Gmail password.
#  Generate one at:
#  Google Account → Security → 2-Step Verification → App Passwords
# ============================================================
EMAIL_ENABLED    = False                    # set True once you add credentials
GMAIL_SENDER     = "balsaraniyati@gmail.com"  # Gmail address you send FROM
GMAIL_APP_PASS   = "owon nhbx nmku lnub"   # 16-char App Password (spaces ok)
NOTIFY_RECIPIENT = "balsaraniyati@gmail.com"


def get_db():
    """Return a fresh MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)


def send_email_notification(name, email, message):
    """Fire a notification email when a new message arrives."""
    if not EMAIL_ENABLED:
        return
    try:
        body = (
            f"You received a new message on your portfolio!\n\n"
            f"Name:    {name}\n"
            f"Email:   {email}\n\n"
            f"Message:\n{message}\n"
        )
        msg = MIMEText(body)
        msg["Subject"] = f"Portfolio: New message from {name}"
        msg["From"]    = GMAIL_SENDER
        msg["To"]      = NOTIFY_RECIPIENT

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_SENDER, GMAIL_APP_PASS)
            smtp.send_message(msg)

        print(f"[email] Notification sent for message from {name}")
    except Exception as e:
        # Notification failure should never break the form submission
        print(f"[email] Failed to send notification: {e}")


@app.route("/contact", methods=["POST"])
def contact():
    """Save contact form submission to MySQL and optionally send email."""
    data    = request.get_json(silent=True) or {}
    name    = str(data.get("name",    "")).strip()
    email   = str(data.get("email",   "")).strip()
    message = str(data.get("message", "")).strip()

    # --- validation ---
    if not name or not email or not message:
        return jsonify({"error": "All fields are required."}), 400

    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"error": "Invalid email address."}), 400

    if len(message) < 10:
        return jsonify({"error": "Message is too short."}), 400

    # --- save to database ---
    try:
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO contact_messages (name, email, message) VALUES (%s, %s, %s)",
            (name, email, message)
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        print(f"[db] Saved message #{new_id} from {name} <{email}>")
    except mysql.connector.Error as db_err:
        print(f"[db] Error: {db_err}")
        return jsonify({"error": "Database error. Please try again."}), 500

    # --- send email notification (best-effort) ---
    send_email_notification(name, email, message)

    return jsonify({"success": True, "id": new_id}), 201


@app.route("/health", methods=["GET"])
def health():
    """Quick endpoint to verify the server and DB are reachable."""
    try:
        conn = get_db()
        conn.close()
        return jsonify({"status": "ok", "db": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "error", "db": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

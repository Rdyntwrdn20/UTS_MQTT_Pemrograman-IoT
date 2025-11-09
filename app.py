# ==============================================================
# BACKEND FLASK - SISTEM MONITORING DATA SENSOR (UTS)
# Menggunakan MQTT (test.mosquitto.org) + MySQL Database
# ==============================================================
from flask import Flask, jsonify, render_template, redirect, url_for
import paho.mqtt.client as mqtt
import mysql.connector
import threading
import json
from datetime import datetime

# --------------------------------------------------------------
# 1️⃣ SETUP FLASK
# --------------------------------------------------------------
app = Flask(__name__)

# --------------------------------------------------------------
# 2️⃣ DATABASE SETUP (MySQL)
# --------------------------------------------------------------
db_config = {
    'host': 'localhost',       # ganti kalau MySQL-mu pakai IP lain
    'user': 'root',            # ganti sesuai user MySQL kamu
    'password': '',            # isi jika MySQL kamu pakai password
    'database': 'uts_sensor'   # nama database di HeidiSQL
}

def init_db():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS data_sensor (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    suhu FLOAT,
                    humidity FLOAT,
                    lux FLOAT,
                    timestamp VARCHAR(50)
                )''')
    conn.commit()
    conn.close()

init_db()

# --------------------------------------------------------------
# 3️⃣ CALLBACK MQTT
# --------------------------------------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT Broker (test.mosquitto.org)")
        client.subscribe("sensor/data")
    else:
        print("❌ Failed to connect, return code", rc)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        print(f"📥 Data diterima dari MQTT: {data}")

        # --- Validasi format data ---
        suhu = humidity = lux = None

        if all(k in data for k in ("suhu", "humidity", "lux")):
            suhu = float(data["suhu"])
            humidity = float(data["humidity"])
            lux = float(data["lux"])
        elif "data" in data and "temp" in data["data"]:
            suhu = float(data["data"]["temp"])
            humidity = 0
            lux = 0
        else:
            print("⚠️ Format data tidak dikenali, dilewati.")
            return

        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # --- Simpan ke database MySQL ---
        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor()
        cur.execute("INSERT INTO data_sensor (suhu, humidity, lux, timestamp) VALUES (%s, %s, %s, %s)",
                    (suhu, humidity, lux, waktu))
        conn.commit()
        conn.close()

        print(f"💾 Data tersimpan ke MySQL: Suhu={suhu}, Humidity={humidity}, Lux={lux}, Timestamp={waktu}")

    except Exception as e:
        print("⚠️ Error parsing/saving message:", e)

# --------------------------------------------------------------
# 4️⃣ JALANKAN MQTT CLIENT DALAM THREAD
# --------------------------------------------------------------
def mqtt_thread():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("test.mosquitto.org", 1883, 60)
    client.loop_forever()

mqtt_t = threading.Thread(target=mqtt_thread)
mqtt_t.daemon = True
mqtt_t.start()

# --------------------------------------------------------------
# 5️⃣ ENDPOINT FLASK UNTUK DASHBOARD & API
# --------------------------------------------------------------
@app.route('/')
def home():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_all_data():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT * FROM data_sensor ORDER BY id DESC LIMIT 20")
    rows = cur.fetchall()
    conn.close()

    data_list = []
    for row in rows:
        data_list.append({
            "id": row[0],
            "suhu": row[1],
            "humidity": row[2],
            "lux": row[3],
            "timestamp": row[4]
        })
    return jsonify(data_list)

@app.route('/api/summary', methods=['GET'])
def get_summary():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT MAX(suhu), MIN(suhu), AVG(suhu), MAX(humidity), MIN(humidity), AVG(humidity) FROM data_sensor")
    row = cur.fetchone()
    conn.close()

    summary = {
        "suhu_max": round(row[0], 2) if row[0] else None,
        "suhu_min": round(row[1], 2) if row[1] else None,
        "suhu_avg": round(row[2], 2) if row[2] else None,
        "humid_max": round(row[3], 2) if row[3] else None,
        "humid_min": round(row[4], 2) if row[4] else None,
        "humid_avg": round(row[5], 2) if row[5] else None
    }
    return jsonify(summary)

# --------------------------------------------------------------
# 6️⃣ JALANKAN FLASK
# --------------------------------------------------------------
if __name__ == '__main__':
    print("🚀 Flask server berjalan di http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)

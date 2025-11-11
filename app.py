# ==============================================================
# BACKEND FLASK - SISTEM MONITORING DATA SENSOR (UTS)
# Menggunakan MQTT (broker.hivemq.com) + MySQL Database
# ==============================================================
from flask import Flask, jsonify, render_template, redirect, url_for, Response
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
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'uts_sensor'
}

def init_db():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS data_sensor (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    suhu FLOAT,
                    humidity FLOAT,
                    lux FLOAT,
                    timestamp DATETIME
                )''')
    conn.commit()
    conn.close()

init_db()

# --------------------------------------------------------------
# 3️⃣ CALLBACK MQTT
# --------------------------------------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker (broker.hivemq.com)")
        client.subscribe("sensor/ridayanti/data")
    else:
        print("Failed to connect, return code", rc)

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
        else:
            print("Format data tidak dikenali, dilewati.")
            return

        waktu = datetime.now()

        # --- Simpan ke database ---
        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO data_sensor (suhu, humidity, lux, timestamp) VALUES (%s, %s, %s, %s)",
            (suhu, humidity, lux, waktu)
        )
        conn.commit()
        conn.close()

        print(f"💾 Data tersimpan ke MySQL: Suhu={suhu}, Humidity={humidity}, Lux={lux}, Timestamp={waktu}")

    except Exception as e:
        print("Error parsing/saving message:", e)

# --------------------------------------------------------------
# 4️⃣ JALANKAN MQTT CLIENT DALAM THREAD
# --------------------------------------------------------------
def mqtt_thread():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    # Ganti broker ke broker.hivemq.com
    client.connect("broker.hivemq.com", 1883, 60)
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

# ==============================================================
# 6️⃣ API UNTUK DATA SENSOR (RAW JSON)
# ==============================================================
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
            "timestamp": row[4].strftime("%Y-%m-%d %H:%M:%S") if isinstance(row[4], datetime) else str(row[4])
        })

    pretty_json = json.dumps(data_list, indent=2, ensure_ascii=False)
    return Response(pretty_json, mimetype='application/json')

# ==============================================================
# 7️⃣ API UNTUK SUMMARY DATA SENSOR
# ==============================================================
@app.route('/api/summary', methods=['GET'])
def get_summary():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            MAX(suhu), MIN(suhu), AVG(suhu),
            MAX(humidity), MIN(humidity), AVG(humidity)
        FROM data_sensor
    """)
    row = cur.fetchone()

    cur.execute("""
        SELECT id, suhu, humidity, lux, timestamp
        FROM data_sensor
        ORDER BY suhu DESC, humidity DESC
        LIMIT 2
    """)
    top_rows = cur.fetchall()

    cur.execute("""
        SELECT DATE_FORMAT(MAX(timestamp), '%m-%Y') AS month_year
        FROM data_sensor
        GROUP BY DATE_FORMAT(timestamp, '%m-%Y')
        ORDER BY MAX(timestamp) DESC
        LIMIT 2
    """)
    month_rows = cur.fetchall()

    conn.close()

    summary = {
        "suhumax": round(row[0], 2) if row[0] else None,
        "suhumin": round(row[1], 2) if row[1] else None,
        "suhurata": round(row[2], 2) if row[2] else None,
        "humidmax": round(row[3], 2) if row[3] else None,
        "humidmin": round(row[4], 2) if row[4] else None,
        "humidrata": round(row[5], 2) if row[5] else None,
        "nilai_suhu_max_humid_max": [
            {
                "idx": r[0],
                "suhun": r[1],
                "humid": r[2],
                "kecerahan": r[3],
                "timestamp": r[4].strftime("%Y-%m-%d %H:%M:%S") if isinstance(r[4], datetime) else str(r[4])
            } for r in top_rows
        ],
        "month_year_max": [
            {"month_year": m[0]} for m in month_rows
        ]
    }

    pretty_json = json.dumps(summary, indent=2, ensure_ascii=False)
    return Response(pretty_json, mimetype='application/json')

# --------------------------------------------------------------
# 8️⃣ JALANKAN FLASK
# --------------------------------------------------------------
if __name__ == '__main__':
    print("Flask server berjalan di http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)

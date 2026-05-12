import sqlite3
import os

def log_market_data(crop, weight, lat, lon):
    try:
        # Ensure the path is absolute relative to this script's location
        db_path = os.path.join(os.getcwd(), 'data/veripath_pulse.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO market_intelligence (crop_type, weight_kg, lat, lon, transit_status)
            VALUES (?, ?, ?, ?, ?)
        """, (crop, weight, lat, lon, 'INITIALIZED'))
        
        conn.commit()
        conn.close()
        print(f"📊 Secret Pulse: {crop} ({weight}kg) logged at [{lat}, {lon}]")
    except Exception as e:
        print(f"⚠️ Pulse Error: {e}")

import sqlite3
import pandas as pd
from datetime import datetime

def generate_dashboard_summary():
    print("\033[95m" + "📊 VeriPath Exporter Intelligence Report" + "\033[0m")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 45)

    try:
        conn = sqlite3.connect('data/veripath_pulse.db')
        
        # Pull everything from your secret database
        query = "SELECT crop_type, weight_kg, lat, lon, timestamp FROM market_intelligence"
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("📭 No data found in the Pulse Database.")
            return

        # 1. High-Level Stats
        total_weight = df['weight_kg'].sum()
        top_crop = df['crop_type'].value_counts().idxmax()
        
        print(f"📈 Total Volume Tracked: {total_weight} kg")
        print(f"🌟 Leading Export Crop: {top_crop}")
        print("-" * 45)

        # 2. Geolocation Log (The Audit Trail)
        print("📍 Recent Geolocation Pulses:")
        for _, row in df.tail(5).iterrows():
            print(f"  - {row['crop_type']}: {row['weight_kg']}kg at [{row['lat']}, {row['lon']}]")

        conn.close()
    except Exception as e:
        print(f"❌ Report Error: {e}")

if __name__ == "__main__":
    generate_dashboard_summary()

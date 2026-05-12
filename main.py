import asyncio
import pandas as pd
import os
import sys
from bridges.kentrade_login import run_bridge
from bridges.pulse_logger import log_market_data

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

BOTANICAL_MAP = {'Avocado': 'Persea americana', 'Mango': 'Mangifera indica'}

def load_data(file_path):
    """Detects file type and loads it into a DataFrame"""
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == '.xlsx':
        return pd.read_excel(file_path)
    elif ext == '.csv':
        return pd.read_csv(file_path)
    else:
        raise ValueError("Unsupported file format. Please use Excel or CSV.")

async def main():
    print("\033[92m" + "💎 VeriPath: Universal Data Orchestrator" + "\033[0m")
    
    # Check for Excel first, then CSV
    target_file = 'farmers.xlsx' if os.path.exists('farmers.xlsx') else 'farmers.csv'
    
    if not os.path.exists(target_file):
        print(f"❌ Error: {target_file} not found.")
        return

    print(f"📂 Loading data from: {target_file}")
    df = load_data(target_file).dropna(subset=['id', 'name'])

    for index, row in df.iterrows():
        crop = row['crop']
        botanical = row['botanical_name'] if pd.notna(row['botanical_name']) else BOTANICAL_MAP.get(crop, 'Unknown')
        
        print(f"\n[📦 Consignment: {row['id']}]")
        print(f"🌿 Regulatory: {botanical}")
        
        # Bridge execution...
        await run_bridge("DUMMY_USER", "DUMMY_PASS")
        log_market_data(crop, row['weight'], row['lat'], row['lon'])

    print("\n\033[94m✅ Pipeline Finished.\033[0m")

if __name__ == "__main__":
    asyncio.run(main())

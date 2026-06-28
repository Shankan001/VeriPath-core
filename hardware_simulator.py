#!/usr/bin/env python3
"""
VeriPath Hardware Simulator
Mimics ESP32 collar + bolus sending temperature readings to Supabase.
Run this alongside your Streamlit app to demo live telemetry.

Usage:
    python3 hardware_simulator.py                    # simulate all animals
    python3 hardware_simulator.py --tag VP-LIV-0001  # single animal
    python3 hardware_simulator.py --scenario fever   # trigger RED alert
    python3 hardware_simulator.py --interval 10      # read every 10 seconds
"""

import argparse
import time
import random
import sys
from datetime import datetime, timezone

# ── Load env ───────────────────────────────────────────────────
import os
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from supabase_db import get_client

# ── Species thresholds ─────────────────────────────────────────
THRESHOLDS = {
    "Goat":   {"min":38.5,"max":40.0,"mild":40.2,"sig":40.5,"emerg":41.5},
    "Cattle": {"min":38.0,"max":39.3,"mild":39.5,"sig":39.8,"emerg":40.5},
    "Sheep":  {"min":38.5,"max":39.5,"mild":39.8,"sig":40.0,"emerg":41.0},
}

# ── Scenarios ──────────────────────────────────────────────────
SCENARIOS = {
    "normal": {
        "description": "All animals healthy — GREEN readings",
        "temp_fn": lambda t: random.uniform(t["min"], t["max"]),
    },
    "heat_stress": {
        "description": "Daytime heat stress — YELLOW readings afternoon",
        "temp_fn": lambda t: random.uniform(t["mild"], t["sig"] - 0.1),
    },
    "fever": {
        "description": "Pathological fever — RED alerts firing",
        "temp_fn": lambda t: random.uniform(t["sig"], t["emerg"] - 0.1),
    },
    "emergency": {
        "description": "Emergency — critical temperatures",
        "temp_fn": lambda t: random.uniform(t["emerg"], t["emerg"] + 1.0),
    },
    "mixed": {
        "description": "Mixed herd — some GREEN some YELLOW some RED",
        "temp_fn": None,  # handled specially
    },
    "recovery": {
        "description": "Animal recovering — temperatures dropping from RED to YELLOW",
        "temp_fn": lambda t: random.uniform(t["mild"], t["sig"]),
    },
}

def _time_of_day() -> str:
    h = datetime.now().hour
    if 6  <= h < 12: return "morning"
    if 12 <= h < 17: return "afternoon"
    if 17 <= h < 20: return "evening"
    return "night"

def _classify(temp: float, species: str) -> str:
    t   = THRESHOLDS.get(species, THRESHOLDS["Goat"])
    tod = _time_of_day()
    if temp < t["min"]:  return "BLUE"
    if temp <= t["max"]: return "GREEN"
    if temp < t["sig"]:
        return "YELLOW" if tod in ("afternoon","evening") else "RED"
    return "RED"

def _get_temp(scenario: str, species: str, index: int) -> float:
    t = THRESHOLDS.get(species, THRESHOLDS["Goat"])
    if scenario == "mixed":
        # Cycle through states based on animal index
        bucket = index % 3
        if bucket == 0: return round(random.uniform(t["min"], t["max"]), 1)
        if bucket == 1: return round(random.uniform(t["mild"], t["sig"]-0.1), 1)
        return round(random.uniform(t["sig"], t["emerg"]-0.1), 1)
    fn = SCENARIOS[scenario]["temp_fn"]
    return round(fn(t), 1)

def load_animals(company: str = None, tag: str = None) -> list[dict]:
    try:
        client = get_client()
        q = client.table("animals").select("*").eq("status","active")
        if company:
            q = q.eq("company", company)
        if tag:
            q = q.eq("animal_tag", tag)
        res = q.execute()
        return res.data or []
    except Exception as e:
        print(f"❌ Failed to load animals: {e}")
        return []

def post_reading(animal: dict, temp: float,
                 status: str, source: str = "sim:collar") -> bool:
    try:
        client = get_client()
        now    = datetime.now(timezone.utc).isoformat()

        # Insert temp reading
        client.table("animal_temps").insert({
            "animal_tag":    animal["animal_tag"],
            "company":       animal["company"],
            "recorded_by":   source,
            "temp_celsius":  temp,
            "recorded_at":   now,
            "time_of_day":   _time_of_day(),
            "health_status": status,
            "notes":         f"auto:{source}",
        }).execute()

        # Update animal health_status
        client.table("animals").update({
            "health_status": status
        }).eq("animal_tag", animal["animal_tag"]).execute()

        return True
    except Exception as e:
        print(f"  ❌ Post failed for {animal['animal_tag']}: {e}")
        return False

def _status_symbol(status: str) -> str:
    return {"GREEN":"🟢","YELLOW":"🟡","RED":"🔴","BLUE":"🔵"}.get(status,"⚪")

def run_simulator(
    scenario:  str   = "normal",
    interval:  int   = 30,
    tag:       str   = None,
    company:   str   = None,
    cycles:    int   = None,
    source:    str   = "sim:collar",
):
    print(f"\n{'='*55}")
    print(f"  🐄 VeriPath Hardware Simulator")
    print(f"{'='*55}")
    print(f"  Scenario : {scenario} — {SCENARIOS[scenario]['description']}")
    print(f"  Interval : every {interval} seconds")
    print(f"  Filter   : {'tag=' + tag if tag else 'company=' + (company or 'ALL')}")
    print(f"  Cycles   : {'∞ (Ctrl+C to stop)' if not cycles else cycles}")
    print(f"{'='*55}\n")

    animals = load_animals(company=company, tag=tag)
    if not animals:
        print("❌ No animals found. Register animals in VeriPath first.")
        sys.exit(1)

    print(f"✅ Loaded {len(animals)} animal(s):\n")
    for a in animals:
        print(f"  {_status_symbol(a.get('health_status','GREEN'))} "
              f"{a['animal_tag']} — {a.get('species','?')} "
              f"{a.get('breed','?')} · {a.get('county','?')}")
    print()

    cycle = 0
    try:
        while True:
            cycle += 1
            now_str = datetime.now().strftime("%H:%M:%S")
            print(f"━━━ Cycle {cycle} · {now_str} · {_time_of_day()} ━━━")

            for i, animal in enumerate(animals):
                species = animal.get("species","Goat")
                temp    = _get_temp(scenario, species, i)
                status  = _classify(temp, species)
                sym     = _status_symbol(status)

                ok = post_reading(animal, temp, status, source)
                if ok:
                    print(f"  {sym} {animal['animal_tag']:15} "
                          f"{temp}°C → {status:6} "
                          f"[{species}]")
                else:
                    print(f"  ❌ {animal['animal_tag']} — failed")

            print()

            if cycles and cycle >= cycles:
                print(f"✅ Completed {cycles} cycle(s). Stopping.")
                break

            print(f"  ⏱ Next reading in {interval}s... (Ctrl+C to stop)\n")
            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n\n⏹ Simulator stopped after {cycle} cycle(s).")
        print(f"   {len(animals)} animals tracked.")

def main():
    parser = argparse.ArgumentParser(
        description="VeriPath Hardware Simulator — mimics ESP32 collar telemetry"
    )
    parser.add_argument(
        "--scenario", default="normal",
        choices=list(SCENARIOS.keys()),
        help="Temperature scenario to simulate"
    )
    parser.add_argument(
        "--interval", type=int, default=30,
        help="Seconds between readings (default: 30)"
    )
    parser.add_argument(
        "--tag", default=None,
        help="Simulate single animal by tag (e.g. VP-LIV-0001)"
    )
    parser.add_argument(
        "--company", default=None,
        help="Filter by company name"
    )
    parser.add_argument(
        "--cycles", type=int, default=None,
        help="Number of cycles then stop (default: run forever)"
    )
    parser.add_argument(
        "--source", default="sim:collar",
        help="Source label in database (default: sim:collar)"
    )
    parser.add_argument(
        "--list-scenarios", action="store_true",
        help="List all available scenarios and exit"
    )

    args = parser.parse_args()

    if args.list_scenarios:
        print("\nAvailable scenarios:\n")
        for name, cfg in SCENARIOS.items():
            print(f"  {name:12} — {cfg['description']}")
        print()
        sys.exit(0)

    if args.scenario not in SCENARIOS:
        print(f"❌ Unknown scenario '{args.scenario}'")
        print(f"   Available: {', '.join(SCENARIOS.keys())}")
        sys.exit(1)

    run_simulator(
        scenario = args.scenario,
        interval = args.interval,
        tag      = args.tag,
        company  = args.company,
        cycles   = args.cycles,
        source   = args.source,
    )

if __name__ == "__main__":
    main()

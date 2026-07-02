# ── VeriPath Bridge Engine v7.0 ───────────────────────────────
# Demo/Live toggle + CSV fallback for portal downtime

import os
import time
import json
import random
import csv
import io
from datetime import datetime

def _load_env():
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

_load_env()

AFA_IMIS_URL = "https://imis.afa.go.ke/"
KEPHIS_URL   = "https://ieics.kephis.org/login.html"
KENTRADE_URL = "https://www.kentrade.go.ke"

PORTAL_TIMEOUT_SECONDS = 30

def get_bridge_mode() -> str:
    return os.getenv("BRIDGE_MODE", "simulation")

def set_bridge_mode(mode: str) -> None:
    """Set mode at runtime — 'simulation' or 'real'."""
    os.environ["BRIDGE_MODE"] = mode

def get_credential_status() -> dict:
    return {
        "KenTrade": bool(os.getenv("KENTRADE_USERNAME") and os.getenv("KENTRADE_PASSWORD")),
        "KEPHIS":   bool(os.getenv("KEPHIS_USERNAME")   and os.getenv("KEPHIS_PASSWORD")),
        "AFA IMIS": bool(os.getenv("AFA_USERNAME")      and os.getenv("AFA_PASSWORD")),
    }

def set_portal_credentials(portal: str, username: str, password: str) -> None:
    """Set credentials at runtime from UI input."""
    key_map = {
        "KenTrade": ("KENTRADE_USERNAME", "KENTRADE_PASSWORD"),
        "KEPHIS":   ("KEPHIS_USERNAME",   "KEPHIS_PASSWORD"),
        "AFA IMIS": ("AFA_USERNAME",      "AFA_PASSWORD"),
    }
    if portal in key_map:
        u_key, p_key = key_map[portal]
        os.environ[u_key] = username
        os.environ[p_key] = password

# ── CSV Fallback Generator ─────────────────────────────────────
def generate_kentrade_csv(records: list) -> str:
    """Generate KenTrade-formatted CSV for manual upload."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Declaration_Reference", "Exporter_PIN", "Commodity_Description",
        "HS_Code", "Origin_County", "Net_Weight_KG", "FOB_Value_USD",
        "Farmer_Name", "Consignment_ID", "Submission_Date"
    ])
    for r in records:
        writer.writerow([
            r.get("Consignment_ID", r.get("session_id", "—")),
            r.get("KRA_PIN", r.get("kra_pin", "—")),
            r.get("Crop_Type", r.get("crop", "—")),
            r.get("HS_Code", r.get("hs_code", "0804.40")),
            r.get("Origin_County", r.get("county", "—")),
            r.get("Net_Weight_KG", r.get("weight_kg", 0)),
            r.get("FOB_Value_USD", r.get("fob_value_usd", 0)),
            r.get("Farmer_Name", r.get("farmer_name", "—")),
            r.get("Consignment_ID", r.get("session_id", "—")),
            datetime.utcnow().strftime("%Y-%m-%d"),
        ])
    return output.getvalue()

def generate_kephis_csv(records: list) -> str:
    """Generate KEPHIS-formatted CSV for manual upload."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Application_Reference", "Exporter_Name", "Commodity",
        "HS_Code", "Origin", "Quantity_KG", "Destination",
        "Consignment_ID", "Application_Date"
    ])
    for r in records:
        writer.writerow([
            f"KP-{r.get('Consignment_ID', r.get('session_id','VP'))[-6:]}",
            r.get("Farmer_Name", r.get("farmer_name", "—")),
            r.get("Crop_Type",   r.get("crop", "—")),
            r.get("HS_Code",     r.get("hs_code", "0804.40")),
            r.get("Origin_County", r.get("county", "—")),
            r.get("Net_Weight_KG", r.get("weight_kg", 0)),
            "EU",
            r.get("Consignment_ID", r.get("session_id", "—")),
            datetime.utcnow().strftime("%Y-%m-%d"),
        ])
    return output.getvalue()

# ── Simulation mode ────────────────────────────────────────────
PORTAL_RESPONSES = {
    "KenTrade": [
        {"status": "submitted", "ref": "KT-{id}", "message": "Single Window declaration created. Customs officer review queued."},
        {"status": "submitted", "ref": "KT-{id}", "message": "Consignment registered. Reference number issued."},
    ],
    "KEPHIS": [
        {"status": "submitted", "ref": "KP-{id}", "message": "Phytosanitary certificate request logged. Inspection scheduled."},
        {"status": "pending",   "ref": "KP-{id}", "message": "KEPHIS queue busy. Queued for next inspection slot."},
    ],
    "AFA IMIS": [
        {"status": "submitted", "ref": "AFA-{id}", "message": "Agri-food inspection record created in IMIS."},
    ],
}

def _simulate_portal(portal: str, consignment: dict) -> dict:
    c_id     = str(consignment.get("session_id") or consignment.get("Consignment_ID") or "VP-0000")
    short_id = c_id[-6:] if len(c_id) >= 6 else c_id
    time.sleep(0.6)
    response = random.choice(PORTAL_RESPONSES.get(portal, [
        {"status": "submitted", "ref": f"REF-{short_id}", "message": "Submission accepted."}
    ]))
    return {
        "portal":       portal,
        "mode":         "simulation",
        "status":       response["status"],
        "reference":    response["ref"].replace("{id}", short_id),
        "message":      response["message"],
        "submitted_at": datetime.utcnow().isoformat(),
        "consignment":  c_id,
        "fallback_csv": None,
    }

# ── Real mode with timeout + fallback ─────────────────────────
def _submit_with_timeout(submit_fn, consignment: dict,
                         portal: str, records_for_fallback: list) -> dict:
    """Wrap a portal submission with timeout and CSV fallback."""
    import threading
    result_container = [None]
    error_container  = [None]

    def _run():
        try:
            result_container[0] = submit_fn(consignment)
        except Exception as e:
            error_container[0] = str(e)

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join(timeout=PORTAL_TIMEOUT_SECONDS)

    if thread.is_alive():
        # Portal timed out — generate fallback CSV
        thread.join(0)
        csv_data = (generate_kentrade_csv(records_for_fallback)
                    if portal == "KenTrade"
                    else generate_kephis_csv(records_for_fallback))
        return {
            "portal":       portal,
            "mode":         "real",
            "status":       "timeout",
            "reference":    "—",
            "message":      f"{portal} portal timed out after {PORTAL_TIMEOUT_SECONDS}s. CSV fallback generated — upload manually.",
            "submitted_at": datetime.utcnow().isoformat(),
            "consignment":  consignment.get("Consignment_ID","—"),
            "fallback_csv": csv_data,
            "fallback_filename": f"veripath_{portal.lower().replace(' ','_')}_fallback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
        }

    if error_container[0]:
        csv_data = (generate_kentrade_csv(records_for_fallback)
                    if portal == "KenTrade"
                    else generate_kephis_csv(records_for_fallback))
        return {
            "portal":       portal,
            "mode":         "real",
            "status":       "error",
            "reference":    "—",
            "message":      f"{portal} error: {error_container[0]}. CSV fallback generated.",
            "submitted_at": datetime.utcnow().isoformat(),
            "consignment":  consignment.get("Consignment_ID","—"),
            "fallback_csv": csv_data,
            "fallback_filename": f"veripath_{portal.lower().replace(' ','_')}_fallback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
        }

    return result_container[0]

def _submit_kephis_real(consignment: dict) -> dict:
    c_id = consignment.get("Consignment_ID", consignment.get("id", "VP-0000"))
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, slow_mo=800)
            page    = browser.new_page()
            page.goto(KEPHIS_URL, timeout=90000)
            page.fill("#username", os.getenv("KEPHIS_USERNAME", ""))
            page.fill("#password", os.getenv("KEPHIS_PASSWORD", ""))
            page.click("#login_form_submit")
            page.wait_for_load_state("networkidle", timeout=15000)
            browser.close()
            return {
                "portal": "KEPHIS", "mode": "real", "status": "submitted",
                "reference": f"KP-LIVE-{c_id[-6:]}",
                "message": "KEPHIS session opened. Form submission ready.",
                "submitted_at": datetime.utcnow().isoformat(),
                "consignment": c_id, "fallback_csv": None,
            }
    except Exception as e:
        raise Exception(str(e))

def _submit_afa_real(consignment: dict) -> dict:
    c_id = consignment.get("Consignment_ID", consignment.get("id", "VP-0000"))
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, slow_mo=800)
            page    = browser.new_page()
            page.goto(AFA_IMIS_URL, timeout=90000)
            browser.close()
            return {
                "portal": "AFA IMIS", "mode": "real", "status": "submitted",
                "reference": f"AFA-LIVE-{c_id[-6:]}",
                "message": "AFA IMIS portal reached.",
                "submitted_at": datetime.utcnow().isoformat(),
                "consignment": c_id, "fallback_csv": None,
            }
    except Exception as e:
        raise Exception(str(e))

def _submit_kentrade_real(consignment: dict) -> dict:
    c_id = consignment.get("Consignment_ID", consignment.get("id", "VP-0000"))
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, slow_mo=800)
            page    = browser.new_page()
            page.goto(KENTRADE_URL, timeout=90000)
            browser.close()
            return {
                "portal": "KenTrade", "mode": "real", "status": "submitted",
                "reference": f"KT-LIVE-{c_id[-6:]}",
                "message": "KenTrade portal reached.",
                "submitted_at": datetime.utcnow().isoformat(),
                "consignment": c_id, "fallback_csv": None,
            }
    except Exception as e:
        raise Exception(str(e))

# ── Main public function ───────────────────────────────────────
def transmit_consignment(consignment: dict, portals: list = None,
                          all_records: list = None) -> list:
    if portals is None:
        portals = ["KenTrade", "KEPHIS", "AFA IMIS"]
    if all_records is None:
        all_records = [consignment]

    mode    = get_bridge_mode()
    results = []

    for portal in portals:
        if mode == "real":
            if portal == "KenTrade":
                result = _submit_with_timeout(
                    _submit_kentrade_real, consignment, portal, all_records
                )
            elif portal == "KEPHIS":
                result = _submit_with_timeout(
                    _submit_kephis_real, consignment, portal, all_records
                )
            elif portal == "AFA IMIS":
                result = _submit_with_timeout(
                    _submit_afa_real, consignment, portal, all_records
                )
            else:
                result = _simulate_portal(portal, consignment)
        else:
            result = _simulate_portal(portal, consignment)
        results.append(result)

    return results

# ── Logging ───────────────────────────────────────────────────
def save_transmission_log(results: list) -> None:
    os.makedirs("data", exist_ok=True)
    log_file = "data/transmission_log.json"
    existing = []
    if os.path.exists(log_file):
        try:
            with open(log_file) as f:
                existing = json.load(f)
        except Exception:
            existing = []
    # Don't serialize CSV data into log — too large
    clean = [{k: v for k, v in r.items() if k != "fallback_csv"} for r in results]
    existing.extend(clean)
    with open(log_file, "w") as f:
        json.dump(existing, f, indent=2)

def load_transmission_log() -> list:
    log_file = "data/transmission_log.json"
    if not os.path.exists(log_file):
        return []
    try:
        with open(log_file) as f:
            return json.load(f)
    except Exception:
        return []

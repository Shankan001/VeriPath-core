import streamlit as st
import pandas as pd
from datetime import datetime, date, timezone
from supabase_db import get_client

# ── SQL (run once in Supabase):
# CREATE TABLE IF NOT EXISTS vet_consultations (
#     id               SERIAL PRIMARY KEY,
#     animal_tag       TEXT NOT NULL,
#     company          TEXT NOT NULL,
#     vet_username     TEXT NOT NULL,
#     consulted_at     TIMESTAMPTZ DEFAULT NOW(),
#     consult_type     TEXT,
#     diagnosis        TEXT,
#     treatment        TEXT,
#     fee_kes          NUMERIC(10,2) DEFAULT 0,
#     commission_pct   NUMERIC(5,2)  DEFAULT 15.0,
#     commission_kes   NUMERIC(10,2) DEFAULT 0,
#     veripath_cut_kes NUMERIC(10,2) DEFAULT 0,
#     vet_payout_kes   NUMERIC(10,2) DEFAULT 0,
#     referral_month   INTEGER,
#     referral_year    INTEGER,
#     paid_out         BOOLEAN DEFAULT FALSE,
#     notes            TEXT
# );
#
# CREATE TABLE IF NOT EXISTS bolus_installations (
#     id              SERIAL PRIMARY KEY,
#     animal_tag      TEXT NOT NULL,
#     company         TEXT NOT NULL,
#     installed_by    TEXT NOT NULL,
#     installed_at    TIMESTAMPTZ DEFAULT NOW(),
#     bolus_id        TEXT,
#     bolus_brand     TEXT,
#     bolus_batch     TEXT,
#     animal_weight   NUMERIC(6,1),
#     fasted_hours    INTEGER,
#     balling_gun     BOOLEAN DEFAULT FALSE,
#     confirmed_swallow BOOLEAN DEFAULT FALSE,
#     post_check_30min  BOOLEAN DEFAULT FALSE,
#     post_check_24hr   BOOLEAN DEFAULT FALSE,
#     complications     TEXT,
#     checklist_complete BOOLEAN DEFAULT FALSE,
#     notes             TEXT
# );

def _client():
    return get_client()

# ── Commission model ───────────────────────────────────────────────────────
# Month 1–3 post referral: 15–20% of consult fee
# VeriPath takes 10% of fee, vet keeps 90% of fee
# Commission on top of that from diaspora owner referral bonus

CONSULT_TYPES = [
    "Routine checkup",
    "Fever / temperature alert",
    "Disease assessment — CCPP",
    "Disease assessment — PPR",
    "Disease assessment — ECF",
    "Vaccination",
    "Deworming",
    "Wound treatment",
    "Rumen bolus installation",
    "Emergency callout",
    "Post-mortem examination",
    "Other",
]

def _calc_splits(fee: float, commission_pct: float) -> tuple[float, float, float]:
    """Returns (commission_kes, veripath_cut, vet_payout)."""
    commission   = round(fee * (commission_pct / 100), 2)
    veripath_cut = round(fee * 0.10, 2)
    vet_payout   = round(fee - veripath_cut + commission, 2)
    return commission, veripath_cut, vet_payout

def save_consultation(record: dict) -> bool:
    try:
        _client().table("vet_consultations").insert(record).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save consultation: {e}")
        return False

def load_consultations(vet_username: str, company: str) -> list[dict]:
    try:
        res = (_client().table("vet_consultations")
               .select("*")
               .eq("vet_username", vet_username)
               .eq("company", company)
               .order("consulted_at", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []

def load_all_consultations(company: str) -> list[dict]:
    try:
        res = (_client().table("vet_consultations")
               .select("*")
               .eq("company", company)
               .order("consulted_at", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []

def save_bolus_install(record: dict) -> bool:
    try:
        _client().table("bolus_installations").insert(record).execute()
        _client().table("animals").update({
            "bolus_id":       record.get("bolus_id",""),
            "hardware_status": "bolus",
        }).eq("animal_tag", record["animal_tag"]).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save bolus install: {e}")
        return False

def load_bolus_installs(company: str) -> list[dict]:
    try:
        res = (_client().table("bolus_installations")
               .select("*")
               .eq("company", company)
               .order("installed_at", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []

# ── Render ─────────────────────────────────────────────────────────────────
def render_vet_earnings(profile: dict):
    company  = profile.get("company","")
    username = profile.get("username","")
    role     = profile.get("role","")

    if role not in ("veterinarian","admin"):
        st.warning("🔒 Vet earnings requires veterinarian or admin role.")
        return

    st.markdown("# 💰 Vet Earnings & Commissions")
    st.markdown(
        "<p style='color:#64748b'>Consultation fees · referral commissions · bolus installs</p>",
        unsafe_allow_html=True
    )

    tab_log, tab_bolus, tab_earnings = st.tabs([
        "📋 Log Consultation", "💊 Bolus Installation", "💰 My Earnings"
    ])

    # ── TAB 1: Log Consultation ────────────────────────────────────────────
    with tab_log:
        st.markdown("<div class='section-header'>LOG CONSULTATION</div>",
                    unsafe_allow_html=True)

        try:
            res = (_client().table("animals")
                   .select("animal_tag, species, breed, owner_username")
                   .eq("company", company)
                   .eq("status","active")
                   .execute())
            animals = res.data or []
        except Exception:
            animals = []

        if not animals:
            st.info("No animals registered yet.")
            return

        options = {
            f"{a['animal_tag']} — {a.get('species','')} {a.get('breed','')}": a
            for a in animals
        }

        with st.form("consult_form"):
            selected_label  = st.selectbox("Animal *", list(options.keys()))
            selected_animal = options[selected_label]

            col1, col2 = st.columns(2)
            with col1:
                consult_type = st.selectbox("Consultation type *", CONSULT_TYPES)
            with col2:
                fee = st.number_input("Consultation fee (KES) *",
                                      min_value=0.0, value=1500.0,
                                      step=100.0, format="%.2f")

            col3, col4 = st.columns(2)
            with col3:
                commission_pct = st.number_input(
                    "Referral commission % (Month 1–3)",
                    min_value=0.0, max_value=20.0,
                    value=15.0, step=0.5, format="%.1f"
                )
            with col4:
                consult_date = st.date_input("Consultation date", value=date.today())

            diagnosis = st.text_input("Diagnosis / findings",
                                      placeholder="e.g. CCPP suspected — started Tylosin")
            treatment = st.text_input("Treatment given",
                                      placeholder="e.g. Tylosin 10mg/kg IM")
            notes     = st.text_area("Notes", height=70)

            submitted = st.form_submit_button(
                "✅ Save Consultation", use_container_width=True, type="primary"
            )

        if submitted:
            commission, vp_cut, vet_payout = _calc_splits(fee, commission_pct)

            # Preview splits
            st.markdown(f"""
            <div style='background:#0f2233;border:1px solid #1e3a5f;
                        border-radius:12px;padding:16px 20px;margin:12px 0'>
                <div style='font-family:Space Mono,monospace;color:#38bdf8;
                            margin-bottom:10px'>EARNINGS BREAKDOWN</div>
                <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px'>
                    <div style='text-align:center'>
                        <div style='color:#64748b;font-size:0.72rem'>CONSULT FEE</div>
                        <div style='color:#e8eaf0;font-size:1.1rem;font-weight:700'>
                            KES {fee:,.0f}
                        </div>
                    </div>
                    <div style='text-align:center'>
                        <div style='color:#64748b;font-size:0.72rem'>VERIPATH (10%)</div>
                        <div style='color:#f87171;font-size:1.1rem;font-weight:700'>
                            − KES {vp_cut:,.0f}
                        </div>
                    </div>
                    <div style='text-align:center'>
                        <div style='color:#64748b;font-size:0.72rem'>YOUR PAYOUT</div>
                        <div style='color:#4ade80;font-size:1.1rem;font-weight:700'>
                            KES {vet_payout:,.0f}
                        </div>
                    </div>
                </div>
                <div style='border-top:1px solid #1e3a5f;margin-top:10px;
                            padding-top:8px;color:#94a3b8;font-size:0.78rem'>
                    Referral commission ({commission_pct}%):
                    <span style='color:#fbbf24'>+ KES {commission:,.0f}</span>
                    included in payout above
                </div>
            </div>
            """, unsafe_allow_html=True)

            record = {
                "animal_tag":       selected_animal["animal_tag"],
                "company":          company,
                "vet_username":     username,
                "consulted_at":     datetime.combine(
                    consult_date, datetime.min.time()
                ).replace(tzinfo=timezone.utc).isoformat(),
                "consult_type":     consult_type,
                "diagnosis":        diagnosis.strip() or None,
                "treatment":        treatment.strip() or None,
                "fee_kes":          fee,
                "commission_pct":   commission_pct,
                "commission_kes":   commission,
                "veripath_cut_kes": vp_cut,
                "vet_payout_kes":   vet_payout,
                "referral_month":   consult_date.month,
                "referral_year":    consult_date.year,
                "paid_out":         False,
                "notes":            notes.strip() or None,
            }
            if save_consultation(record):
                st.success(
                    f"✅ Consultation logged — KES {vet_payout:,.0f} earned."
                )

    # ── TAB 2: Bolus Installation ──────────────────────────────────────────
    with tab_bolus:
        st.markdown("<div class='section-header'>RUMEN BOLUS INSTALLATION CHECKLIST</div>",
                    unsafe_allow_html=True)
        st.markdown("""
        <div style='background:#0d1224;border:1px solid #1e3a5f;
                    border-radius:10px;padding:12px 16px;margin-bottom:16px;
                    font-size:0.82rem;color:#94a3b8'>
            Complete all checklist items before confirming installation.
            Incomplete installs are flagged for follow-up.
        </div>
        """, unsafe_allow_html=True)

        try:
            res = (_client().table("animals")
                   .select("animal_tag, species, breed, weight_kg")
                   .eq("company", company)
                   .eq("status","active")
                   .execute())
            animals_b = res.data or []
        except Exception:
            animals_b = []

        if not animals_b:
            st.info("No animals registered yet.")
            return

        options_b = {
            f"{a['animal_tag']} — {a.get('species','')} {a.get('breed','')}": a
            for a in animals_b
        }

        with st.form("bolus_form"):
            sel_label_b  = st.selectbox("Animal *", list(options_b.keys()))
            sel_animal_b = options_b[sel_label_b]

            col1, col2 = st.columns(2)
            with col1:
                bolus_id    = st.text_input("Bolus ID *", placeholder="BOL-001")
                bolus_brand = st.text_input("Bolus brand", placeholder="e.g. SmaXtec")
            with col2:
                bolus_batch   = st.text_input("Batch number", placeholder="BT-2024-001")
                animal_weight = st.number_input("Animal weight (KG)",
                                                min_value=0.0, max_value=800.0,
                                                value=0.0, step=0.5)

            st.markdown("**Pre-installation checklist**")
            col_a, col_b = st.columns(2)
            with col_a:
                fasted_hours   = st.number_input("Hours fasted before install",
                                                  min_value=0, max_value=24, value=0)
                balling_gun    = st.checkbox("✅ Balling gun prepared & sterilised")
            with col_b:
                confirmed_swallow = st.checkbox("✅ Swallow confirmed (no regurgitation)")
                post_30min        = st.checkbox("✅ 30-minute post-install check done")

            post_24hr      = st.checkbox("✅ 24-hour follow-up scheduled")
            complications  = st.text_input("Complications (if any)",
                                           placeholder="Leave blank if none")
            notes_b        = st.text_area("Installation notes", height=60)

            submitted_b = st.form_submit_button(
                "💊 Save Installation", use_container_width=True, type="primary"
            )

        if submitted_b:
            checklist_items  = [balling_gun, confirmed_swallow, post_30min, post_24hr]
            checklist_complete = all(checklist_items)
            completed_count    = sum(checklist_items)

            if not bolus_id.strip():
                st.error("❌ Bolus ID is required.")
            else:
                if not checklist_complete:
                    st.warning(
                        f"⚠️ {completed_count}/4 checklist items complete. "
                        f"Installation saved but flagged as incomplete."
                    )
                record_b = {
                    "animal_tag":         sel_animal_b["animal_tag"],
                    "company":            company,
                    "installed_by":       username,
                    "installed_at":       datetime.now(timezone.utc).isoformat(),
                    "bolus_id":           bolus_id.strip(),
                    "bolus_brand":        bolus_brand.strip() or None,
                    "bolus_batch":        bolus_batch.strip() or None,
                    "animal_weight":      animal_weight or None,
                    "fasted_hours":       fasted_hours,
                    "balling_gun":        balling_gun,
                    "confirmed_swallow":  confirmed_swallow,
                    "post_check_30min":   post_30min,
                    "post_check_24hr":    post_24hr,
                    "complications":      complications.strip() or None,
                    "checklist_complete": checklist_complete,
                    "notes":              notes_b.strip() or None,
                }
                if save_bolus_install(record_b):
                    if checklist_complete:
                        st.success(
                            f"✅ Bolus {bolus_id} installed on "
                            f"{sel_animal_b['animal_tag']} — all checks passed."
                        )
                    else:
                        st.warning(
                            f"💊 Bolus {bolus_id} saved with incomplete checklist "
                            f"— flagged for follow-up."
                        )

        # Recent installs
        installs = load_bolus_installs(company)
        if installs:
            st.markdown("---")
            st.markdown("<div class='section-header'>RECENT INSTALLATIONS</div>",
                        unsafe_allow_html=True)
            for inst in installs[:5]:
                complete = inst.get("checklist_complete", False)
                color    = "#16a34a" if complete else "#d97706"
                bg       = "#071a0f" if complete else "#1a0f00"
                inst_at  = inst.get("installed_at","")[:10]
                st.markdown(f"""
                <div style='background:{bg};border:1px solid {color};
                            border-radius:10px;padding:12px 16px;margin-bottom:8px'>
                    <div style='display:flex;justify-content:space-between'>
                        <span style='font-family:Space Mono,monospace;
                                     color:{color};font-weight:700'>
                            💊 {inst.get("bolus_id","—")} →
                            {inst.get("animal_tag","—")}
                        </span>
                        <span style='color:#64748b;font-size:0.75rem'>{inst_at}</span>
                    </div>
                    <div style='color:#94a3b8;font-size:0.78rem;margin-top:4px'>
                        {"✅ Complete" if complete else "⚠️ Incomplete checklist"} ·
                        By {inst.get("installed_by","—")}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ── TAB 3: My Earnings ─────────────────────────────────────────────────
    with tab_earnings:
        st.markdown("<div class='section-header'>EARNINGS SUMMARY</div>",
                    unsafe_allow_html=True)

        consults = load_consultations(username, company)
        if not consults:
            st.info("No consultations logged yet.")
            return

        df = pd.DataFrame(consults)
        df["fee_kes"]        = df["fee_kes"].astype(float)
        df["vet_payout_kes"] = df["vet_payout_kes"].astype(float)
        df["commission_kes"] = df["commission_kes"].astype(float)

        total_fee      = df["fee_kes"].sum()
        total_payout   = df["vet_payout_kes"].sum()
        total_commiss  = df["commission_kes"].sum()
        unpaid         = df[df["paid_out"]==False]["vet_payout_kes"].sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>TOTAL FEES</div>
            <div class='metric-value' style='font-size:1.3rem'>
                KES {total_fee:,.0f}
            </div>
        </div>""", unsafe_allow_html=True)
        c2.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>YOUR PAYOUT</div>
            <div class='metric-value' style='color:#4ade80;font-size:1.3rem'>
                KES {total_payout:,.0f}
            </div>
        </div>""", unsafe_allow_html=True)
        c3.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>COMMISSIONS</div>
            <div class='metric-value' style='color:#fbbf24;font-size:1.3rem'>
                KES {total_commiss:,.0f}
            </div>
        </div>""", unsafe_allow_html=True)
        c4.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>UNPAID</div>
            <div class='metric-value' style='color:#f87171;font-size:1.3rem'>
                KES {unpaid:,.0f}
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # Monthly breakdown
        st.markdown("<div class='section-header'>MONTHLY BREAKDOWN</div>",
                    unsafe_allow_html=True)
        df["consulted_at"] = pd.to_datetime(df["consulted_at"])
        df["month"]        = df["consulted_at"].dt.strftime("%Y-%m")
        monthly = (df.groupby("month")
                     .agg(consults=("fee_kes","count"),
                          total_fee=("fee_kes","sum"),
                          total_payout=("vet_payout_kes","sum"))
                     .reset_index()
                     .sort_values("month", ascending=False))
        st.dataframe(monthly, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("<div class='section-header'>ALL CONSULTATIONS</div>",
                    unsafe_allow_html=True)
        display_cols = ["consulted_at","animal_tag","consult_type",
                        "fee_kes","vet_payout_kes","commission_kes","paid_out"]
        st.dataframe(
            df[[c for c in display_cols if c in df.columns]],
            use_container_width=True, hide_index=True
        )

        if st.button("⬇ Export Earnings CSV"):
            st.download_button(
                "Download CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=f"veripath_vet_earnings_{date.today()}.csv",
                mime="text/csv"
            )

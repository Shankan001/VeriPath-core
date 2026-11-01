import streamlit as st
from datetime import datetime, timezone
from supabase_db import get_client
import listing_photos as lp

LISTING_ROLES = ("admin", "farm_manager", "diaspora_owner")

PURPOSE_OPTIONS = {"Not set": None, "Breeding": "breeding",
                   "Slaughter": "slaughter", "Both": "both"}
STATUS_OPTIONS = {"Available": "available", "Reserved": "reserved",
                  "Sold": "sold"}


def _client():
    return get_client()


def _get_farm(company: str):
    """Returns the public farm profile row linked to this exact company
    string, or None if the farm page has not been set up."""
    link = (_client().table("public_farm_links")
            .select("farm_id").eq("company", company).execute())
    if not link.data:
        return None
    prof = (_client().table("public_farm_profiles")
            .select("id,slug,display_name,is_public")
            .eq("id", link.data[0]["farm_id"]).execute())
    return prof.data[0] if prof.data else None


def _load_animals(company: str) -> list[dict]:
    res = (_client().table("animals")
           .select("animal_tag,species,breed,sex,birth_date,status")
           .eq("company", company).order("animal_tag").execute())
    return res.data or []


def _load_listings(tags: list[str], farm_id: str) -> dict:
    """Maps animal_tag -> existing public_listings row for this farm."""
    if not tags:
        return {}
    links = (_client().table("public_listing_links")
             .select("listing_id,animal_tag").in_("animal_tag", tags).execute())
    if not links.data:
        return {}
    ids = [l["listing_id"] for l in links.data]
    rows = (_client().table("public_listings").select("*")
            .in_("id", ids).eq("farm_id", farm_id).execute())
    by_id = {r["id"]: r for r in (rows.data or [])}
    return {l["animal_tag"]: by_id[l["listing_id"]]
            for l in links.data if l["listing_id"] in by_id}


def _save_listing(company: str, farm_id: str, animal_tag: str,
                  existing: dict | None, fields: dict) -> tuple[bool, str]:
    # Server-side ownership check: the animal MUST belong to this company.
    a = (_client().table("animals")
         .select("animal_tag,species,breed,sex,birth_date")
         .eq("animal_tag", animal_tag).eq("company", company).execute())
    if not a.data:
        return False, "That animal does not belong to your farm."
    animal = a.data[0]
    now = datetime.now(timezone.utc).isoformat()

    row = {
        "title":        fields["title"],
        "description":  fields["description"],
        "purpose":      fields["purpose"],
        "status":       fields["status"],
        "is_published": fields["is_published"],
        "species":      animal.get("species"),
        "breed":        animal.get("breed"),
        "sex":          animal.get("sex"),
        "birth_date":   animal.get("birth_date"),
        "updated_at":   now,
    }

    if existing:
        if fields["is_published"] and not existing.get("published_at"):
            row["published_at"] = now
        (_client().table("public_listings").update(row)
         .eq("id", existing["id"]).eq("farm_id", farm_id).execute())
        return True, "Listing updated."

    row["farm_id"] = farm_id
    row["published_at"] = now if fields["is_published"] else None
    ins = _client().table("public_listings").insert(row).execute()
    if not ins.data:
        return False, "Could not create the listing."
    listing_id = ins.data[0]["id"]
    try:
        _client().table("public_listing_links").insert(
            {"listing_id": listing_id, "animal_tag": animal_tag}).execute()
    except Exception as e:
        # Never leave an orphan public listing without its private link.
        _client().table("public_listings").delete().eq("id", listing_id).execute()
        return False, f"Could not link listing to animal: {e}"
    return True, "Listing created."


def _check_owned(company: str, farm_id: str, listing_id: str, animal_tag: str):
    """Server-side ownership check. Returns (current_photo_paths, error)."""
    a = (_client().table("animals").select("animal_tag")
         .eq("animal_tag", animal_tag).eq("company", company).execute())
    if not a.data:
        return None, "That animal does not belong to your farm."
    link = (_client().table("public_listing_links").select("listing_id")
            .eq("animal_tag", animal_tag).execute())
    if not link.data or link.data[0]["listing_id"] != listing_id:
        return None, "Listing does not match this animal."
    row = (_client().table("public_listings").select("photo_paths")
           .eq("id", listing_id).eq("farm_id", farm_id).execute())
    if not row.data:
        return None, "Listing not found for your farm."
    return list(row.data[0].get("photo_paths") or []), None


def _cleanup(paths):
    for pth in paths:
        try:
            lp.delete_listing_photo(pth)
        except Exception:
            pass


def _add_photos(company, farm_id, listing_id, animal_tag, files):
    current, err = _check_owned(company, farm_id, listing_id, animal_tag)
    if err:
        return False, err
    room = lp.MAX_PHOTOS_PER_LISTING - len(current)
    if room <= 0:
        return False, f"Maximum {lp.MAX_PHOTOS_PER_LISTING} photos reached."
    uploaded = []
    try:
        for f in files[:room]:
            uploaded.append(lp.upload_listing_photo(f.getvalue()))
    except ValueError as e:
        _cleanup(uploaded)
        return False, str(e)
    except Exception as e:
        _cleanup(uploaded)
        return False, f"Upload failed: {e}"
    try:
        (_client().table("public_listings")
         .update({"photo_paths": current + uploaded})
         .eq("id", listing_id).eq("farm_id", farm_id).execute())
    except Exception as e:
        _cleanup(uploaded)
        return False, f"Could not save photos: {e}"
    skipped = len(files) - len(uploaded)
    note = f" ({skipped} skipped, limit {lp.MAX_PHOTOS_PER_LISTING})" if skipped else ""
    return True, f"{len(uploaded)} photo(s) added{note}."


def _remove_photo(company, farm_id, listing_id, animal_tag, path):
    current, err = _check_owned(company, farm_id, listing_id, animal_tag)
    if err:
        return False, err
    if path not in current:
        return False, "Photo not found on this listing."
    (_client().table("public_listings")
     .update({"photo_paths": [x for x in current if x != path]})
     .eq("id", listing_id).eq("farm_id", farm_id).execute())
    _cleanup([path])  # link removed first, so a failed delete leaves no broken image
    return True, "Photo removed."


def render_website_listings(profile: dict):
    role = profile.get("role", "")
    if role not in LISTING_ROLES:
        st.warning("🔒 Access restricted.")
        return
    company = (profile.get("company") or "").strip()
    if not company:
        st.error("Your account has no farm identity set — contact support.")
        return

    st.markdown("# 🌐 Website Listings")
    st.markdown(
        "<p style='color:#64748b'>Choose which animals appear on your public "
        "farm page. Prices are never shown — buyers use “Call for price”.</p>",
        unsafe_allow_html=True)

    flash = st.session_state.pop("_wl_flash", None)
    if flash:
        st.success(flash)

    try:
        farm = _get_farm(company)
    except Exception as e:
        st.error(f"Could not load your farm page: {e}")
        return
    if not farm:
        st.info("Your public farm page isn't set up yet. "
                "Contact VeriPath support to activate it.")
        return

    state = "🟢 LIVE" if farm["is_public"] else "⚪ Not live yet"
    st.caption(f"Farm page: **{farm['display_name']}** · "
               f"/farm/{farm['slug']} · {state}")
    if not farm["is_public"]:
        st.caption("Listings you publish stay hidden until the farm page "
                   "is switched live.")

    try:
        animals = _load_animals(company)
        listings = _load_listings([a["animal_tag"] for a in animals], farm["id"])
    except Exception as e:
        st.error(f"Could not load animals: {e}")
        return
    if not animals:
        st.info("No animals registered yet. Add them in Animal Registry first.")
        return

    st.caption("Public: title, description, breed, sex, birth date, purpose, "
               "status. Never public: animal tag, company, location, health, costs.")

    purpose_by_val = {v: k for k, v in PURPOSE_OPTIONS.items()}
    status_by_val = {v: k for k, v in STATUS_OPTIONS.items()}

    for a in animals:
        tag = a["animal_tag"]
        ex = listings.get(tag)
        badge = ("🟢 Published" if ex and ex["is_published"]
                 else "⚪ Draft" if ex else "— Not listed")
        label = f"{tag} · {a.get('breed','—')} {a.get('species','')} · {badge}"
        with st.expander(label):
            if ex:
                photos = list(ex.get("photo_paths") or [])
                st.markdown(f"**Photos ({len(photos)}/{lp.MAX_PHOTOS_PER_LISTING})** "
                            "— slide order = upload order; first is shown first")
                if photos:
                    pcols = st.columns(len(photos))
                    for i, pth in enumerate(photos):
                        with pcols[i]:
                            st.image(lp.public_url(pth), caption=f"Slide {i+1}")
                            if st.button("Remove", key=f"wl_rm_{tag}_{i}"):
                                ok, msg = _remove_photo(company, farm["id"], ex["id"], tag, pth)
                                if ok:
                                    st.session_state["_wl_flash"] = f"{tag}: {msg}"
                                    st.rerun()
                                else:
                                    st.error(msg)
                if len(photos) < lp.MAX_PHOTOS_PER_LISTING:
                    n = st.session_state.get(f"_wl_up_{tag}", 0)
                    files = st.file_uploader(
                        "Add photos (JPG or PNG)", type=["jpg", "jpeg", "png"],
                        accept_multiple_files=True, key=f"wl_up_{tag}_{n}")
                    if files and st.button("Upload photos", key=f"wl_upbtn_{tag}"):
                        ok, msg = _add_photos(company, farm["id"], ex["id"], tag, files)
                        if ok:
                            st.session_state[f"_wl_up_{tag}"] = n + 1
                            st.session_state["_wl_flash"] = f"{tag}: {msg}"
                            st.rerun()
                        else:
                            st.error(msg)
            else:
                st.caption("Save the listing first, then you can add photos.")
            with st.form(f"wl_form_{tag}"):
                pub = st.checkbox("Show on public website",
                                  value=bool(ex and ex["is_published"]))
                default_title = f"{a.get('breed','')} {a.get('sex','')}".strip()
                title = st.text_input(
                    "Title", value=(ex or {}).get("title") or default_title,
                    max_chars=80)
                desc = st.text_area(
                    "Short description", value=(ex or {}).get("description") or "",
                    max_chars=500)
                p_labels = list(PURPOSE_OPTIONS.keys())
                s_labels = list(STATUS_OPTIONS.keys())
                p_idx = p_labels.index(purpose_by_val.get((ex or {}).get("purpose"), "Not set"))
                s_idx = s_labels.index(status_by_val.get((ex or {}).get("status"), "Available"))
                purpose = st.selectbox("Purpose", p_labels, index=p_idx)
                status = st.selectbox("Status", s_labels, index=s_idx)
                submitted = st.form_submit_button("Save listing")

            if submitted:
                if pub and not title.strip():
                    st.error("A title is required to publish.")
                    continue
                fields = {
                    "title": title.strip(),
                    "description": desc.strip(),
                    "purpose": PURPOSE_OPTIONS[purpose],
                    "status": STATUS_OPTIONS[status],
                    "is_published": pub,
                }
                try:
                    ok, msg = _save_listing(company, farm["id"], tag, ex, fields)
                except Exception as e:
                    ok, msg = False, f"Save failed: {e}"
                if ok:
                    st.session_state["_wl_flash"] = f"{tag}: {msg}"
                    st.rerun()
                else:
                    st.error(msg)

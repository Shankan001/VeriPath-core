import streamlit as st
from supabase_db import get_client
import listing_photos as lp

MAX_GALLERY = 12


def _client():
    return get_client()


def _farms():
    r = (_client().table("public_farm_profiles")
         .select("id,slug,display_name,is_public,gallery_paths")
         .order("display_name").execute())
    return r.data or []


def _current(farm_id: str):
    r = (_client().table("public_farm_profiles").select("gallery_paths")
         .eq("id", farm_id).execute())
    if not r.data:
        return None
    return list(r.data[0].get("gallery_paths") or [])


def _cleanup(paths):
    for p in paths:
        try:
            lp.delete_listing_photo(p)
        except Exception:
            pass


def _add(farm_id: str, files):
    current = _current(farm_id)
    if current is None:
        return False, "Farm not found."
    room = MAX_GALLERY - len(current)
    if room <= 0:
        return False, f"Maximum {MAX_GALLERY} gallery photos reached."
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
        (_client().table("public_farm_profiles")
         .update({"gallery_paths": current + uploaded})
         .eq("id", farm_id).execute())
    except Exception as e:
        _cleanup(uploaded)
        return False, f"Could not save photos: {e}"
    skipped = len(files) - len(uploaded)
    note = f" ({skipped} skipped, limit {MAX_GALLERY})" if skipped else ""
    return True, f"{len(uploaded)} photo(s) added{note}."


def _remove(farm_id: str, path: str):
    current = _current(farm_id)
    if current is None or path not in current:
        return False, "Photo not found on this farm."
    (_client().table("public_farm_profiles")
     .update({"gallery_paths": [p for p in current if p != path]})
     .eq("id", farm_id).execute())
    _cleanup([path])  # link removed first; a failed delete leaves no broken image
    return True, "Photo removed."


def render_client_sites(profile: dict):
    if profile.get("role") != "admin":
        st.warning("🔒 Access restricted.")
        return

    st.markdown("# 🏢 Client Sites")
    st.markdown(
        "<p style='color:#64748b'>Upload farm-life gallery photos on a client's "
        "behalf. Photos are cleaned (location data removed), resized and given "
        "random names. They only become public when the farm is switched live.</p>",
        unsafe_allow_html=True)

    flash = st.session_state.pop("_cs_flash", None)
    if flash:
        st.success(flash)

    try:
        farms = _farms()
    except Exception as e:
        st.error(f"Could not load farms: {e}")
        return
    if not farms:
        st.info("No public farm profiles exist yet.")
        return

    labels = {f"{f['display_name']} (/{f['slug']})": f for f in farms}
    choice = st.selectbox("Client farm", list(labels.keys()))
    farm = labels[choice]
    st.caption("🟢 LIVE" if farm["is_public"] else "⚪ Hidden — not live yet")

    photos = list(farm.get("gallery_paths") or [])
    st.markdown(f"**Gallery ({len(photos)}/{MAX_GALLERY})** — shown in this order")
    if photos:
        cols = st.columns(4)
        for i, p in enumerate(photos):
            with cols[i % 4]:
                st.image(lp.public_url(p), width=160, caption=f"Photo {i+1}")
                if st.button("Remove", key=f"cs_rm_{farm['id']}_{i}"):
                    try:
                        ok, msg = _remove(farm["id"], p)
                    except Exception as e:
                        ok, msg = False, f"Remove failed: {e}"
                    if ok:
                        st.session_state["_cs_flash"] = msg
                        st.rerun()
                    else:
                        st.error(msg)

    if len(photos) < MAX_GALLERY:
        n = st.session_state.get("_cs_up", 0)
        files = st.file_uploader("Add photos (JPG or PNG)",
                                 type=["jpg", "jpeg", "png"],
                                 accept_multiple_files=True,
                                 key=f"cs_up_{farm['id']}_{n}")
        if files and st.button("Upload photos", key="cs_upbtn"):
            try:
                ok, msg = _add(farm["id"], files)
            except Exception as e:
                ok, msg = False, f"Upload failed: {e}"
            if ok:
                st.session_state["_cs_up"] = n + 1
                st.session_state["_cs_flash"] = msg
                st.rerun()
            else:
                st.error(msg)

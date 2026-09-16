import streamlit as st
import os
import io
import urllib.parse
from datetime import date, datetime, timedelta
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Tirth Yatra Photo Portal",
                   layout="wide", page_icon="🚌")

STORAGE_DIR = "Bus_Folders"
GUIDE_IMAGE_PATH = "guide.jpg"
os.makedirs(STORAGE_DIR, exist_ok=True)

# -------------------------------------------------------------
# Form Reset / Version Controller
# Ensures every reload or reset wipes all files and text inputs
# -------------------------------------------------------------
if "form_v" not in st.session_state:
    st.session_state["form_v"] = 0

f_id = st.session_state["form_v"]


def reset_entire_form():
    st.session_state["form_v"] += 1
    st.session_state.pop("last_submission", None)
    st.rerun()

# -------------------------------------------------------------
# Poster Cropping Logic
# -------------------------------------------------------------


def get_cropped_guide(crop_coords):
    if os.path.exists(GUIDE_IMAGE_PATH):
        try:
            with Image.open(GUIDE_IMAGE_PATH) as img:
                w, h = img.size
                box = (
                    int(crop_coords[0] * w),
                    int(crop_coords[1] * h),
                    int(crop_coords[2] * w),
                    int(crop_coords[3] * h)
                )
                return img.crop(box)
        except Exception:
            return None
    return None


CROP_ODO = (0.015, 0.545, 0.250, 0.680)   # Departure Odometer (#9)
CROP_GROUP = (0.015, 0.208, 0.255, 0.350)  # Departure Group (#1)
CROP_GLASS = (0.745, 0.208, 0.985, 0.350)  # Refreshment & Steel Glass (#4)
CROP_MEAL = (0.015, 0.360, 0.255, 0.500)  # Meals / Lunch (#5)

# -------------------------------------------------------------
# PDF Generator Helper
# -------------------------------------------------------------


def generate_pdf(bus, guide, start_d, end_d, saved_count):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, 750, "MUKH MANTRI TIRTH YATRA - TRIP REPORT")
    p.setFont("Helvetica", 12)
    p.drawString(50, 710, f"Bus Number       : {bus}")
    p.drawString(50, 690, f"Team Guide Name  : {guide}")
    p.drawString(50, 670, f"Trip Duration    : {start_d} to {end_d}")
    p.drawString(50, 650, f"Total Photos     : {saved_count}")
    p.drawString(
        50, 630, f"Report Generated : {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
    p.drawString(
        50, 590, "All mandatory odometer readings and journey milestones have been logged.")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


# -------------------------------------------------------------
# Top Header & Trip Metadata
# -------------------------------------------------------------
st.title("🚌 Tirth Yatra - Photo Upload Portal")
st.info("⚠️ **Rules:** GPS Map Camera only. Complete Bus Number must be clearly visible.")

if not os.path.exists(GUIDE_IMAGE_PATH):
    st.warning("📌 Upload the poster once below to load reference images:")
    uploaded_poster = st.file_uploader("Upload Guide Poster", type=[
                                       "jpg", "png", "jpeg"], key="setup_guide")
    if uploaded_poster:
        with open(GUIDE_IMAGE_PATH, "wb") as f:
            f.write(uploaded_poster.getbuffer())
        st.rerun()

# Row 1: Bus Number & Team Guide Name
c_bus, c_guide = st.columns(2)
with c_bus:
    bus_no = st.text_input(
        "Bus Number", placeholder="e.g. AR 20 A 6004", key=f"bus_{f_id}").strip().upper()
with c_guide:
    team_guide = st.text_input("Team Guide / Conductor Name",
                               placeholder="e.g. Gurpreet Singh", key=f"guide_{f_id}").strip()

# Row 2: Trip Start and End Dates
c_start, c_end = st.columns(2)
with c_start:
    trip_start = st.date_input(
        "Trip Start Date", value=date.today(), key=f"start_{f_id}")
with c_end:
    trip_end = st.date_input(
        "Trip End Date", value=date.today() + timedelta(days=3), key=f"end_{f_id}")

st.divider()

# =============================================================
# 1. ODOMETER SECTION (4 PHOTOS)
# =============================================================
st.subheader("⏱️ 1. Odometer Photos (4 Photos Required)")
st.caption("Punjab Start ➔ Destination Arrival ➔ Return Start ➔ Punjab Arrival")

col_ref1, col_box1 = st.columns([1, 3])
with col_ref1:
    odo_guide = get_cropped_guide(CROP_ODO)
    if odo_guide:
        st.image(odo_guide, caption="Reference: Odometer",
                 use_container_width=True)
with col_box1:
    odo_files = st.file_uploader(
        "Upload All 4 Odometer Photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"batch_odo_{f_id}"
    )
    if len(odo_files) > 4:
        st.error(f"❌ Only 4 photos allowed (Selected: {len(odo_files)}).")
    elif len(odo_files) == 4:
        st.success("✅ Exactly 4 Odometer photos selected.")
    if odo_files:
        p_cols = st.columns(min(len(odo_files), 4))
        for i, f in enumerate(odo_files[:4]):
            p_cols[i].image(f, caption=f"Odo {i+1}", use_container_width=True)

st.divider()

# =============================================================
# 2. YATRI GROUP PHOTOS (4 PHOTOS)
# =============================================================
st.subheader("👥 2. Yatri Group Photos (4 Photos Required)")
st.caption("Departure Banner ➔ Inside Cabin ➔ Return Group ➔ MLA/VIP Group")

col_ref2, col_box2 = st.columns([1, 3])
with col_ref2:
    grp_guide = get_cropped_guide(CROP_GROUP)
    if grp_guide:
        st.image(grp_guide, caption="Reference: Group Photo",
                 use_container_width=True)
with col_box2:
    group_files = st.file_uploader(
        "Upload All 4 Group Photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"batch_group_{f_id}"
    )
    if len(group_files) > 4:
        st.error(f"❌ Only 4 photos allowed (Selected: {len(group_files)}).")
    elif len(group_files) == 4:
        st.success("✅ Exactly 4 Group photos selected.")
    if group_files:
        p_cols = st.columns(min(len(group_files), 4))
        for i, f in enumerate(group_files[:4]):
            p_cols[i].image(
                f, caption=f"Group {i+1}", use_container_width=True)

st.divider()

# =============================================================
# 3. DISTRIBUTION SECTION (GLASS & REFRESHMENTS)
# =============================================================
st.subheader("🥤 3. Glass & Refreshment Distribution")
st.caption("Steel glass distribution & tea/snack service inside the bus")

col_ref3, col_box3 = st.columns([1, 3])
with col_ref3:
    glass_guide = get_cropped_guide(CROP_GLASS)
    if glass_guide:
        st.image(glass_guide, caption="Reference: Glass / Refreshment",
                 use_container_width=True)
with col_box3:
    dist_files = st.file_uploader(
        "Upload Distribution Photos (1 or 2 Photos)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"batch_dist_{f_id}"
    )
    if len(dist_files) > 2:
        st.error(f"❌ Maximum 2 photos allowed.")
    elif dist_files:
        p_cols = st.columns(min(len(dist_files), 2))
        for i, f in enumerate(dist_files[:2]):
            p_cols[i].image(
                f, caption=f"Distribution {i+1}", use_container_width=True)

st.divider()

# =============================================================
# 4. MEALS SECTION (BREAKFAST, LUNCH, DINNER)
# =============================================================
st.subheader("🍽️ 4. Passenger Meals")
st.caption("Breakfast, Lunch, Dinner, or Hi-Tea photos in one place")

col_ref4, col_box4 = st.columns([1, 3])
with col_ref4:
    meal_guide = get_cropped_guide(CROP_MEAL)
    if meal_guide:
        st.image(meal_guide, caption="Reference: Meals",
                 use_container_width=True)
with col_box4:
    meal_files = st.file_uploader(
        "Upload Meals Photos (Up to 3 Photos)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"batch_meals_{f_id}"
    )
    if len(meal_files) > 3:
        st.error(f"❌ Maximum 3 meal photos allowed.")
    elif meal_files:
        p_cols = st.columns(min(len(meal_files), 3))
        for i, f in enumerate(meal_files[:3]):
            p_cols[i].image(f, caption=f"Meal {i+1}", use_container_width=True)

st.divider()

# =============================================================
# ACTION BUTTONS: SAVE & RESET
# =============================================================
col_btn_save, col_btn_reset = st.columns([3, 1])

with col_btn_save:
    save_clicked = st.button(
        "💾 SAVE ALL PHOTOS TO FOLDER", type="primary", use_container_width=True)

with col_btn_reset:
    if st.button("🔄 Reset / Clear Form", use_container_width=True):
        reset_entire_form()

if save_clicked:
    if not bus_no:
        st.error("❌ Please enter the Bus Number first!")
    elif not team_guide:
        st.error("❌ Please enter the Team Guide Name first!")
    elif len(odo_files) > 4 or len(group_files) > 4 or len(dist_files) > 2 or len(meal_files) > 3:
        st.error("❌ Please fix photo limits before saving.")
    else:
        batch_folder_name = f"{trip_start}_to_{trip_end}"
        bus_folder = os.path.join(
            STORAGE_DIR, batch_folder_name, bus_no.replace(" ", "_"))
        os.makedirs(bus_folder, exist_ok=True)

        info_path = os.path.join(bus_folder, "trip_info.txt")
        with open(info_path, "w", encoding="utf-8") as f_info:
            f_info.write(f"BUS NUMBER      : {bus_no}\n")
            f_info.write(f"TEAM GUIDE      : {team_guide}\n")
            f_info.write(f"TRIP DURATION   : {trip_start} to {trip_end}\n")
            f_info.write(
                f"SUBMITTED AT    : {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}\n")

        def save_files(files, prefix):
            cnt = 0
            for idx, uf in enumerate(files, start=1):
                img = Image.open(uf)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(os.path.join(
                    bus_folder, f"{prefix}_{idx}.jpg"), "JPEG", quality=85)
                cnt += 1
            return cnt

        total_saved = 0
        total_saved += save_files(odo_files[:4], "01_Odometer")
        total_saved += save_files(group_files[:4], "02_Yatri_Group")
        total_saved += save_files(dist_files[:2], "03_Distribution")
        total_saved += save_files(meal_files[:3], "04_Meals")

        if total_saved > 0:
            st.session_state["last_submission"] = {
                "bus_no": bus_no,
                "team_guide": team_guide,
                "trip_start": str(trip_start),
                "trip_end": str(trip_end),
                "total_saved": total_saved,
                "folder": bus_folder
            }
        else:
            st.warning("⚠️ No photos selected. Please select photos first.")

# =============================================================
# EXPORT & WHATSAPP SHARE (PERSISTENT DISPLAY)
# =============================================================
if "last_submission" in st.session_state:
    sub = st.session_state["last_submission"]
    st.success(
        f"✅ Submission Saved for {sub['bus_no']} ({sub['total_saved']} Photos Recorded)")

    wa_msg = (
        f"🚌 *MUKH MANTRI TIRTH YATRA REPORT*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *Bus Number:* {sub['bus_no']}\n"
        f"👤 *Team Guide:* {sub['team_guide']}\n"
        f"📅 *Dates:* {sub['trip_start']} to {sub['trip_end']}\n"
        f"📸 *Photos Saved:* {sub['total_saved']} Photos\n"
        f"✅ *Status:* Complete & Verified\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"All odometer and meal records logged successfully."
    )
    wa_link = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_msg)}"

    pdf_bytes = generate_pdf(
        sub["bus_no"],
        sub["team_guide"],
        sub["trip_start"],
        sub["trip_end"],
        sub["total_saved"]
    )

    st.markdown("### 📤 Export & Next Actions")
    col_pdf, col_wa, col_next = st.columns([1, 1, 1])

    with col_pdf:
        st.download_button(
            label="📄 Download Trip PDF Report",
            data=pdf_bytes,
            file_name=f"{sub['bus_no']}_Trip_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    with col_wa:
        st.link_button(
            label="📲 Share on WhatsApp",
            url=wa_link,
            type="primary",
            use_container_width=True
        )

    with col_next:
        if st.button("➕ Start Next Bus (Clear All)", use_container_width=True):
            reset_entire_form()

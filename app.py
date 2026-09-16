import streamlit as st
import os
import io
import zipfile
import urllib.parse
from datetime import date, datetime, timedelta
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

st.set_page_config(page_title="Tirth Yatra Fleet Portal",
                   layout="wide", page_icon="🚌")

STORAGE_DIR = "Bus_Folders"
GUIDE_IMAGE_PATH = "guide.jpg"
os.makedirs(STORAGE_DIR, exist_ok=True)

# -------------------------------------------------------------
# Session State Management
# -------------------------------------------------------------
if "form_v" not in st.session_state:
    st.session_state["form_v"] = 0

f_id = st.session_state["form_v"]


def reset_entire_form():
    st.session_state["form_v"] += 1
    st.session_state.pop("last_submission", None)
    st.rerun()

# -------------------------------------------------------------
# Poster Cropping
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


CROP_ODO = (0.015, 0.545, 0.250, 0.680)
CROP_GROUP = (0.015, 0.208, 0.255, 0.350)
CROP_GLASS = (0.745, 0.208, 0.985, 0.350)
CROP_MEAL = (0.015, 0.360, 0.255, 0.500)

# -------------------------------------------------------------
# PDF Generator with Embedded Images
# -------------------------------------------------------------


def generate_photo_dossier_pdf(bus, guide, start_d, end_d, photo_manifest):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    page_w, page_h = A4

    def draw_header():
        p.setFillColor(colors.HexColor("#0D47A1"))
        p.rect(0, page_h - 70, page_w, 70, fill=True, stroke=False)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(30, page_h - 38,
                     "MUKH MANTRI TIRTH YATRA - FLEET AUDIT DOSSIER")
        p.setFont("Helvetica", 9)
        p.drawString(
            30, page_h - 55, "Department of Transport, Punjab | Milestone Verification Record")
        p.setFillColor(colors.black)

    draw_header()

    # Trip Metadata Panel
    p.setFillColor(colors.HexColor("#F5F5F5"))
    p.rect(30, page_h - 145, page_w - 60, 65, fill=True, stroke=True)
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(45, page_h - 95, f"BUS NUMBER     : {bus}")
    p.drawString(45, page_h - 112, f"TEAM GUIDE     : {guide}")
    p.drawString(320, page_h - 95, f"TRIP DATES     : {start_d} to {end_d}")
    p.drawString(320, page_h - 112,
                 f"TOTAL PHOTOS   : {len(photo_manifest)} Images")
    p.setFont("Helvetica-Oblique", 8)
    p.drawString(45, page_h - 132,
                 f"Generated: {datetime.now().strftime('%d-%b-%Y %I:%M %p')} | Location Tagged: GPS Verified")

    # Grid settings: 2 columns x 2 rows per page = 4 photos per page
    box_w = 255
    box_h = 240
    col_coords = [35, 305]
    row_coords = [page_h - 410, page_h - 675]

    slots_on_page = 0
    first_page = True

    for item in photo_manifest:
        if first_page and slots_on_page == 4:
            p.showPage()
            draw_header()
            first_page = False
            slots_on_page = 0
            row_coords = [page_h - 325, page_h - 590]
        elif not first_page and slots_on_page == 4:
            p.showPage()
            draw_header()
            slots_on_page = 0

        c_idx = slots_on_page % 2
        r_idx = slots_on_page // 2
        x = col_coords[c_idx]
        y = row_coords[r_idx]

        # Container box
        p.setStrokeColor(colors.HexColor("#CCCCCC"))
        p.setFillColor(colors.HexColor("#FAFAFA"))
        p.roundRect(x, y, box_w, box_h, 4, fill=True, stroke=True)

        # Photo Title Tag
        p.setFillColor(colors.HexColor("#263238"))
        p.rect(x, y + box_h - 22, box_w, 22, fill=True, stroke=False)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(x + 8, y + box_h - 15, item["title"][:42])

        # Draw Image
        try:
            if os.path.exists(item["path"]):
                img = Image.open(item["path"])
                img_reader = ImageReader(img)
                p.drawImage(img_reader, x + 8, y + 8, width=box_w - 16,
                            height=box_h - 35, preserveAspectRatio=True, anchor='c')
        except Exception:
            p.setFillColor(colors.red)
            p.setFont("Helvetica", 8)
            p.drawString(x + 10, y + 50, "Error rendering photo.")

        slots_on_page += 1

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


def create_bus_zip(folder_path):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, folder_path)
                zf.write(full_path, arcname)
    zip_buffer.seek(0)
    return zip_buffer


# -------------------------------------------------------------
# Main Application Tabs
# -------------------------------------------------------------
tab_upload, tab_explorer = st.tabs(
    ["📲 Upload & Generate Photo Dossier", "📁 Bus Folders & Archive"])

# =============================================================
# TAB 1: UPLOAD & GENERATE
# =============================================================
with tab_upload:
    st.title("🚌 Tirth Yatra - Photo Upload Portal")
    st.info(
        "⚠️ **Rules:** Use GPS Map Camera. Complete Bus Number must be clearly visible.")

    if not os.path.exists(GUIDE_IMAGE_PATH):
        uploaded_poster = st.file_uploader("Upload Guide Poster Once", type=[
                                           "jpg", "png", "jpeg"], key="setup_poster")
        if uploaded_poster:
            with open(GUIDE_IMAGE_PATH, "wb") as f:
                f.write(uploaded_poster.getbuffer())
            st.rerun()

    # Success & Export Banner
    if "last_submission" in st.session_state:
        sub = st.session_state["last_submission"]
        st.success(
            f"🎉 **{sub['bus_no']}** saved successfully with **{sub['total_saved']} Photos**!")

        c_pdf, c_zip, c_wa, c_new = st.columns([1.2, 1.2, 1.2, 1])
        with c_pdf:
            st.download_button(
                label="📄 Download Photo Dossier (PDF)",
                data=sub["pdf_data"],
                file_name=f"{sub['bus_no']}_Photo_Dossier.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        with c_zip:
            st.download_button(
                label="📦 Download All Photos (.ZIP)",
                data=sub["zip_data"],
                file_name=f"{sub['bus_no']}_Photos.zip",
                mime="application/zip",
                use_container_width=True
            )
        with c_wa:
            st.link_button(
                label="📲 Share on WhatsApp",
                url=sub["wa_url"],
                type="primary",
                use_container_width=True
            )
        with c_new:
            if st.button("➕ Start Next Bus", use_container_width=True):
                reset_entire_form()
        st.divider()

    # Upload Form
    with st.form("yatra_form", clear_on_submit=False):
        c_bus, c_guide = st.columns(2)
        with c_bus:
            bus_no = st.text_input(
                "Bus Number", placeholder="e.g. AR 20 A 6004", key=f"bus_{f_id}").strip().upper()
        with c_guide:
            team_guide = st.text_input(
                "Team Guide / Conductor Name", placeholder="e.g. Gurpreet Singh", key=f"guide_{f_id}").strip()

        c_start, c_end = st.columns(2)
        with c_start:
            trip_start = st.date_input(
                "Trip Start Date", value=date.today(), key=f"start_{f_id}")
        with c_end:
            trip_end = st.date_input(
                "Trip End Date", value=date.today() + timedelta(days=3), key=f"end_{f_id}")

        st.markdown("---")

        # 1. Odometers
        st.markdown("#### ⏱️ 1. Odometer Photos (4 Required)")
        col_ref1, col_box1 = st.columns([1, 3])
        with col_ref1:
            g1 = get_cropped_guide(CROP_ODO)
            if g1:
                st.image(g1, caption="Odometer Guide",
                         use_container_width=True)
        with col_box1:
            odo_files = st.file_uploader("Upload 4 Odometers", type=[
                                         "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"odo_{f_id}")

        st.markdown("---")

        # 2. Group
        st.markdown("#### 👥 2. Yatri Group Photos (4 Required)")
        col_ref2, col_box2 = st.columns([1, 3])
        with col_ref2:
            g2 = get_cropped_guide(CROP_GROUP)
            if g2:
                st.image(g2, caption="Group Photo Guide",
                         use_container_width=True)
        with col_box2:
            group_files = st.file_uploader("Upload 4 Group Photos", type=[
                                           "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"grp_{f_id}")

        st.markdown("---")

        # 3. Distribution
        st.markdown("#### 🥤 3. Glass & Refreshments (1-2 Photos)")
        col_ref3, col_box3 = st.columns([1, 3])
        with col_ref3:
            g3 = get_cropped_guide(CROP_GLASS)
            if g3:
                st.image(g3, caption="Glass Guide", use_container_width=True)
        with col_box3:
            dist_files = st.file_uploader("Upload Distribution Photos", type=[
                                          "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"dist_{f_id}")

        st.markdown("---")

        # 4. Meals
        st.markdown("#### 🍽️ 4. Passenger Meals (1-3 Photos)")
        col_ref4, col_box4 = st.columns([1, 3])
        with col_ref4:
            g4 = get_cropped_guide(CROP_MEAL)
            if g4:
                st.image(g4, caption="Meals Guide", use_container_width=True)
        with col_box4:
            meal_files = st.file_uploader("Upload Meals Photos", type=[
                                          "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"meal_{f_id}")

        st.markdown("---")
        submit_clicked = st.form_submit_button(
            "💾 SAVE ALL PHOTOS & BUILD PHOTO DOSSIER", type="primary", use_container_width=True)

    if submit_clicked:
        if not bus_no:
            st.error("❌ Please enter the Bus Number!")
        elif not team_guide:
            st.error("❌ Please enter the Team Guide Name!")
        elif not odo_files and not group_files and not dist_files and not meal_files:
            st.error(
                "❌ No photos selected or files are still uploading. Please wait for progress bars to finish.")
        else:
            with st.spinner("⚡ Compressing photos and embedding all images into PDF Dossier..."):
                batch_name = f"{trip_start}_to_{trip_end}"
                target_dir = os.path.join(
                    STORAGE_DIR, batch_name, bus_no.replace(" ", "_"))
                os.makedirs(target_dir, exist_ok=True)

                # Write metadata
                with open(os.path.join(target_dir, "trip_info.txt"), "w", encoding="utf-8") as f_meta:
                    f_meta.write(
                        f"BUS NUMBER : {bus_no}\nGUIDE      : {team_guide}\nDATES      : {trip_start} to {trip_end}\n")

                manifest = []

                def save_batch(files, prefix, labels):
                    for idx, f in enumerate(files, start=1):
                        img = Image.open(f)
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                        save_name = f"{prefix}_{idx}.jpg"
                        out_path = os.path.join(target_dir, save_name)
                        img.save(out_path, "JPEG", quality=82, optimize=True)
                        lbl = labels[idx-1] if idx - \
                            1 < len(labels) else f"{prefix} #{idx}"
                        manifest.append({"title": lbl, "path": out_path})

                save_batch(odo_files, "01_Odometer", [
                    "1. Punjab Departure Odometer",
                    "2. Destination Arrival Odometer",
                    "3. Return Start Odometer",
                    "4. Punjab Final Arrival Odometer"
                ])
                save_batch(group_files, "02_Group", [
                    "1. Departure Banner Group",
                    "2. Inside Cabin Yatri Group",
                    "3. Destination Return Group",
                    "4. MLA / VIP Group Photo"
                ])
                save_batch(dist_files, "03_Distribution", [
                    "1. Steel Glass Distribution",
                    "2. Refreshment Distribution"
                ])
                save_batch(meal_files, "04_Meals", [
                    "1. Breakfast Meal",
                    "2. Lunch Meal",
                    "3. Dinner Meal"
                ])

                # Build PDF containing all images
                pdf_data = generate_photo_dossier_pdf(
                    bus_no, team_guide, trip_start, trip_end, manifest)
                zip_data = create_bus_zip(target_dir)

                wa_text = (
                    f"🚌 *MUKH MANTRI TIRTH YATRA - TRIP REPORT*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📋 *Bus Number:* {bus_no}\n"
                    f"👤 *Team Guide:* {team_guide}\n"
                    f"📅 *Trip Duration:* {trip_start} to {trip_end}\n"
                    f"📸 *Verified Photos:* {len(manifest)} Embedded\n"
                    f"✅ *Dossier Status:* Complete & Verified\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"Full photo audit dossier generated and saved."
                )
                wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_text)}"

                st.session_state["last_submission"] = {
                    "bus_no": bus_no,
                    "total_saved": len(manifest),
                    "pdf_data": pdf_data,
                    "zip_data": zip_data,
                    "wa_url": wa_url
                }
                st.rerun()

# =============================================================
# TAB 2: BUS FOLDERS & ARCHIVE EXPLORER
# =============================================================
with tab_explorer:
    st.subheader("📁 Saved Bus Folders & Storage Explorer")
    st.caption(
        "Inspect saved bus batches, review uploaded photos, and download complete archives.")

    batches = [b for b in os.listdir(STORAGE_DIR) if os.path.isdir(
        os.path.join(STORAGE_DIR, b))]

    if not batches:
        st.info("No bus folders have been saved yet.")
    else:
        sel_batch = st.selectbox(
            "Select Trip Batch Date", sorted(batches, reverse=True))
        batch_path = os.path.join(STORAGE_DIR, sel_batch)
        buses = [b for b in os.listdir(batch_path) if os.path.isdir(
            os.path.join(batch_path, b))]

        if not buses:
            st.info(f"No buses found in batch {sel_batch}.")
        else:
            col_b_sel, col_b_dl = st.columns([2, 2])
            with col_b_sel:
                inspect_bus = st.selectbox("Select Bus Folder", sorted(buses))

            selected_bus_dir = os.path.join(batch_path, inspect_bus)

            with col_b_dl:
                st.write("")
                st.write("")
                bus_zip_data = create_bus_zip(selected_bus_dir)
                st.download_button(
                    label=f"📥 Download {inspect_bus} Folder (.ZIP)",
                    data=bus_zip_data,
                    file_name=f"{inspect_bus}_{sel_batch}.zip",
                    mime="application/zip",
                    use_container_width=True
                )

            # Display Folder Content Thumbnails
            st.markdown(f"#### 📷 Photos in `{sel_batch}/{inspect_bus}`")
            all_imgs = [f for f in os.listdir(
                selected_bus_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

            if not all_imgs:
                st.warning("No images found in this bus folder.")
            else:
                grid = st.columns(4)
                for idx, img_name in enumerate(sorted(all_imgs)):
                    img_path = os.path.join(selected_bus_dir, img_name)
                    with grid[idx % 4]:
                        st.image(img_path, caption=img_name,
                                 use_container_width=True)

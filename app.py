import streamlit as st
import os
import io
import zipfile
import urllib.parse
from datetime import date, datetime, timedelta
from PIL import Image, ImageDraw, ImageOps

st.set_page_config(page_title="Tirth Yatra Fleet Portal",
                   layout="wide", page_icon="🚌")

STORAGE_DIR = "Bus_Folders"
os.makedirs(STORAGE_DIR, exist_ok=True)

if "bus_index" not in st.session_state:
    st.session_state["bus_index"] = 0


def start_fresh_bus():
    st.session_state["bus_index"] += 1
    st.session_state.pop("completed_trip", None)
    st.rerun()


b_idx = st.session_state["bus_index"]

# Pure-Pillow PDF generator - stamps every photo into a multi-page PDF


def create_image_pdf(bus_no, guide, start_d, end_d, photo_manifest):
    pdf_pages = []

    # Page 1: Summary Sheet
    cover = Image.new("RGB", (1240, 1754), color=(245, 247, 250))
    draw = ImageDraw.Draw(cover)
    draw.rectangle([(0, 0), (1240, 180)], fill=(13, 71, 161))
    draw.text((60, 50), "MUKH MANTRI TIRTH YATRA SCHEME", fill=(255, 255, 255))
    draw.text((60, 110), "Official Transport Department - Photo Verification Dossier",
              fill=(200, 220, 255))

    draw.rectangle([(60, 230), (1180, 520)], fill=(
        255, 255, 255), outline=(200, 200, 200), width=3)
    meta_text = (
        f"BUS REGISTRATION  : {bus_no}\n\n"
        f"CONDUCTOR / GUIDE : {guide}\n\n"
        f"JOURNEY DATES     : {start_d} to {end_d}\n\n"
        f"TOTAL PHOTOS      : {len(photo_manifest)} Verified Images\n\n"
        f"DATE PROCESSED    : {datetime.now().strftime('%d-%b-%Y %I:%M %p')}"
    )
    draw.text((90, 260), meta_text, fill=(20, 20, 20))

    draw.text((60, 560), "VERIFIED PHOTO MANIFEST:", fill=(13, 71, 161))
    y_line = 610
    for idx, item in enumerate(photo_manifest, 1):
        draw.text((80, y_line),
                  f"[{idx:02d}]  {item['label']}", fill=(50, 50, 50))
        y_line += 40
        if y_line > 1650:
            break

    pdf_pages.append(cover)

    # Pages 2+: Every Photo Stamped on Full A4 Page
    for item in photo_manifest:
        try:
            with Image.open(item["path"]) as raw_img:
                img = ImageOps.exif_transpose(raw_img)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                page = Image.new("RGB", (1240, 1754), color=(250, 250, 250))
                p_draw = ImageDraw.Draw(page)
                p_draw.rectangle([(0, 0), (1240, 110)], fill=(38, 50, 56))
                p_draw.text(
                    (40, 35), f"BUS: {bus_no}  |  {item['label'].upper()}", fill=(255, 255, 255))

                img.thumbnail((1160, 1580), Image.Resampling.LANCZOS)
                pos_x = (1240 - img.width) // 2
                pos_y = 120 + (1600 - img.height) // 2
                page.paste(img, (pos_x, pos_y))
                pdf_pages.append(page)
        except Exception:
            continue

    pdf_buffer = io.BytesIO()
    if pdf_pages:
        pdf_pages[0].save(
            pdf_buffer,
            format="PDF",
            save_all=True,
            append_images=pdf_pages[1:],
            resolution=100.0
        )
    pdf_buffer.seek(0)
    return pdf_buffer


def make_bus_zip(dir_path):
    z_buf = io.BytesIO()
    with zipfile.ZipFile(z_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dir_path):
            for f in files:
                fp = os.path.join(root, f)
                zf.write(fp, os.path.relpath(fp, dir_path))
    z_buf.seek(0)
    return z_buf


# Header & Top Button
col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    st.title("🚌 Tirth Yatra Fleet Portal")
with col_t2:
    st.write("")
    if st.button("➕ START NEW BUS (RESET)", type="primary", use_container_width=True):
        start_fresh_bus()

# Persistent Download Banner After Submission
if "completed_trip" in st.session_state:
    done = st.session_state["completed_trip"]
    st.success(f"🎉 **{done['bus']}** saved with **{done['count']} photos**!")

    col_d1, col_d2, col_d3 = st.columns([1.5, 1.5, 1])
    with col_d1:
        st.download_button(
            label="📄 1. DOWNLOAD PHOTO PDF (ALL PICTURES INSIDE)",
            data=done["pdf_data"],
            file_name=f"{done['bus']}_Full_Photo_Dossier.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    with col_d2:
        st.download_button(
            label="📦 DOWNLOAD FOLDER (.ZIP)",
            data=done["zip_data"],
            file_name=f"{done['bus']}_Photos.zip",
            mime="application/zip",
            use_container_width=True
        )
    with col_d3:
        st.link_button("📲 OPEN WHATSAPP",
                       url=done["wa_link"], use_container_width=True)

    st.info("💡 **WhatsApp Instruction:** Tap Button 1 to download the PDF, then tap Button 2, hit 📎 ➔ **Document**, and send the downloaded PDF.")
    st.divider()

# Input Form
with st.form("bus_entry_form", clear_on_submit=False):
    st.subheader("📝 Bus Details")
    f_c1, f_c2 = st.columns(2)
    with f_c1:
        b_num = st.text_input(
            "Bus Number", placeholder="e.g. AR 20 A 6004", key=f"b_{b_idx}").strip().upper()
    with f_c2:
        g_name = st.text_input("Team Guide / Conductor Name",
                               placeholder="e.g. Gurpreet Singh", key=f"g_{b_idx}").strip()

    f_d1, f_d2 = st.columns(2)
    with f_d1:
        s_date = st.date_input(
            "Trip Start Date", value=date.today(), key=f"sd_{b_idx}")
    with f_d2:
        e_date = st.date_input(
            "Trip End Date", value=date.today() + timedelta(days=3), key=f"ed_{b_idx}")

    st.markdown("---")
    st.markdown("#### ⏱️ 1. Odometer Photos (4 Required)")
    up_odos = st.file_uploader("Select 4 Odometers", type=[
                               "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"up_odo_{b_idx}")

    st.markdown("---")
    st.markdown("#### 👥 2. Yatri Group Photos (4 Required)")
    up_grps = st.file_uploader("Select 4 Group Photos", type=[
                               "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"up_grp_{b_idx}")

    st.markdown("---")
    st.markdown("#### 🥤 3. Steel Glass & Refreshments")
    up_dsts = st.file_uploader("Select Distribution Photos", type=[
                               "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"up_dst_{b_idx}")

    st.markdown("---")
    st.markdown("#### 🍽️ 4. Passenger Meals")
    up_mels = st.file_uploader("Select Meals Photos", type=[
                               "jpg", "jpeg", "png"], accept_multiple_files=True, key=f"up_mel_{b_idx}")

    st.markdown("---")
    submit_btn = st.form_submit_button(
        "💾 SAVE ALL PHOTOS & BUILD PHOTO PDF", type="primary", use_container_width=True)

if submit_btn:
    if not b_num:
        st.error("❌ Please type the Bus Number.")
    elif not g_name:
        st.error("❌ Please type the Guide / Conductor Name.")
    elif not up_odos and not up_grps and not up_dsts and not up_mels:
        st.error("❌ No photos selected! Please select photos before clicking Save.")
    else:
        with st.spinner("⏳ Stitching full-size images into PDF..."):
            folder_name = b_num.replace(" ", "_")
            batch_date_tag = f"{s_date}_to_{e_date}"
            save_dir = os.path.join(STORAGE_DIR, batch_date_tag, folder_name)
            os.makedirs(save_dir, exist_ok=True)

            manifest = []

            def save_and_tag(files, prefix, labels):
                for i, f in enumerate(files, 1):
                    with Image.open(f) as im:
                        im = ImageOps.exif_transpose(im)
                        if im.mode in ("RGBA", "P"):
                            im = im.convert("RGB")
                        im.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                        filename = f"{prefix}_{i}.jpg"
                        dest = os.path.join(save_dir, filename)
                        im.save(dest, "JPEG", quality=85)
                        lbl = labels[i-1] if i - \
                            1 < len(labels) else f"{prefix} #{i}"
                        manifest.append({"label": lbl, "path": dest})

            save_and_tag(up_odos, "01_Odo", ["1. Punjab Departure Odometer", "2. Destination Arrival Odometer",
                         "3. Return Start Odometer", "4. Punjab Final Arrival Odometer"])
            save_and_tag(up_grps, "02_Group", [
                         "1. Departure Banner Group", "2. Inside Cabin Yatri Group", "3. Destination Return Group", "4. MLA / VIP Group Photo"])
            save_and_tag(up_dsts, "03_Glass", [
                         "1. Steel Glass Distribution", "2. Refreshment Distribution"])
            save_and_tag(up_mels, "04_Meal", [
                         "1. Breakfast Photo", "2. Lunch Photo", "3. Dinner Photo"])

            pdf_bytes = create_image_pdf(
                b_num, g_name, s_date, e_date, manifest)
            zip_bytes = make_bus_zip(save_dir)

            wa_msg = (
                f"🚌 *MUKH MANTRI TIRTH YATRA REPORT*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 *Bus Number:* {b_num}\n"
                f"👤 *Team Guide:* {g_name}\n"
                f"📅 *Dates:* {s_date} to {e_date}\n"
                f"📸 *Photos Logged:* {len(manifest)} Verified Images\n"
                f"✅ Complete Photo PDF Dossier Generated.\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            wa_encoded = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_msg)}"

            st.session_state["completed_trip"] = {
                "bus": b_num,
                "count": len(manifest),
                "pdf_data": pdf_bytes,
                "zip_data": zip_bytes,
                "wa_link": wa_encoded
            }
            st.rerun()

# Saved Bus Folders Section
st.markdown("---")
st.subheader("📁 Saved Bus Folders on System")

batches = [d for d in os.listdir(STORAGE_DIR) if os.path.isdir(
    os.path.join(STORAGE_DIR, d))]
if not batches:
    st.caption("No bus folders saved yet.")
else:
    for b_batch in sorted(batches, reverse=True):
        b_dir = os.path.join(STORAGE_DIR, b_batch)
        buses = [b for b in os.listdir(
            b_dir) if os.path.isdir(os.path.join(b_dir, b))]

        with st.expander(f"🗓️ Trip Batch: {b_batch} ({len(buses)} Buses Saved)", expanded=True):
            cols = st.columns(3)
            for idx, b_name in enumerate(sorted(buses)):
                bus_path = os.path.join(b_dir, b_name)
                pic_count = len([f for f in os.listdir(
                    bus_path) if f.endswith('.jpg')])
                with cols[idx % 3]:
                    st.write(f"🚌 **{b_name}** ({pic_count} photos)")
                    z_data = make_bus_zip(bus_path)
                    st.download_button(
                        label=f"📥 Download {b_name} (.ZIP)",
                        data=z_data,
                        file_name=f"{b_name}_{b_batch}.zip",
                        mime="application/zip",
                        key=f"zip_{b_batch}_{b_name}"
                    )

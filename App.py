# streamlit_app.py
import os
import io
from typing import List, Dict, Any, Optional
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import numpy as np

st.set_page_config(page_title="Space Safety Scanner", layout="wide")

BACKEND_URL = os.environ.get("BACKEND_URL", "").strip()  # e.g. http://your-backend.com/api/detect

st.title("Space Safety Scanner")
st.write("Upload an image to scan for safety objects. (If BACKEND_URL is unset, a demo/dummy result will be shown.)")

uploaded = st.file_uploader("Select image", type=["png", "jpg", "jpeg"])

def draw_boxes(img: Image.Image, detections: List[Dict[str,Any]]):
    out = img.convert("RGBA")
    draw = ImageDraw.Draw(out)
    w, h = img.size
    # try to load a small font; Streamlit server may not have custom fonts
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", size=14)
    except Exception:
        font = ImageFont.load_default()
    for d in detections:
        box = d.get("box")
        label = d.get("label", "obj")
        conf = d.get("confidence", 0.0)
        if not box:
            continue
        # box assumed normalized [0..1]
        x = int(box["x"] * w)
        y = int(box["y"] * h)
        bw = int(box["w"] * w)
        bh = int(box["h"] * h)
        rect = [x, y, x + bw, y + bh]
        # draw rectangle and label background
        draw.rectangle(rect, outline=(255, 80, 80), width=3)
        text = f"{label} {conf*100:.1f}%"
        text_w, text_h = draw.textsize(text, font=font)
        draw.rectangle([x, max(0, y - text_h - 6), x + text_w + 6, y], fill=(255,80,80))
        draw.text((x + 3, max(0, y - text_h - 4)), text, fill="white", font=font)
    return out

def call_backend(file_bytes: bytes) -> Optional[Dict[str,Any]]:
    if not BACKEND_URL:
        return None
    try:
        files = {"image": ("upload.jpg", file_bytes, "image/jpeg")}
        resp = requests.post(BACKEND_URL, files=files, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Error calling backend: {e}")
        return None

if uploaded:
    image = Image.open(uploaded).convert("RGB")
    st.subheader("Preview")
    st.image(image, use_column_width=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Send to server"):
            with st.spinner("Detecting..."):
                buf = io.BytesIO()
                image.save(buf, format="JPEG")
                buf.seek(0)
                result = call_backend(buf.read())
                # backend result expected: {"results": [ {label, confidence, box:{x,y,w,h}}, ... ]}
                if result is None:
                    st.info("No backend URL set — showing demo results.")
                elif result.get("error"):
                    st.error("Backend error: " + str(result.get("error")))
                else:
                    detections = result.get("results", [])
                    boxed = draw_boxes(image, detections)
                    st.image(boxed, use_column_width=True)
                    st.subheader("Detections")
                    for d in detections:
                        st.write(f"- **{d.get('label','')}** — {d.get('confidence',0)*100:.1f}%")
    # If no backend or user didn't click Send, show demo detections
    if not BACKEND_URL:
        st.warning("No BACKEND_URL set — showing demo detection (not real).")
        demo = [
            {"label":"hardhat","confidence":0.92,"box":{"x":0.12,"y":0.18,"w":0.25,"h":0.28}},
            {"label":"person","confidence":0.88,"box":{"x":0.42,"y":0.12,"w":0.26,"h":0.6}},
        ]
        boxed = draw_boxes(image, demo)
        st.image(boxed, use_column_width=True)
        st.subheader("Demo Detections")
        for d in demo:
            st.write(f"- **{d.get('label','')}** — {d.get('confidence',0)*100:.1f}%")
else:
    st.info("Upload an image to get started.")

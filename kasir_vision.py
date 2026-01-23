import cv2
import time
import json
import os
import numpy as np
import threading
import sys

from ultralytics import YOLO
from insightface.app import FaceAnalysis
from PyQt5.QtWidgets import QApplication

from kasir_ui import KasirApp

# ==========================
# CONFIG
# ==========================
FACE_PIP_SIZE = (320, 260)
FACE_PIP_MARGIN = 10

CAM_INDICES = [0, 1]
RESOLUTIONS = [
    (2560, 1440),  # BARANG
    (352, 288)     # FACE
]
FPS_SETTINGS = [60, 30]

FACE_DIR = "faces"
FACE_THRESH = 0.5

# ==========================
# LOAD FACE DB
# ==========================
face_db = {}
if os.path.exists(FACE_DIR):
    for filename in os.listdir(FACE_DIR):
        if filename.endswith('.npy'):
            name = filename.replace('.npy', '')
            face_db[name] = os.path.join(FACE_DIR, filename)
print(f"[OK] Loaded {len(face_db)} faces from {FACE_DIR}/")

def cosine_sim(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def match_face(emb):
    best, score = "Unknown", 0
    for name, path in face_db.items():
        db = np.load(path)
        s = cosine_sim(emb, db)
        if s > score:
            best, score = name, s
    return best if score > FACE_THRESH else "Unknown"

# ==========================
# INIT FACE MODEL (GPU)
# ==========================
face_app = FaceAnalysis(
    name="buffalo_l",
    providers=["CUDAExecutionProvider"]
)
face_app.prepare(ctx_id=0, det_size=(640, 640))

# ==========================
# INIT YOLO + BYTE TRACK
# ==========================
yolo = YOLO("best.pt", task="detect")

# ==========================
# INIT CAMERAS
# ==========================
caps = []
for idx, (w, h), fps in zip(CAM_INDICES, RESOLUTIONS, FPS_SETTINGS):
    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"Kamera index {idx} gagal")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_FPS, fps)
    caps.append(cap)

print("[OK] Dua kamera aktif")

# ==========================
# INIT UI IN MAIN THREAD
# ==========================
app = QApplication(sys.argv)
ui = KasirApp()
ui.show()

# ==========================
# TRACKING STATE
# ==========================
seen_track_ids = set()

# ==========================
# FPS COUNTER
# ==========================
prev_time = time.time()

# ==========================
# CAMERA THREAD
# ==========================
def camera_loop():
    global prev_time
    while True:
        ret0, frame_barang = caps[0].read()
        ret1, frame_face = caps[1].read()
        if not ret0 or not ret1:
            continue

        # ========== FACE ==========
        faces = face_app.get(frame_face)
        for f in faces:
            name = match_face(f.embedding)
            ui.sig_set_customer.emit(name)

            x1, y1, x2, y2 = map(int, f.bbox)
            cv2.rectangle(frame_face, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame_face,
                name,
                (x1, y1 - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

        # ========== FACE → PIP ==========
        face_small = cv2.resize(frame_face, FACE_PIP_SIZE)
        px, py = FACE_PIP_MARGIN, FACE_PIP_MARGIN
        ph, pw = face_small.shape[:2]
        frame_barang[py:py+ph, px:px+pw] = face_small

        # ========== YOLO + BYTE TRACK ==========
        results = yolo.track(
            frame_barang,
            persist=True,
            tracker="bytetrack.yaml",
            conf=0.5,
            imgsz=640,
            device=0,
            verbose=False
        )[0]

        # Build live counts per class for current frame
        counts = {}
        boxes = results.boxes
        if boxes is not None and boxes.cls is not None:
            for cls in boxes.cls:
                label = yolo.names[int(cls)]
                counts[label] = counts.get(label, 0) + 1

        # Send live counts to UI (only currently detected objects shown)
        ui.sig_set_counts.emit(counts)

        # ========== DRAW ==========
        frame_barang = results.plot(img=frame_barang)

        # ========== FPS ==========
        now = time.time()
        fps = 1.0 / (now - prev_time)
        prev_time = now

        cv2.putText(
            frame_barang,
            f"FPS: {fps:.1f}",
            (10, frame_barang.shape[0] - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        # ========== SHOW ==========
        cv2.imshow("KASIRLESS", frame_barang)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            # Cleanup
            for c in caps:
                c.release()
            cv2.destroyAllWindows()
            app.quit()
            break

# Start camera thread
threading.Thread(target=camera_loop, daemon=True).start()

# ==========================
# RUN QT APP
# ==========================
sys.exit(app.exec_())

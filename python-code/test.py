import cv2
import numpy as np
import math



def get_globe_timeline_curv(r=200,deg=-90,cx=0,cy=0, steps=20):

    rad = math.radians(deg)
    flatening = math.sin(rad)
    ys = np.linspace(-r, r, steps)
    pts = []

    for y in ys:
        x = flatening * math.sqrt(r**2-y**2)
        pts.append([x + cx, y + cy])

    return np.array(pts, dtype=np.int32).reshape((-1, 1, 2))

def get_globe_timeline_curvs(r, cx=0, cy=0, deg_steps=15, draw_steps=30, frame=None, draw = False):
    color = (0, 255, 0)
    width = 2
    timelines = []
    for deg in range(-90, deg_steps+90, deg_steps):
        pts = get_globe_timeline_curv(r,deg,cx,cy,draw_steps)
        timelines.append(pts)

        if draw:
            color = (0, 255, 0)
            width = 2
            cv2.polylines(frame, [pts], False, color, width)

    return timelines

# def time_area_curve(r, deg, cx, cy, steps=100):
#     rad = math.radians(deg)
#     x_offset = r * math.sin(rad)

#     ys = np.linspace(-r, r, steps)
#     pts = []

#     for y in ys:
#         inside = r*r - y*y
#         if inside < 0:
#             continue
#         x_local = math.sqrt(inside)
#         x = cx + x_offset
#         pts.append([x, cy + y])

#     return np.array(pts, dtype=np.int32).reshape((-1, 1, 2))

cap = cv2.VideoCapture(1)

if not cap.isOpened():
    raise RuntimeError("Webcam konnte nicht geöffnet werden")

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        break

    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    r = int(min(w, h) * 0.28)

    overlay = frame.copy()

    # Globus-Kontur
    # cv2.circle(overlay, (cx, cy), r, (0, 255, 0), 3, cv2.LINE_AA)

    # Meridiane / Zeitzonen in 15°-Schritten
    pts = get_globe_timeline_curvs(r,cx,cy,15,50,overlay,True)



    cv2.imshow("Globus Frontansicht", overlay)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# cv2.polylines(overlay, [pts], False, (0, 0, 255), 3)
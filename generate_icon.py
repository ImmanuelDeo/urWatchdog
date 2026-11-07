import os
import math
from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def create_urwatchdog_icon(output_dir="assets"):
    target_dir = os.path.join(BASE_DIR, output_dir)
    os.makedirs(target_dir, exist_ok=True)
    ico_path = os.path.join(target_dir, "urwatchdog.ico")
    png_path = os.path.join(target_dir, "urwatchdog.png")

    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Base squircle / rounded shield background
    # Background color: Deep dark midnight #0f172a
    bg_radius = 90
    bg_margin = 24
    draw.rounded_rectangle(
        [bg_margin, bg_margin, size - bg_margin, size - bg_margin],
        radius=bg_radius,
        fill=(15, 23, 42, 255),
        outline=(56, 189, 248, 220), # Subtle cyan border
        width=10
    )

    # Subtle inner dark card
    inner_margin = 38
    draw.rounded_rectangle(
        [inner_margin, inner_margin, size - inner_margin, size - inner_margin],
        radius=bg_radius - 12,
        fill=(24, 24, 27, 255),
        outline=(30, 41, 59, 255),
        width=4
    )

    # 2. Geometric Watchdog Silhouette
    # Sleek angular cyber-canine profile facing right or frontal geometric crest
    # Let's draw an authoritative, sleek, symmetrical cyber-watchdog crest:
    # Center x: 256
    cx = 256

    # Shield / Crest backdrop in deep navy slate
    shield_pts = [
        (cx - 140, 150),
        (cx + 140, 150),
        (cx + 115, 340),
        (cx, 420),
        (cx - 115, 340)
    ]
    draw.polygon(shield_pts, fill=(30, 41, 59, 255), outline=(56, 189, 248, 180), width=6)

    # Watchdog Face / Ears (Sharp, stylized geometric polygons)
    # Left Ear:
    left_ear = [(cx - 95, 130), (cx - 45, 185), (cx - 105, 215)]
    draw.polygon(left_ear, fill=(56, 189, 248, 255))

    # Right Ear:
    right_ear = [(cx + 95, 130), (cx + 45, 185), (cx + 105, 215)]
    draw.polygon(right_ear, fill=(56, 189, 248, 255))

    # Forehead / Brow:
    forehead = [
        (cx - 65, 185),
        (cx + 65, 185),
        (cx + 45, 255),
        (cx, 275),
        (cx - 45, 255)
    ]
    draw.polygon(forehead, fill=(14, 165, 233, 255))

    # Cheeks / Jaw:
    left_jaw = [(cx - 90, 235), (cx - 35, 275), (cx - 20, 345), (cx - 75, 310)]
    right_jaw = [(cx + 90, 235), (cx + 35, 275), (cx + 20, 345), (cx + 75, 310)]
    draw.polygon(left_jaw, fill=(2, 132, 199, 255))
    draw.polygon(right_jaw, fill=(2, 132, 199, 255))

    # Snout / Nose bridge:
    snout = [
        (cx, 275),
        (cx + 28, 335),
        (cx, 370),
        (cx - 28, 335)
    ]
    draw.polygon(snout, fill=(186, 230, 253, 255))

    # Sharp Watchful Eyes (Glowing Cyan / Teal slits)
    left_eye = [(cx - 52, 222), (cx - 24, 232), (cx - 48, 236)]
    right_eye = [(cx + 52, 222), (cx + 24, 232), (cx + 48, 236)]
    draw.polygon(left_eye, fill=(255, 255, 255, 255))
    draw.polygon(right_eye, fill=(255, 255, 255, 255))

    # Power / Watchdog radar node at the bottom tip
    node_cx, node_cy = cx, 400
    draw.ellipse([node_cx - 10, node_cy - 10, node_cx + 10, node_cy + 10], fill=(56, 189, 248, 255))
    draw.ellipse([node_cx - 5, node_cy - 5, node_cx + 5, node_cy + 5], fill=(255, 255, 255, 255))

    # Save high-res PNG
    img.save(png_path, "PNG")

    # Multi-resolution ICO export
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=icon_sizes)

    print(f"Generated icon:\n - PNG: {png_path}\n - ICO: {ico_path}")
    return ico_path

if __name__ == "__main__":
    create_urwatchdog_icon()

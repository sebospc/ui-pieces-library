# Usage: python3 measure.py <shot.png> [out.json] [--width-pt=393]
# Measures the structure of one phone screenshot into a JSON file: sizes, spacing, type, alignment, radii, colours, contrast.
# The same code and version runs on every shot, so two screens can be compared like with like.
import json, subprocess, sys
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

VERSION = "0.1.2"
STATUS_BAR_PT = 54
RING_READS = {"O", "o", "0", "•", "○", "◦"}
HERE = Path(__file__).resolve().parent
ASCENDERS, DESCENDERS = set("bdfhklß"), set("gjpqyQ,;")
CAPS = set("ABCDEFGHIJKLMNOPRSTUVWXYZ0123456789ÀÁÂÄÉÈÊÍÓÖÚÜÑ")
# Calibration from test_measure.py --fit on the even half of the catalog shots (type size ÷ ink height).
SIZE_PER_HEIGHT = {"ascender": 1.34, "cap": 1.40, "x": 1.90}  # x: no sample yet, from font metrics
WEIGHT_STROKE = {"regular": 0.118, "semibold": 0.159, "bold": 0.187, "heavy": 0.211}  # stroke ÷ ink height


PHONE_WIDTHS_PT = (320, 375, 390, 393, 402, 414, 428, 430, 440)


def device_scale(width_px: int, width_pt: float | None = None) -> tuple[float, bool]:
    # A native shot is 2x or 3x a known phone width; anything else (a resized reference) is read as 393 pt and flagged.
    if width_pt:
        return width_px / width_pt, False
    native = [width_px / w for w in PHONE_WIDTHS_PT if width_px / w in (2, 3)]
    return (native[0], False) if native else (width_px / 393, True)


def hex_of(rgb) -> str:
    return "#" + "".join(f"{int(round(c)):02X}" for c in rgb)


def luminance(rgb) -> float:
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (v / 255 for v in rgb)]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a, b) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def page_colour(pixels: np.ndarray) -> np.ndarray:
    # The middle band, so the status bar and the system's top and bottom bars do not win.
    height = pixels.shape[0]
    band = pixels[height // 5: height * 9 // 10].reshape(-1, 3)
    keys, counts = np.unique(band // 4, axis=0, return_counts=True)
    return keys[counts.argmax()] * 4 + 2


def read_text(path: Path) -> list[dict]:
    out = subprocess.run([str(HERE / "vision_text"), str(path)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def corner_radius(mask: np.ndarray) -> float:
    # Each corner's edge inset per row, fitted to a circle; the median of the four corners, in px.
    height, width = mask.shape
    reach = min(height, width) // 2
    corners = [mask, mask[:, ::-1], mask[::-1, :], mask[::-1, ::-1]]
    rows = np.arange(reach) + 0.5
    found = []
    for corner in corners:
        filled = corner[:reach, :reach]
        insets = np.where(filled.any(axis=1), filled.argmax(axis=1), reach).astype(float)
        candidates = np.arange(0, reach + 0.5, 0.5)
        errors = [np.sum((np.where(rows < r, r - np.sqrt(np.maximum(0, r * r - (r - rows) ** 2)), 0) - insets) ** 2)
                  for r in candidates]
        found.append(candidates[int(np.argmin(errors))])
    return float(np.median(found))


def surfaces(pixels: np.ndarray, page: np.ndarray, text_boxes: list, scale: int) -> list[dict]:
    smallest = (6 * scale) ** 2
    keys = (pixels // 8).reshape(-1, 3)
    bins, counts = np.unique(keys, axis=0, return_counts=True)
    found = []
    for key in bins[counts >= smallest * 0.7]:
        colour = key * 8 + 4
        if np.abs(colour - page).max() <= 8:
            continue
        mask = np.abs(pixels - colour).max(axis=2) <= 8
        labels, _ = ndimage.label(mask)
        for index, box in enumerate(ndimage.find_objects(labels), start=1):
            region = labels[box] == index
            height, width = region.shape
            # A surface is a filled shape; glyphs and anti-aliased edges are thin and sparse.
            if min(height, width) < 6 * scale or region.mean() < 0.7:
                continue
            x, y = box[1].start, box[0].start
            if any(tx <= x and ty <= y and x + width <= tx + tw and y + height <= ty + th for tx, ty, tw, th in text_boxes):
                continue
            rect = [round(v / scale, 1) for v in (x, y, width, height)]
            # Two colour bins can hold the same anti-aliased shape.
            if any(seen["rect"] == rect for seen in found):
                continue
            fill = pixels[box][region].mean(axis=0)
            radius = corner_radius(region)
            found.append({
                "rect": rect,
                "colour": hex_of(fill),
                "radius": "capsule" if radius >= min(height, width) / 2 - scale else round(radius / scale, 1),
            })
    return found


def stroke_width(ink: np.ndarray) -> float:
    edge = ink & ~ndimage.binary_erosion(ink)
    return 2 * ink.sum() / max(edge.sum(), 1)


def only_this_line(ink: np.ndarray, core_box: tuple) -> np.ndarray:
    # Keep the glyphs that reach into Vision's box; drop neighbours and edges that cross the crop border.
    labels, _ = ndimage.label(ink, structure=np.ones((3, 3)))
    top, bottom, left, right = (int(v) for v in core_box)
    inside = set(np.unique(labels[max(top, 0):bottom, max(left, 0):right])) - {0}
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])))
    return np.isin(labels, list(inside - border))


def measure_text(pixels: np.ndarray, line: dict, scale: int) -> dict | None:
    x, y, width, height = line["box"]
    top, bottom = int(max(0, y - height * 0.25)), int(min(pixels.shape[0], y + height * 1.25))
    left, right = int(max(0, x - 2 * scale)), int(min(pixels.shape[1], x + width + 2 * scale))
    crop = pixels[top:bottom, left:right].astype(float)
    if crop.size == 0:
        return None
    border = np.concatenate([crop[0], crop[-1], crop[:, 0], crop[:, -1]])
    behind = np.median(border, axis=0)
    distance = np.sqrt(((crop - behind) ** 2).sum(axis=2))
    if distance.max() < 20:
        return None
    ink = only_this_line(distance >= distance.max() * 0.5, (y - top, y + height - top, x - left, x + width - left))
    if not ink.any():
        return None
    # The stroke centre holds the drawn colour; the anti-aliased rim would pull it toward the background.
    core = crop[ink & (distance >= distance[ink].max() * 0.9)].astype(int)
    keys, counts = np.unique(core, axis=0, return_counts=True)
    colour = keys[counts.argmax()]
    row_ink = ink.sum(axis=1)
    rows = np.nonzero(row_ink)[0]
    letters = set(line["text"])
    if letters & DESCENDERS:
        # Descenders are thin rows under the line; the baseline is the last row where the body of the letters is.
        baseline = np.nonzero(row_ink >= row_ink.max() * 0.3)[0][-1]
    else:
        baseline = rows[-1]
    ink_height = baseline - rows[0] + 1
    shape = "ascender" if letters & ASCENDERS else "cap" if letters & CAPS else "x"
    size = ink_height / scale * SIZE_PER_HEIGHT[shape]
    stroke = stroke_width(ink[rows[0]: baseline + 1]) / ink_height
    weight = min(WEIGHT_STROKE, key=lambda name: abs(np.log(WEIGHT_STROKE[name] / stroke)))
    columns = np.nonzero(ink.any(axis=0))[0]
    return {
        "text": line["text"],
        "rect": [round((left + columns[0]) / scale, 1), round((top + rows[0]) / scale, 1),
                 round((columns[-1] - columns[0] + 1) / scale, 1), round(ink_height / scale, 1)],
        "size": round(size, 1), "weight": weight, "stroke": round(stroke, 4), "shape": shape,
        "colour": hex_of(colour), "behind": hex_of(behind), "contrast": round(contrast(colour, behind), 2),
    }


def counts_as_type(text: dict) -> bool:
    # The status bar is the system's type, and Vision reads a ring or dot before a word as "O" or "•", so the ink
    # height of that line is the ring's: neither says which type sizes the app uses.
    first_word = text["text"].split(" ", 1)[0]
    return (text["rect"][1] >= STATUS_BAR_PT and any(c.isalnum() for c in text["text"])
            and not (first_word in RING_READS and " " in text["text"]))


def size_groups(sizes: list[float]) -> list[float]:
    # The ink scan reads one type size as a spread (17.0, 17.4, 16.8): sizes within 1 pt of a group's first are one size.
    groups: list[list[float]] = []
    for size in sorted(sizes):
        if groups and size - groups[-1][0] <= 1:
            groups[-1].append(size)
        else:
            groups.append([size])
    return [round(float(np.median(group)), 1) for group in groups]


def alignment(left_edges: list[float]) -> dict:
    clusters: dict[float, int] = {}
    for edge in sorted(left_edges):
        home = next((c for c in clusters if abs(c - edge) <= 1), edge)
        clusters[home] = clusters.get(home, 0) + 1
    main = max(clusters, key=clusters.get) if clusters else None
    return {"left_edges": sorted(clusters), "main_edge": main,
            "main_share": round(clusters[main] / len(left_edges), 2) if main is not None else 0}


def measure(path: Path, width_pt: float | None = None) -> dict:
    pixels = np.asarray(Image.open(path).convert("RGB")).astype(int)
    scale, guessed = device_scale(pixels.shape[1], width_pt)
    page = page_colour(pixels)
    lines = read_text(path)
    texts = [t for t in (measure_text(pixels, line, scale) for line in lines) if t]
    shapes = surfaces(pixels, page, [line["box"] for line in lines], scale)
    sizes = size_groups([t["size"] for t in texts if counts_as_type(t)])
    # Pictures and bands that touch the screen edge bleed on purpose; they say nothing about the margin.
    content = [t["rect"][0] for t in texts] + [s["rect"][0] for s in shapes if s["rect"][0] >= 1]
    return {
        "frame": {"width": round(pixels.shape[1] / scale), "height": round(pixels.shape[0] / scale),
                  "scale": round(scale, 3), "scale_guessed": guessed},
        "page": hex_of(page),
        "texts": texts,
        "surfaces": shapes,
        "spacing": {"screen_margin": round(min(content), 1) if content else None},
        "type": {"sizes": sizes, "count": len(sizes)},
        "alignment": alignment([t["rect"][0] for t in texts]),
        "motion": "not measured",
        "words": [line["text"] for line in lines],
        "method": {"name": "design-library measurer", "version": VERSION, "at": date.today().isoformat()},
    }


if __name__ == "__main__":
    arguments = [a for a in sys.argv[1:] if not a.startswith("--width-pt=")]
    width = next((float(a.split("=")[1]) for a in sys.argv[1:] if a.startswith("--width-pt=")), None)
    result = json.dumps(measure(Path(arguments[0]), width), indent=1)
    if len(arguments) > 1:
        Path(arguments[1]).write_text(result + "\n")
    else:
        print(result)

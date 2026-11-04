# Measurer

Reads one phone screenshot and writes what its layout is made of: sizes, spacing, type, alignment, corner radii, colours and contrast. It keeps the structure of a screen, not its content.

```
python3 measure.py <shot.png> [out.json] [--width-pt=393]
```

Needs Python with numpy, Pillow and scipy. Text boxes come from Apple's Vision framework through `vision_text.swift` (macOS; build it with `swiftc vision_text.swift -o vision_text`).

## What it measures


| field | how | done when (on the calibration set) |
|---|---|---|
| frame | width in px ÷ device scale = width in pt (1170→390, 1179→393, 1206→402); status bar and home bar bands cut | scale found for every shot |
| tree | page colour = most common colour; surfaces = connected regions that differ from what is behind them by ΔE > 2 (`scipy.ndimage.label`), nested by containment; text boxes from Vision; small square regions near text = icon or dot | box edges within 1 pt for 95 % of boxes |
| spacing | gaps between siblings, screen margin (smallest left x of content), padding (text box inset in its surface) | within 1 pt for 95 % |
| type | size from the ink height of capitals and digits in each text box (cap height ÷ 0.7 for SF); weight from stroke width (distance transform) over size, in 4 bands (regular, medium, semibold, bold) | size within 1 pt for 90 %, weight band right for 80 % |
| alignment | left edges clustered within 1 pt; share of boxes on the main edge | exact on the set |
| radii | per surface, the inset of the edge on the first rows of each corner, fitted to a circle; "capsule" when radius ≥ half the height − 1 | within 2 pt |
| colour_roles | median colour inside each surface; text colour = the colour inside the text box that contrasts most with the box's surface; accent = most saturated colour with a small area | used only for the next row |
| contrast | WCAG ratio per text, dot and icon against the surface behind it | within 0.1 of the frame's own value |
| words | the text Vision reads, kept for the 3-word copy check | free from the text pass |
| motion | not from a still: always "not measured" | |

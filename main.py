"""news-image-20261121 v4 — "THE FRONT PAGE".

Sums up Saturday 21 November 2026's world news in one 1024x1024 image.
Pure Python standard library only: hand-written PNG encoder (zlib),
5x7 bitmap font, and a small shape rasterizer. Deterministic:
identical bytes on every run. No network, no third-party packages.

Layout (classic broadsheet front page, pyramid hierarchy):
  nameplate + date -> ONE dominant lead (FBI database hacked)
  -> 2 half-width stories (ICJ genocide verdict, markets meltdown)
  -> 3 third-width stories (Kyiv, cancer breakthrough, Chapo Isidro)
  -> 1 full-width strip (128 nations agree killer-robot rules)
  -> ALSO TODAY ticker -> sources footer.
Seven main stories across seven fields.
"""
import os
import struct
import sys
import zlib

WIDTH = 1024
HEIGHT = 1024

# Palette: cool "night edition" broadsheet paper (NOT v3's warm cream).
BG = (237, 240, 242)      # cool grey-blue paper
PAPER = (255, 255, 255)    # panel white
INK = (16, 24, 32)         # near-black ink
RED = (185, 28, 28)        # alert red
BLUE = (30, 58, 95)        # deep ink blue
GOLD = (138, 109, 0)       # verdict gold
TEAL = (15, 118, 110)      # health teal
AMBER = (180, 83, 9)       # crime amber
GREY = (91, 103, 112)      # muted grey
RULE = (200, 207, 212)     # light rule

MASTHEAD_TITLE = "THE WORLD IN ONE IMAGE"
MASTHEAD_DATE = "SATURDAY 21 NOVEMBER 2026"

STORIES = [
    {"kicker": "CYBERATTACK - LEAD STORY", "color": RED,
     "headline": "FBI DATABASE HACKED",
     "fact": "THE BUREAU INVESTIGATES A BREACH OF ITS NATIONWIDE CRIME "
             "DATABASE.",
     "stat": "2ND BREACH IN MONTHS - USDA ALSO HIT"},
    {"kicker": "JUSTICE - THE HAGUE", "color": GOLD,
     "headline": "MYANMAR GUILTY OF GENOCIDE",
     "fact": "FIRST TIME ANY INTERNATIONAL COURT HAS FOUND A STATE "
             "GUILTY OF GENOCIDE.",
     "stat": None},
    {"kicker": "MARKETS - WALL STREET", "color": RED,
     "headline": "MARKETS IN MELTDOWN",
     "fact": "S&P -3.7% - DOW -950 - NVIDIA -14%",
     "stat": "-5.28%"},
    {"kicker": "WAR - UKRAINE", "color": RED,
     "headline": "KYIV UNDER FIRE",
     "fact": "400+ DRONES, 110 MISSILES OVERNIGHT; STRIKES REACH POLAND.",
     "stat": None},
    {"kicker": "HEALTH - BARCELONA", "color": TEAL,
     "headline": "CANCER BREAKTHROUGH",
     "fact": "TUMOURS STOPPED GROWING IN 90.2%.",
     "stat": "1 IN 12"},
    {"kicker": "CRIME - MEXICO", "color": AMBER,
     "headline": "CHAPO ISIDRO CAUGHT",
     "fact": "FBI TOP 10 FUGITIVE SEIZED IN SINALOA.",
     "stat": "$5M REWARD"},
    {"kicker": "ARMS CONTROL - GENEVA", "color": BLUE,
     "headline": "128 NATIONS AGREE TO DRAFT KILLER-ROBOT RULES",
     "fact": "GENEVA, 04:45 - TWO-YEAR PATH TO RULES. NO BINDING TREATY YET.",
     "stat": None},
]

TICKER = ("ALSO TODAY: SHENZHEN PEACE DEAL - COP31 DEADLOCK - "
          "BAYER $7.25BN DEAL - HOUTHI MISSILES AT RIYADH - "
          "GEN Z PROTESTS IN 25 COUNTRIES - PERU 6.9 QUAKE")
FOOTER = "SOURCES: REUTERS - AP - CNN - BBC - UN NEWS - ICJ - AFP"

# ---------------------------------------------------------------- font
# 5x7 bitmap glyphs, one string per row, "#" = on. Written from scratch.
_GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "\u00b7": ("00000", "00000", "01100", "01100", "00000", "00000", "00000"),
}
_ALIASES = {"\u2014": "-", "\u2013": "-", "\u2212": "-", "\u2019": "'",
            "\u201c": '"', "\u201d": '"'}


def _glyph(ch):
    ch = _ALIASES.get(ch, ch)
    return _GLYPHS.get(ch.upper(), _GLYPHS["?"])


def text_width(text, scale):
    """Pixel width of text at the given scale (6 units per char)."""
    return len(text) * 6 * scale


def wrap_text(text, scale, max_width):
    """Greedy word wrap; every returned line fits max_width."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if text_width(trial, scale) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- image
class Image:
    def __init__(self, width, height, bg):
        self.width = width
        self.height = height
        self.pixels = bytearray(bg) * (width * height)

    def set(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.pixels[i:i + 3] = bytes(color)

    def fill_rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.width, x + w), min(self.height, y + h)
        for yy in range(y0, y1):
            base = (yy * self.width + x0) * 3
            self.pixels[base:base + (x1 - x0) * 3] = bytes(color) * (x1 - x0)

    def rect(self, x, y, w, h, color, t=1):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def hline(self, x, y, w, color, t=1):
        self.fill_rect(x, y, w, t, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.fill_rect(x0 - t // 2, y0 - t // 2, t, t, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color, filled=True):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) ** 2) ** 0.5)
            if filled:
                self.fill_rect(cx - dx, yy, 2 * dx + 1, 1, color)
            else:
                self.set(cx - dx, yy, color)
                self.set(cx + dx, yy, color)

    def triangle(self, pts, color):
        """Filled triangle, scanline fill."""
        (x0, y0), (x1, y1), (x2, y2) = sorted(pts, key=lambda p: p[1])
        if y2 == y0:
            return
        def interp(xa, ya, xb, yb, y):
            return xa if yb == ya else xa + (xb - xa) * (y - ya) / (yb - ya)
        for y in range(y0, y2 + 1):
            if y < y1:
                xa = interp(x0, y0, x1, y1, y)
                xb = interp(x0, y0, x2, y2, y)
            else:
                xa = interp(x1, y1, x2, y2, y)
                xb = interp(x0, y0, x2, y2, y)
            self.fill_rect(int(min(xa, xb)), y, int(abs(xb - xa)) + 1, 1, color)

    def draw_text(self, x, y, text, scale, color, bold=False, align="left"):
        if align == "center":
            x -= text_width(text, scale) // 2
        elif align == "right":
            x -= text_width(text, scale)
        cx = x
        for ch in text:
            g = _glyph(ch)
            for r, row in enumerate(g):
                for c, bit in enumerate(row):
                    if bit == "1":
                        self.fill_rect(cx + c * scale, y + r * scale,
                                       scale, scale, color)
                        if bold:
                            self.fill_rect(cx + c * scale + max(1, scale // 3),
                                           y + r * scale, scale, scale, color)
            cx += 6 * scale
        return cx

    def draw_text_block(self, x, y, lines, scale, color, leading=None,
                        bold=False):
        leading = leading if leading is not None else int(7 * scale * 1.5)
        for line in lines:
            self.draw_text(x, y, line, scale, color, bold=bold)
            y += leading
        return y


def _chunk(ctype, payload):
    return (struct.pack(">I", len(payload)) + ctype + payload +
            struct.pack(">I", zlib.crc32(ctype + payload) & 0xFFFFFFFF))


def encode_png(img):
    raw = bytearray()
    stride = img.width * 3
    for y in range(img.height):
        raw.append(0)  # filter: none
        raw += img.pixels[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", img.width, img.height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) +
            _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b""))

# ---------------------------------------------------------------- pictograms
def pict_padlock(img, cx, cy, s, color):
    """Padlock: shackle arc + body + keyhole."""
    w, h = int(s * 0.62), int(s * 0.5)
    top = cy - h // 2
    # shackle: two posts + top bar
    t = max(2, s // 14)
    img.fill_rect(cx - w // 2, top - int(s * 0.28), t, int(s * 0.28) + t, color)
    img.fill_rect(cx + w // 2 - t, top - int(s * 0.28), t, int(s * 0.28) + t, color)
    img.fill_rect(cx - w // 2, top - int(s * 0.28), w, t, color)
    # body
    img.fill_rect(cx - w // 2, top, w, h, color)
    # keyhole: paper-coloured dot + slot
    img.circle(cx, top + h // 3, max(2, s // 16), PAPER)
    img.fill_rect(cx - max(1, s // 32), top + h // 3, max(2, s // 16),
                  h // 3, PAPER)


def pict_scales(img, cx, cy, s, color):
    """Scales of justice: post, crossbar, two pans, base."""
    t = max(2, s // 16)
    img.fill_rect(cx - t // 2, cy - s // 2, t, s, color)              # post
    img.fill_rect(cx - s // 2, cy - s // 2, s, t, color)              # crossbar
    img.fill_rect(cx - s // 2, cy + s // 2 - t, s, t, color)          # base
    for px in (cx - s // 2, cx + s // 2):
        img.line(px, cy - s // 2 + t, px - s // 6, cy + s // 6, color, t)
        img.line(px, cy - s // 2 + t, px + s // 6, cy + s // 6, color, t)
        img.triangle([(px - s // 6, cy + s // 6), (px + s // 6, cy + s // 6),
                      (px, cy + s // 6 + s // 8)], color)


def pict_chart(img, cx, cy, s, color):
    """Plunging market chart: axes + descending zigzag + arrow."""
    t = max(2, s // 16)
    x0, y0 = cx - s // 2, cy + s // 2
    img.fill_rect(x0, y0 - t, s, t, color)                            # x axis
    img.fill_rect(x0, cy - s // 2, t, s, color)                       # y axis
    pts = [(x0 + s * 0.08, cy - s * 0.38), (x0 + s * 0.30, cy - s * 0.18),
           (x0 + s * 0.46, cy - s * 0.30), (x0 + s * 0.66, cy + s * 0.05),
           (x0 + s * 0.86, cy + s * 0.34)]
    for a, b in zip(pts, pts[1:]):
        img.line(int(a[0]), int(a[1]), int(b[0]), int(b[1]), color, t + 1)
    ex, ey = int(pts[-1][0]), int(pts[-1][1])
    img.line(ex, ey, ex - s // 8, ey - s // 16, color, t + 1)
    img.line(ex, ey, ex - s // 16, ey + s // 8, color, t + 1)


def pict_burst(img, cx, cy, s, color):
    """Explosion burst: rays from a centre dot."""
    import math
    for k in range(12):
        a = k * math.pi / 6
        r1, r2 = s // 6, s // 2
        img.line(int(cx + r1 * math.cos(a)), int(cy + r1 * math.sin(a)),
                 int(cx + r2 * math.cos(a)), int(cy + r2 * math.sin(a)),
                 color, max(2, s // 18))
    img.circle(cx, cy, max(2, s // 10), color)


def pict_capsule(img, cx, cy, s, color):
    """Medicine capsule: two halves, split down the middle."""
    w, h = int(s * 0.85), int(s * 0.34)
    x0, y0 = cx - w // 2, cy - h // 2
    img.fill_rect(x0 + h // 2, y0, w - h, h, color)
    img.circle(x0 + h // 2, cy, h // 2, color)
    img.circle(x0 + w - h // 2, cy, h // 2, color)
    img.fill_rect(cx - max(1, s // 40), y0, max(2, s // 20), h, PAPER)
    # highlight half in paper outline
    img.rect(x0, y0, w, h, PAPER, max(1, s // 40))


def pict_badge(img, cx, cy, s, color):
    """Sheriff badge: shield outline + star."""
    w, h = s // 2, int(s * 0.62)
    x0, y0 = cx - w // 2, cy - h // 2
    img.line(x0, y0, x0 + w, y0, color, 3)
    img.line(x0, y0, x0, y0 + h // 2, color, 3)
    img.line(x0 + w, y0, x0 + w, y0 + h // 2, color, 3)
    img.line(x0, y0 + h // 2, cx, y0 + h, color, 3)
    img.line(x0 + w, y0 + h // 2, cx, y0 + h, color, 3)
    img.circle(cx, cy - h // 10, max(2, s // 12), color)


def pict_robot(img, cx, cy, s, color):
    """Robot head: antenna, head, two eyes, jaw."""
    t = max(2, s // 18)
    img.fill_rect(cx - t // 2, cy - s // 2 - s // 6, t, s // 6, color)
    img.circle(cx, cy - s // 2 - s // 6, max(2, s // 14), color)
    hw, hh = s // 2, int(s * 0.34)
    img.rect(cx - hw // 2, cy - hh // 2, hw, hh, color, t)
    img.circle(cx - hw // 5, cy - hh // 6, max(2, s // 16), color)
    img.circle(cx + hw // 5, cy - hh // 6, max(2, s // 16), color)
    img.fill_rect(cx - hw // 4, cy + hh // 4, hw // 2, t, color)


PICTOGRAMS = {"padlock": pict_padlock, "scales": pict_scales,
              "chart": pict_chart, "burst": pict_burst,
              "capsule": pict_capsule, "badge": pict_badge,
              "robot": pict_robot}


# ---------------------------------------------------------------- layout
def panel(img, x, y, w, h):
    img.fill_rect(x, y, w, h, PAPER)
    img.rect(x, y, w, h, INK, 2)


def kicker_line(img, x, y, text, color):
    img.draw_text(x, y, text, 2, color, bold=True)
    return y + 22


def render():
    img = Image(WIDTH, HEIGHT, BG)
    M = 30                      # outer margin
    W = WIDTH - 2 * M           # 964 usable

    # ---- nameplate: big title, red date, red double rule (no black band)
    img.draw_text(WIDTH // 2, 30, MASTHEAD_TITLE, 7, INK, bold=True,
                  align="center")
    img.draw_text(WIDTH // 2, 92, MASTHEAD_DATE, 3, RED, bold=True,
                  align="center")
    img.hline(M, 122, W, RED, 4)
    img.hline(M, 130, W, RED, 2)

    lead, second1, second2 = STORIES[0], STORIES[1], STORIES[2]
    row3 = STORIES[3:6]
    strip = STORIES[6]

    # ---- LEAD: FBI DATABASE HACKED (y 146..470)
    panel(img, M, 146, W, 324)
    kicker_line(img, M + 24, 164, lead["kicker"], RED)
    img.draw_text(M + 24, 196, "FBI DATABASE", 8, INK, bold=True)
    img.draw_text(M + 24, 264, "HACKED", 8, INK, bold=True)
    fact_lines = wrap_text(lead["fact"], 3, 620)
    img.draw_text_block(M + 24, 344, fact_lines, 3, INK, leading=30)
    # stat chip, bottom-left
    chip = lead["stat"]
    cw = text_width(chip, 2) + 28
    img.fill_rect(M + 24, 424, cw, 30, RED)
    img.draw_text(M + 38, 431, chip, 2, PAPER, bold=True)
    # padlock pictogram, right side
    pict_padlock(img, M + W - 130, 300, 190, RED)

    # ---- ROW 2: two half-width panels (y 486..696)
    y2, h2 = 486, 210
    w2 = (W - 24) // 2          # 470 each
    for i, st, pict in ((0, second1, "scales"), (1, second2, "chart")):
        x = M + i * (w2 + 24)
        panel(img, x, y2, w2, h2)
        kicker_line(img, x + 20, y2 + 16, st["kicker"], st["color"])
        hl = wrap_text(st["headline"], 4, w2 - 40)
        hy = img.draw_text_block(x + 20, y2 + 44, hl, 4, INK, leading=40,
                                 bold=True)
        if st["stat"]:
            img.draw_text(x + 20, hy + 6, st["stat"], 5, st["color"],
                          bold=True)
            fy = hy + 6 + 7 * 5 + 6
        else:
            fy = hy + 6
        fl = wrap_text(st["fact"], 2, w2 - 130)
        img.draw_text_block(x + 20, fy, fl, 2, GREY, leading=20)
        PICTOGRAMS[pict](img, x + w2 - 52, y2 + h2 - 52, 84, st["color"])

    # ---- ROW 3: three third-width panels (y 710..874)
    y3, h3 = 710, 164
    w3 = (W - 48) // 3          # 305 each
    for i, (st, pict) in enumerate(zip(row3, ("burst", "capsule", "badge"))):
        x = M + i * (w3 + 24)
        panel(img, x, y3, w3, h3)
        kicker_line(img, x + 16, y3 + 12, st["kicker"], st["color"])
        hl = wrap_text(st["headline"], 3, w3 - 88)
        hy = img.draw_text_block(x + 16, y3 + 38, hl, 3, INK, leading=28,
                                 bold=True)
        if st["stat"]:
            img.draw_text(x + 16, hy + 2, st["stat"], 4, st["color"],
                          bold=True)
            fy = hy + 2 + 32
        else:
            fy = hy + 2
        fl = wrap_text(st["fact"], 2, w3 - 32)
        img.draw_text_block(x + 16, fy, fl, 2, GREY, leading=18)
        PICTOGRAMS[pict](img, x + w3 - 34, y3 + 34, 52, st["color"])

    # ---- STRIP: killer-robot rules, full width (y 890..960)
    panel(img, M, 890, W, 70)
    pict_robot(img, M + 44, 890 + 40, 48, BLUE)
    img.draw_text(M + 92, 902, strip["headline"], 3, INK, bold=True)
    img.draw_text(M + 92, 930, strip["fact"], 2, GREY)

    # ---- TICKER + FOOTER
    tl = wrap_text(TICKER, 2, W)
    img.draw_text_block(M, 972, tl, 2, INK, leading=18)
    img.draw_text(WIDTH // 2, 1008, FOOTER, 2, GREY, align="center")
    return img


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "entry.png")
    data = encode_png(render())
    with open(out, "wb") as f:
        f.write(data)
    os.chmod(out, 0o644)
    print("wrote %s (%d bytes, sha256 %s)" %
          (out, len(data), __import__("hashlib").sha256(data).hexdigest()))
    return out


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

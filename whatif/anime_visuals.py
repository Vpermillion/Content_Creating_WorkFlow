"""Original vector storyboards for the Ifverse anime review pilot."""
import html
import math
import textwrap

KINDS = {"anime-intro", "anime-target", "anime-deal", "anime-mission", "anime-demand", "anime-refuse", "anime-choice", "anime-ending"}


def storyboard(scene, index, count, title):
    kind = scene["visual"]
    if kind not in KINDS:
        raise ValueError("Unsupported original anime storyboard kind")
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="720" height="1280" viewBox="0 0 720 1280">',
           '<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#11131c"/><stop offset="1" stop-color="#25121d"/></linearGradient></defs>',
           '<rect width="720" height="1280" fill="url(#bg)"/>',
           '<path d="M0 420L720 150V700L0 1020Z" fill="#542135" opacity=".22"/>']

    def text(x, y, value, size=25, color="#f6f1e8", anchor="start"):
        out.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans" font-weight="bold" font-size="{size}" text-anchor="{anchor}" fill="{color}">{html.escape(value)}</text>')

    def line(x1, y1, x2, y2, color="#ed5c65", width=4):
        out.append(f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{color}" stroke-width="{width}" fill="none"/>')

    def person(x, y, scale=1, color="#ffb35b"):
        out.append(f'<g transform="translate({x},{y}) scale({scale})"><circle cy="-60" r="32" fill="{color}"/><path d="M-44 -15Q0 -40 44 -15L65 110H-65Z" fill="{color}"/><rect x="-34" y="-74" width="68" height="15" rx="4" fill="#171925"/><path d="M34 -68L80 -48 50 -40" fill="{color}"/></g>')

    def faction(x, y, radius=90):
        out.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="#3c1b2b" stroke="#ed5c65" stroke-width="3"/>')
        for i in range(8):
            a = i * math.pi / 4
            cx, cy = x + math.cos(a) * radius * .65, y + math.sin(a) * radius * .65
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="8" fill="#ed5c65"/>')
        text(x, y + 12, "A", 54, "#ed5c65", "middle")

    def village(x, y):
        out.append(f'<g transform="translate({x},{y})"><path d="M-75 45V-25L-35 -65 5 -25V45M5 45V-5L40 -40 75 -5V45" fill="#182c2d" stroke="#7bc6b0" stroke-width="4"/><path d="M-80 45H80" stroke="#7bc6b0" stroke-width="5"/></g>')

    for i in range(16):
        x, y = (i * 157 + 40) % 700, (i * 83 + 380) % 520 + 340
        line(x, y, x + 48, y - 16, "#6a3342", 1)
    text(58, 83, "IFVERSE / ANIME", 22, "#ffb35b")
    text(660, 83, f"{index + 1:02}/{count:02}", 18, "#a69aa5", "end")
    for j, row in enumerate(textwrap.wrap(title.upper(), width=24)):
        text(58, 180 + j * 51, row, 36)
    text(58, 350, scene["label"], 24, "#ffb35b")
    out.append('<rect x="58" y="380" width="604" height="455" rx="22" fill="#11121b" stroke="#49303f" stroke-width="2"/>')
    if kind in {"anime-intro", "anime-refuse"}:
        person(235, 625, .8)
        faction(520, 610)
        line(315, 610, 415, 610)
        text(360, 588, "?" if kind == "anime-intro" else "NO", 34, "#f6f1e8", "middle")
        text(235, 780, "NARUTO", 20, "#ffb35b", "middle")
        text(520, 780, "AKATSUKI", 20, "#ed5c65", "middle")
    elif kind == "anime-target":
        for i in range(9):
            a = (i / 8) * math.pi + math.pi
            x, y = 360 + math.cos(a) * 205, 620 + math.sin(a) * 155
            out.append(f'<path d="M360 650Q{x:.0f} 690 {x:.0f} {y:.0f}" stroke="#a65338" stroke-width="16" fill="none" stroke-linecap="round"/>')
        person(360, 625, .8)
        out.append('<circle cx="360" cy="600" r="150" fill="none" stroke="#ed5c65" stroke-width="3" stroke-dasharray="12 12"/>')
        text(360, 785, "RECRUIT + TARGET", 24, "#ed5c65", "middle")
    elif kind == "anime-deal":
        for x, label, color in [(210, "HIS HELP", "#ffb35b"), (510, "FRIENDS SAFE", "#7bc6b0")]:
            out.append(f'<rect x="{x-112}" y="510" width="224" height="155" rx="14" fill="#1b1e29" stroke="{color}" stroke-width="3"/>')
            text(x, 598, label, 22, color, "middle")
        line(330, 580, 390, 580, "#ed5c65")
        text(360, 750, "A DEAL WITH CONDITIONS", 23, "#a69aa5", "middle")
    elif kind == "anime-mission":
        line(150, 585, 570, 585, "#61515f", 6)
        for i, label in enumerate(["TRUST", "MISSIONS", "PRESSURE"]):
            x = 150 + i * 210
            out.append(f'<circle cx="{x}" cy="585" r="27" fill="{["#ffb35b", "#c87b69", "#ed5c65"][i]}"/>')
            text(x, 690, label, 19, "#f6f1e8", "middle")
        text(360, 770, "EVERY FAVOR HAS A PRICE", 23, "#a69aa5", "middle")
    elif kind in {"anime-demand", "anime-choice"}:
        person(360, 490, .45)
        line(350, 560, 220, 660, "#7bc6b0")
        line(370, 560, 510, 660)
        village(205, 695)
        faction(520, 695, 62)
        text(205, 790, "HIDDEN LEAF", 19, "#7bc6b0", "middle")
        text(520, 790, "AKATSUKI", 19, "#ed5c65", "middle")
    else:
        out.append('<circle cx="360" cy="600" r="150" fill="#251b29" stroke="#ed5c65" stroke-width="3"/>')
        text(360, 665, "?", 185, "#ffb35b", "middle")
        text(360, 790, "WHO CHANGES WHOM?", 25, "#f6f1e8", "middle")
    text(58, 895, "ALTERNATE TIMELINE / FAN SCENARIO", 18, "#a69aa5")
    text(58, 1150, "STORYBOARD DRAFT / SYNTHETIC NARRATION", 16, "#a69aa5")
    out.append(f'<rect x="58" y="1190" width="{604*(index+1)/count}" height="5" fill="#ed5c65"/>')
    out.append('</svg>')
    return "\n".join(out)

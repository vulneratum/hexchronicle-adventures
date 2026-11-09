#!/usr/bin/env python3
"""Build KR1 The Fortress of Kingsreach: Markdown sources -> HTML -> PDF (TSR-style layout)."""
import re, glob, os, subprocess, sys, pathlib
import markdown

ROOT = pathlib.Path(__file__).parent
FONTS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "fonts"
OUT = ROOT / "out"; OUT.mkdir(exist_ok=True)

STAT_KEYS = ("Armor Class|Hit Dice|Move|Attacks|Damage|No. Appearing|Save As|Morale|Treasure Type|Alignment")

def prep(text):
    lines = text.split("\n")
    out = []
    for i, ln in enumerate(lines):
        s = ln.rstrip()
        # consecutive italic stat lines -> hard line breaks, styled as stat paragraphs
        if re.match(r"^\*[^*].*\*$", s) and "(" in s:
            s = s + "  "
        if re.match(rf"^({STAT_KEYS}):", s):
            k, v = s.split(":", 1)
            s = f"<b>{k}:</b>{v}  "
        out.append(s)
    return "\n".join(out)

body = ""
for f in sorted(glob.glob(str(ROOT / "src/*.md"))):
    md = markdown.Markdown(extensions=["tables", "md_in_html", "attr_list", "sane_lists"])
    body += f'<section class="src">' + md.convert(prep(open(f).read())) + "</section>\n"

# Wide tables (6+ columns) span both columns
def widen(m):
    t=m.group(0)
    return t.replace("<table>",'<table class="wide">',1) if t.count("<th")>=6 else t
body = re.sub(r"<table>.*?</thead>", widen, body, flags=re.S)
# Mark keyed-area paragraphs (e.g. "<p><strong>A1. TIDAL ENTRANCE.</strong>") for keep-with-next styling
body = re.sub(r"<p><strong>((?:[A-JW]?\d{1,2})\. )", r'<p class="key"><strong>\1', body)
# Stat-line paragraphs
body = re.sub(r"<p><em>([^<]*\((?:AC|Armor)[^<]*)</em>", r'<p class="stat"><em>\1</em>', body)
body = re.sub(r'<p><strong>([^<.]{3,40})</strong></p>', r'<h3 class="mon">\1</h3>', body)
# Monster blocks: wrap "<p><b>Armor Class" paragraph
body = body.replace("<p><b>Armor Class", '<p class="monblock"><b>Armor Class')
# h1 at the start of each major part starts a new page (except the first)
body = body.replace("<h1>", '<h1 class="part">')

fontcss = ""
for fam, slug, weights in [("Fraunces", "fraunces", [(400, "normal"), (700, "normal"), (900, "normal"), (400, "italic")]),
                           ("Libre Baskerville", "libre-baskerville", [(400, "normal"), (700, "normal"), (400, "italic")])]:
    for w, st in weights:
        p = (FONTS / f"{slug}-latin-{w}-{st}.ttf").resolve()
        fontcss += f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:{st};src:url('{p.as_uri()}') format('truetype');}}\n"

css = open(ROOT / "style.css").read()
cover = open(ROOT / "cover.html").read()

html = f"""<!doctype html><html><head><meta charset="utf-8"><title>KR1 The Fortress of Kingsreach</title>
<style>{fontcss}{css}</style></head><body>
{cover}
<main>{body}</main>
</body></html>"""

# Move back cover out of the two-column flow
m = re.search(r'<div class="backcover">.*?</div>', html, re.S)
if m:
    bc = m.group(0); html = html.replace(bc, "")
    html = html.replace("</body>", f'<div class="backpage">{bc}</div></body>')

(OUT / "kingsreach.html").write_text(html)
print("html ok", len(html))

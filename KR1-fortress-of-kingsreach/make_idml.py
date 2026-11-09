#!/usr/bin/env python3
"""Convert the built KR1 HTML into an IDML package (InDesign Markup Language) for DesignCraft / InDesign."""
import re, sys, zipfile, pathlib, math
from xml.sax.saxutils import escape as xesc
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "out/kingsreach.html"
OUT = ROOT / "out/KR1-Fortress-of-Kingsreach.idml"
INTERIOR_PAGES = 34

DOM = "15.0"
NS = 'xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging"'
HDR = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'

# Page geometry (points). Letter, single pages, page occupies x 0..612, y -396..396 in spread space.
PW, PH = 612.0, 792.0
ML, MR, MT, MB = 43.2, 43.2, 50.4, 46.8
GUT = 20.0
COLW = (PW - ML - MR - GUT) / 2          # 252.8
FULLW = PW - ML - MR                      # 525.6
Y0 = -PH / 2

def esc(s):
    return xesc(s, {'"': "&quot;"})

def attr_escape(s):
    return esc(s)

# ------------------------------------------------------------------ styles
SEA, SHADE, MAPBLUE, MAPLINE, BOXFILL = "Color/Sea", "Color/Shade", "Color/MapBlue", "Color/MapLine", "Color/Paper"

def pstyle(name, font, fstyle, size, leading, extra="", props=""):
    return (f'<ParagraphStyle Self="ParagraphStyle/{name}" Name="{name}" FontStyle="{fstyle}" PointSize="{size}" {extra}>'
            f'<Properties><BasedOn type="object">ParagraphStyle/$ID/[No paragraph style]</BasedOn>'
            f'<AppliedFont type="string">{font}</AppliedFont><Leading type="unit">{leading}</Leading>{props}</Properties></ParagraphStyle>')

BASK, FRAUN = "Libre Baskerville", "Fraunces"
J = 'Justification="LeftJustified" Hyphenation="true"'
L = 'Justification="LeftAlign" Hyphenation="false"'
C = 'Justification="CenterAlign" Hyphenation="false"'
SPAN = 'SpanColumnType="SpanColumns"'
def border(color="Color/Black", w=1, off=5):
    return (f'ParagraphBorderOn="true" ParagraphBorderColor="{color}" ParagraphBorderTopLineWeight="{w}" ParagraphBorderBottomLineWeight="{w}" '
            f'ParagraphBorderLeftLineWeight="{w}" ParagraphBorderRightLineWeight="{w}" ParagraphBorderTopOffset="{off}" ParagraphBorderBottomOffset="{off}" '
            f'ParagraphBorderLeftOffset="{off}" ParagraphBorderRightOffset="{off}" ParagraphBorderDisplayIfSplits="true" MergeConsecutiveParagraphBorders="true"')
def shade(color, tint=100, off=5):
    return (f'ParagraphShadingOn="true" ParagraphShadingColor="{color}" ParagraphShadingTint="{tint}" ParagraphShadingTopOffset="{off}" '
            f'ParagraphShadingBottomOffset="{off}" ParagraphShadingLeftOffset="{off}" ParagraphShadingRightOffset="{off}"')

PARA_STYLES = [
    pstyle("Body", BASK, "Regular", 8.6, 12.2, f'{J} SpaceAfter="4.7"'),
    pstyle("Key", BASK, "Regular", 8.6, 12.2, f'{J} SpaceBefore="6.5" SpaceAfter="4.7"'),
    pstyle("Stat", BASK, "Italic", 8, 10.8, f'{L} LeftIndent="7" FirstLineIndent="-7" SpaceAfter="3.6"'),
    pstyle("MonsterStats", BASK, "Regular", 8.2, 11.9, f'{L} LeftIndent="6" SpaceAfter="6" KeepAllLinesTogether="true" {shade(SHADE, 100, 4)}'),
    pstyle("ListItem", BASK, "Regular", 8.6, 12.2, f'{J} LeftIndent="11" FirstLineIndent="-11" SpaceAfter="2.6"'),
    pstyle("Boxed Text", BASK, "Regular", 8.5, 12, f'{L} LeftIndent="6" RightIndent="6" SpaceBefore="9" SpaceAfter="11" KeepAllLinesTogether="true" {border("Color/Black", 1.2, 5)}'),
    pstyle("Illustration Placeholder", BASK, "Italic", 7.9, 11, f'{L} LeftIndent="6" RightIndent="6" SpaceBefore="9" SpaceAfter="12" KeepAllLinesTogether="true" FillColor="Color/Ink2" {shade(SHADE, 60, 5)} {border("Color/Ink2", 0.75, 5)}'),
    pstyle("Map Placeholder", BASK, "Regular", 8.1, 11.4, f'{L} {SPAN} LeftIndent="6" RightIndent="6" SpaceBefore="12" SpaceAfter="16" FillColor="Color/MapInk" {shade(MAPBLUE, 100, 6)} {border(MAPLINE, 2, 6)}'),
    pstyle("Heading 1", FRAUN, "Black", 22, 24, f'{C} {SPAN} FillColor="{SEA}" SpaceBefore="14" SpaceAfter="10" KeepWithNext="2" '
           f'RuleAbove="true" RuleAboveLineWeight="3" RuleAboveType="StrokeStyle/$ID/ThickThin" RuleAboveOffset="22" RuleAboveColor="Color/Black" RuleAboveWidth="ColumnWidth" '
           f'RuleBelow="true" RuleBelowLineWeight="3" RuleBelowType="StrokeStyle/$ID/ThinThick" RuleBelowOffset="6" RuleBelowColor="Color/Black" RuleBelowWidth="ColumnWidth"'),
    pstyle("Heading 2", FRAUN, "Black", 12.5, 14, f'{L} Capitalization="AllCaps" SpaceBefore="10" SpaceAfter="5" KeepWithNext="2" '
           f'RuleBelow="true" RuleBelowLineWeight="1.2" RuleBelowOffset="3" RuleBelowColor="Color/Black" RuleBelowWidth="ColumnWidth"'),
    pstyle("Heading 3", FRAUN, "Bold Italic" if False else "Italic", 10.5, 12.5, f'{L} FillColor="{SEA}" SpaceBefore="8" SpaceAfter="3" KeepWithNext="2"'),
    pstyle("Monster Name", FRAUN, "Black", 11, 13, f'{L} SpaceBefore="10" SpaceAfter="4" KeepWithNext="2" '
           f'RuleBelow="true" RuleBelowLineWeight="0.8" RuleBelowOffset="3" RuleBelowColor="Color/Black" RuleBelowWidth="ColumnWidth"'),
    pstyle("Title Code", FRAUN, "Bold", 9, 12, f'{C} {SPAN} Capitalization="AllCaps" Tracking="200" FillColor="{SEA}" SpaceBefore="4"'),
    pstyle("Title", FRAUN, "Black", 30, 32, f'{C} {SPAN} SpaceBefore="4" SpaceAfter="2"'),
    pstyle("Title Byline", BASK, "Italic", 8.6, 12, f'{C} {SPAN} SpaceAfter="6"'),
    pstyle("Title Levels", FRAUN, "Black", 10, 13, f'{C} {SPAN} Tracking="120" SpaceBefore="4" SpaceAfter="10" '
           f'RuleAbove="true" RuleAboveLineWeight="1" RuleAboveOffset="12" RuleAboveColor="Color/Black" RuleAboveWidth="ColumnWidth" '
           f'RuleBelow="true" RuleBelowLineWeight="1" RuleBelowOffset="4" RuleBelowColor="Color/Black" RuleBelowWidth="ColumnWidth"'),
    pstyle("Title Body", BASK, "Regular", 9, 12.8, f'{C} {SPAN} LeftIndent="30" RightIndent="30" SpaceAfter="5"'),
    pstyle("Title Note", BASK, "Italic", 7.5, 10, f'{C} {SPAN} FillColor="Color/Ink2" SpaceAfter="14"'),
    pstyle("Table Anchor", BASK, "Regular", 4, 4, f'{L} SpaceBefore="3" SpaceAfter="8"'),
    pstyle("Table Anchor Wide", BASK, "Regular", 4, 4, f'{L} {SPAN} SpaceBefore="3" SpaceAfter="8"'),
    pstyle("Table Head", FRAUN, "Bold", 7.7, 10, f'{L} FillColor="Color/Paper"'),
    pstyle("Table Body", BASK, "Regular", 7.7, 10, f'{L}'),
    pstyle("Table Head Compact", FRAUN, "Bold", 6.4, 8.2, f'{L} FillColor="Color/Paper"'),
    pstyle("Table Body Compact", BASK, "Regular", 6.4, 8.2, f'{L}'),
    pstyle("Header", FRAUN, "Italic", 8, 10, f'Justification="RightAlign" FillColor="Color/Ink2"'),
    pstyle("Header Code", FRAUN, "Black", 8, 10, f'{L} FillColor="{SEA}"'),
    pstyle("Folio", FRAUN, "Bold", 9, 11, f'{C}'),
    pstyle("Cover Small", FRAUN, "Bold", 9, 12, f'{L} Capitalization="AllCaps" Tracking="250" FillColor="Color/CoverPale"'),
    pstyle("Cover Title", FRAUN, "Black", 40, 40, f'{L} FillColor="Color/Paper"'),
    pstyle("Cover Code Label", FRAUN, "Bold", 7.5, 9, f'{C} Capitalization="AllCaps" FillColor="{SEA}"'),
    pstyle("Cover Code", FRAUN, "Black", 34, 34, f'{C} FillColor="{SEA}"'),
    pstyle("Cover Art Label", FRAUN, "Black", 11, 14, f'{C} Tracking="120" FillColor="Color/Gold" SpaceAfter="10"'),
    pstyle("Cover Art Text", BASK, "Italic", 10.5, 16, f'{L} FillColor="Color/CoverPale" SpaceAfter="9"'),
    pstyle("Cover Levels", FRAUN, "Black", 13, 16, f'{C} Capitalization="AllCaps" Tracking="180" FillColor="Color/Paper"'),
    pstyle("Cover Blurb", BASK, "Italic", 9.5, 13, f'{C} FillColor="Color/CoverPale" SpaceBefore="4" SpaceAfter="4"'),
    pstyle("Back Title", FRAUN, "Black", 28, 30, f'{L} FillColor="Color/Paper" SpaceAfter="14"'),
    pstyle("Back Body", BASK, "Regular", 11, 17.5, f'{L} FillColor="Color/CoverPale" SpaceAfter="10"'),
    pstyle("Back Tag", FRAUN, "Black", 16, 20, f'{L} Capitalization="AllCaps" Tracking="80" FillColor="Color/Gold" SpaceBefore="6"'),
]

CHAR_STYLES = {
    "B": '<CharacterStyle Self="CharacterStyle/Bold" Name="Bold" FontStyle="Bold"/>',
    "I": '<CharacterStyle Self="CharacterStyle/Italic" Name="Italic" FontStyle="Italic"/>',
    "BI": '<CharacterStyle Self="CharacterStyle/Bold Italic" Name="Bold Italic" FontStyle="Bold"/>',
    "K": ('<CharacterStyle Self="CharacterStyle/Key Heading" Name="Key Heading" FontStyle="Black" PointSize="9.3">'
          f'<Properties><AppliedFont type="string">{FRAUN}</AppliedFont></Properties></CharacterStyle>'),
}
CS = {None: "CharacterStyle/$ID/[No character style]", "B": "CharacterStyle/Bold", "I": "CharacterStyle/Italic",
      "BI": "CharacterStyle/Bold Italic", "K": "CharacterStyle/Key Heading"}

# ------------------------------------------------------------------ story building
class Story:
    def __init__(self, sid):
        self.sid = sid
        self.parts = []
    def para(self, style, runs):
        """runs: list of (charstyle_key, text) or ('TABLE', xml)"""
        out = [f'<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/{style}">']
        for k, t in runs:
            if k == "TABLE":
                out.append(f'<CharacterStyleRange AppliedCharacterStyle="{CS[None]}">{t}</CharacterStyleRange>')
                continue
            if not t:
                continue
            segs = t.split(" ")
            inner = "".join((f"<Content>{esc(s)}</Content>" if s else "") + ("<Br/>" if i < len(segs) - 1 else "")
                            for i, s in enumerate(segs))
            # forced line break inside a paragraph: use U+2028 content
            inner = inner.replace("<Br/>", "<Content> </Content>")
            out.append(f'<CharacterStyleRange AppliedCharacterStyle="{CS[k]}">{inner}</CharacterStyleRange>')
        out.append(f'<CharacterStyleRange AppliedCharacterStyle="{CS[None]}"><Br/></CharacterStyleRange>')
        out.append('</ParagraphStyleRange>')
        self.parts.append("".join(out))
    def xml(self):
        body = "".join(self.parts)
        # strip the final paragraph break
        body = re.sub(r'<CharacterStyleRange AppliedCharacterStyle="[^"]*"><Br/></CharacterStyleRange></ParagraphStyleRange>$',
                      '</ParagraphStyleRange>', body)
        return (HDR + f'<idPkg:Story {NS} DOMVersion="{DOM}"><Story Self="{self.sid}" AppliedTOCStyle="n" TrackChanges="false" '
                f'StoryTitle="$ID/" AppliedNamedGrid="n"><StoryPreference OpticalMarginAlignment="false" OpticalMarginSize="12" '
                f'FrameType="TextFrameType" StoryOrientation="Horizontal" StoryDirection="LeftToRightDirection"/>'
                f'{body}</Story></idPkg:Story>')

def runs_of(node, b=False, i=False):
    out = []
    for ch in node.children:
        if isinstance(ch, NavigableString):
            out.append((("BI" if b and i else "B" if b else "I" if i else None), str(ch)))
        elif isinstance(ch, Tag):
            if ch.name == "br":
                out.append((("BI" if b and i else "B" if b else "I" if i else None), " "))
            elif ch.name in ("strong", "b"):
                out += runs_of(ch, True, i)
            elif ch.name in ("em", "i"):
                out += runs_of(ch, b, True)
            else:
                out += runs_of(ch, b, i)
    return out

def clean(runs):
    res = []
    for k, t in runs:
        t = re.sub(r"[ \t\r\n]+", " ", t)
        t = re.sub(r" ?  ?", " ", t)
        if res and res[-1][0] == k:
            res[-1] = (k, res[-1][1] + t)
        else:
            res.append((k, t))
    if res:
        res[0] = (res[0][0], res[0][1].lstrip())
        res[-1] = (res[-1][0], res[-1][1].rstrip().rstrip(" "))
    return [r for r in res if r[1]]

tcount = [0]
from PIL import ImageFont
FONTDIR = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "fonts"
_fc = {}
def font_for(bold, head, size):
    name = "fraunces-latin-700-normal.ttf" if head else ("libre-baskerville-latin-700-normal.ttf" if bold else "libre-baskerville-latin-400-normal.ttf")
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(str(FONTDIR / name), size=100)
    f = _fc[key]
    class Scaled:
        def getlength(self, t): return f.getlength(t) * size / 100
    return Scaled()

def table_xml(tbl, wide):
    tcount[0] += 1
    tid = f"tbl{tcount[0]}"
    head = [th for th in tbl.find("thead").find_all("th")]
    rows = [[td for td in tr.find_all("td")] for tr in tbl.find("tbody").find_all("tr")]
    ncol = len(head)
    # DesignCraft lays tables out at column width even in a spanning paragraph,
    # so every table is fitted to one column, measured with the real fonts.
    width = COLW
    def cells_of(c):
        return [(head[c].get_text(" ", strip=True), True)] + [((r[c].get_text(" ", strip=True) if c < len(r) else ""), False) for r in rows]
    def plan(size):
        mins, wants = [], []
        for c in range(ncol):
            mn = wt = 0
            for text, is_head in cells_of(c):
                f = font_for(is_head or c == 0, is_head, size)
                words = text.split() or [""]
                mn = max(mn, max(f.getlength(w) for w in words))
                wt = max(wt, f.getlength(text))
            mins.append(mn + 7); wants.append(wt + 7)
        return mins, wants
    size, compact = 7.7, False
    mins, wants = plan(size)
    if sum(mins) > width:
        size, compact = 6.4, True
        mins, wants = plan(size)
    if sum(wants) <= width:
        widths = [w * width / sum(wants) for w in wants]
    else:
        spare = max(0.0, width - sum(mins)); need = [w - m for w, m in zip(wants, mins)]
        tot = sum(need) or 1
        widths = [m + spare * n / tot for m, n in zip(mins, need)]
        if sum(widths) > width:
            widths = [w * width / sum(widths) for w in widths]
    widths = [round(w, 2) for w in widths]
    widths[-1] = round(width - sum(widths[:-1]), 2)
    x = [f'<Table Self="{tid}" HeaderRowCount="1" FooterRowCount="0" BodyRowCount="{len(rows)}" ColumnCount="{ncol}" '
         f'AppliedTableStyle="TableStyle/$ID/[Basic Table]" TableDirection="LeftToRightDirection" '
         f'TopBorderStrokeWeight="0" BottomBorderStrokeWeight="0.5" LeftBorderStrokeWeight="0" RightBorderStrokeWeight="0">']
    for r in range(len(rows) + 1):
        x.append(f'<Row Self="{tid}Row{r}" Name="{r}" MinimumHeight="11" AutoGrow="true"/>')
    for c in range(ncol):
        x.append(f'<Column Self="{tid}Column{c}" Name="{c}" SingleColumnWidth="{widths[c]}"/>')
    def cell(c, r, node, header):
        if header:
            fill, ps = 'FillColor="Color/Black" FillTint="100"', "Table Head Compact" if compact else "Table Head"
        else:
            fill, ps = ('FillColor="Color/Shade" FillTint="100"' if r % 2 == 0 else 'FillColor="Swatch/None"'), "Table Body Compact" if compact else "Table Body"
        rr = clean(runs_of(node)) if node is not None else []
        if not header and c == 0:
            rr = [("B" if k is None else k, t) for k, t in rr]
        st = Story("tmp"); st.para(ps, rr)
        inner = re.sub(r'<CharacterStyleRange AppliedCharacterStyle="[^"]*"><Br/></CharacterStyleRange>', "", st.parts[0])
        return (f'<Cell Self="{tid}i{c}i{r}" Name="{c}:{r}" RowSpan="1" ColumnSpan="1" AppliedCellStyle="CellStyle/$ID/[None]" '
                f'AppliedCellStylePriority="0" {fill} TopInset="2.5" BottomInset="2.5" LeftInset="3" RightInset="3" '
                f'TopEdgeStrokeWeight="0" LeftEdgeStrokeWeight="0" RightEdgeStrokeWeight="0" '
                f'BottomEdgeStrokeWeight="0.5" BottomEdgeStrokeColor="Color/Rule" VerticalJustification="TopAlign">{inner}</Cell>')
    for c in range(ncol):
        x.append(cell(c, 0, head[c], True))
        for r, row in enumerate(rows, start=1):
            x.append(cell(c, r, row[c] if c < len(row) else None, False))
    x.append("</Table>")
    return "".join(x)

# ------------------------------------------------------------------ parse HTML
soup = BeautifulSoup(SRC.read_text(), "lxml")
main = soup.find("main")
story = Story("u_main")

def emit_block(el, ctx=None):
    name = el.name
    cls = el.get("class") or []
    if name == "section":
        for ch in el.children:
            if isinstance(ch, Tag): emit_block(ch)
        return
    if name == "div":
        if "titlepage" in cls:
            for ch in el.find_all(recursive=False):
                c2 = ch.get("class") or []
                st = {"tp-code": "Title Code", "tp-title": "Title", "tp-by": "Title Byline",
                      "tp-levels": "Title Levels", "tp-note": "Title Note"}.get(c2[0] if c2 else "", "Title Body")
                story.para(st, clean(runs_of(ch)))
            return
        st = "Boxed Text" if "box" in cls else "Map Placeholder" if "map" in cls else "Illustration Placeholder" if "img" in cls else "Body"
        for ch in el.find_all(recursive=False):
            if ch.name in ("p",):
                story.para(st, clean(runs_of(ch)))
            else:
                emit_block(ch)
        return
    if name == "h1":
        story.para("Heading 1", clean(runs_of(el))); return
    if name == "h2":
        story.para("Heading 2", clean(runs_of(el))); return
    if name == "h3":
        story.para("Monster Name" if "mon" in cls else "Heading 3", clean(runs_of(el))); return
    if name == "p":
        r = clean(runs_of(el))
        if "key" in cls:
            if r and r[0][0] == "B": r[0] = ("K", r[0][1])
            story.para("Key", r)
        elif "stat" in cls:
            # each line is its own stat entry
            text_runs, cur = [], []
            for k, t in r:
                pieces = t.split(" ")
                for j, pc in enumerate(pieces):
                    if pc: cur.append((k, pc))
                    if j < len(pieces) - 1:
                        text_runs.append(cur); cur = []
            text_runs.append(cur)
            for tr in text_runs:
                tr = clean(tr)
                if tr: story.para("Stat", [("I" if k is None else k, t) for k, t in tr])
        elif "monblock" in cls:
            story.para("MonsterStats", r)
        else:
            story.para("Body", r)
        return
    if name in ("ul", "ol"):
        for n, li in enumerate(el.find_all("li", recursive=False), start=1):
            r = clean(runs_of(li))
            bullet = "• " if name == "ul" else f"{n}. "
            story.para("ListItem", [(None, bullet)] + r)
        return
    if name == "table":
        wide = "wide" in cls
        story.para("Table Anchor Wide" if wide else "Table Anchor", [("TABLE", table_xml(el, wide))])
        return
    if name == "hr":
        return
    # fallback
    r = clean(runs_of(el))
    if r: story.para("Body", r)

for ch in main.children:
    if isinstance(ch, Tag): emit_block(ch)

# ------------------------------------------------------------------ cover / back stories
small_stories = []
def mk_story(sid, paras):
    s = Story(sid)
    for st, txt in paras:
        s.para(st, [(None, txt)] if isinstance(txt, str) else txt)
    small_stories.append(s)
    return sid

cv = BeautifulSoup((ROOT / "cover.html").read_text(), "lxml")
art_ps = [p.get_text(" ", strip=True) for p in cv.select(".cv-art p")]
mk_story("u_cv_code", [("Cover Code Label", "Adventure Module"), ("Cover Code", "KR1")])
mk_story("u_cv_head", [("Cover Small", "Introductory Adventure"), ("Cover Title", "The Fortress of Kingsreach")])
mk_story("u_cv_art", [("Cover Art Label", "[COVER ILLUSTRATION — full color, framed]")] + [("Cover Art Text", t) for t in art_ps])
mk_story("u_cv_bot", [("Cover Levels", cv.select_one(".cv-levels").get_text(strip=True)),
                      ("Cover Blurb", cv.select_one(".cv-blurb").get_text(" ", strip=True)),
                      ("Cover Small", cv.select_one(".cv-compat").get_text(" ", strip=True))])
bc = soup.select_one(".backcover")
bparas = [("Back Title", bc.find("h2").get_text(strip=True))]
for p in bc.find_all("p"):
    if p.find("strong") and p.get_text(strip=True) == p.find("strong").get_text(strip=True):
        bparas.append(("Back Tag", p.get_text(strip=True)))
    else:
        bparas.append(("Back Body", clean(runs_of(p))))
mk_story("u_back", bparas)
mk_story("u_hdr_l", [("Header Code", "KR1")])
mk_story("u_hdr_r", [("Header", "The Fortress of Kingsreach")])
folio = Story("u_folio")
folio.parts.append('<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/Folio"><CharacterStyleRange '
                   f'AppliedCharacterStyle="{CS[None]}"><Content><?ACE 18?></Content></CharacterStyleRange></ParagraphStyleRange>')
small_stories.append(folio)

# ------------------------------------------------------------------ geometry helpers
def path(x1, y1, x2, y2):
    pts = [(x1, y1), (x1, y2), (x2, y2), (x2, y1)]
    pp = "".join(f'<PathPointType Anchor="{x} {y}" LeftDirection="{x} {y}" RightDirection="{x} {y}"/>' for x, y in pts)
    return f'<Properties><PathGeometry><GeometryPathType PathOpen="false"><PathPointArray>{pp}</PathPointArray></GeometryPathType></PathGeometry></Properties>'

def tframe(fid, story_id, x1, y1, x2, y2, cols=1, prev="n", nxt="n", inset=0, valign="TopAlign", fill="Swatch/None", stroke="Swatch/None", sw=0):
    return (f'<TextFrame Self="{fid}" ParentStory="{story_id}" PreviousTextFrame="{prev}" NextTextFrame="{nxt}" ContentType="TextType" '
            f'ItemLayer="ub3" FillColor="{fill}" StrokeColor="{stroke}" StrokeWeight="{sw}" ItemTransform="1 0 0 1 0 0" '
            f'AppliedObjectStyle="ObjectStyle/$ID/[Normal Text Frame]">{path(x1, y1, x2, y2)}'
            f'<TextFramePreference TextColumnCount="{cols}" TextColumnGutter="{GUT}" TextColumnFixedWidth="{COLW if cols == 2 else x2 - x1 - 2 * inset}" '
            f'UseFixedColumnWidth="false" AutoSizingType="Off" VerticalJustification="{valign}" '
            f'InsetSpacing="{inset} {inset} {inset} {inset}"/></TextFrame>')

def rect(rid, x1, y1, x2, y2, fill, stroke="Swatch/None", sw=0):
    return (f'<Rectangle Self="{rid}" ItemLayer="ub3" FillColor="{fill}" StrokeColor="{stroke}" StrokeWeight="{sw}" '
            f'ItemTransform="1 0 0 1 0 0" AppliedObjectStyle="ObjectStyle/$ID/[Normal Graphics Frame]">{path(x1, y1, x2, y2)}</Rectangle>')

def page_xml(pid, name, master):
    return (f'<Page Self="{pid}" Name="{name}" AppliedMaster="{master}" GeometricBounds="0 0 {PH} {PW}" ItemTransform="1 0 0 1 0 {Y0}" '
            f'OverrideList="" MasterPageTransform="1 0 0 1 0 0" TabOrder="" GridStartingPoint="TopOutside" UseMasterGrid="true">'
            f'<Properties><PageColor type="enumeration">UseMasterColor</PageColor></Properties>'
            f'<MarginPreference ColumnCount="2" ColumnGutter="{GUT}" Top="{MT}" Bottom="{MB}" Left="{ML}" Right="{MR}" '
            f'ColumnDirection="Horizontal" ColumnsPositions="0 {COLW} {COLW + GUT} {FULLW}"/></Page>')

def spread_file(sid, inner, pagecount=1):
    return (HDR + f'<idPkg:Spread {NS} DOMVersion="{DOM}"><Spread Self="{sid}" PageTransitionType="None" PageTransitionDirection="NotApplicable" '
            f'PageTransitionDuration="Medium" ShowMasterItems="true" PageCount="{pagecount}" BindingLocation="0" AllowPageShuffle="true" '
            f'ItemTransform="1 0 0 1 0 0" FlattenerOverride="Default">{inner}</Spread></idPkg:Spread>')

files = {}
spreads = []
X1, X2 = ML, PW - MR
TY1, TY2 = Y0 + MT, Y0 + PH - MB

# Cover (page 1)
pad = 32.4
inner = page_xml("pg_cover", "1", "n")
inner += rect("r_cv_bg", 0, Y0, PW, -Y0, "Color/Sea")
top_y1, top_y2 = Y0 + pad, Y0 + pad + 90
inner += rect("r_cv_code", pad, top_y1, pad + 90, top_y2, "Color/Paper")
inner += tframe("tf_cv_code", "u_cv_code", pad, top_y1, pad + 90, top_y2, valign="CenterAlign")
inner += tframe("tf_cv_head", "u_cv_head", pad + 105, top_y1, PW - pad, top_y2, valign="CenterAlign")
art_y1, art_y2 = top_y2 + 14, -Y0 - pad - 80
inner += rect("r_cv_art", pad, art_y1, PW - pad, art_y2, "Color/Deep", "Color/Paper", 2)
inner += tframe("tf_cv_art", "u_cv_art", pad + 8, art_y1 + 8, PW - pad - 8, art_y2 - 8, inset=28, valign="CenterAlign")
inner += tframe("tf_cv_bot", "u_cv_bot", pad, art_y2 + 12, PW - pad, -Y0 - pad, valign="TopAlign")
files["Spreads/Spread_sp_cover.xml"] = spread_file("sp_cover", inner); spreads.append("sp_cover")

# Interior pages
frame_ids = [f"tf_main{i}" for i in range(INTERIOR_PAGES)]
page_ids = []
for i in range(INTERIOR_PAGES):
    pid = f"pg{i + 2}"; page_ids.append(pid)
    inner = page_xml(pid, str(i + 2), "ms_A")
    inner += tframe(frame_ids[i], "u_main", X1, TY1, X2, TY2, cols=2,
                    prev=frame_ids[i - 1] if i else "n", nxt=frame_ids[i + 1] if i < INTERIOR_PAGES - 1 else "n")
    sid = f"sp{i + 2}"
    files[f"Spreads/Spread_{sid}.xml"] = spread_file(sid, inner); spreads.append(sid)

# Back cover
inner = page_xml("pg_back", str(INTERIOR_PAGES + 2), "n")
inner += rect("r_bk_bg", 0, Y0, PW, -Y0, "Color/Sea")
inner += rect("r_bk_box", 58, Y0 + 170, PW - 58, -Y0 - 170, "Color/Deep", "Color/Paper", 3)
inner += tframe("tf_back", "u_back", 58, Y0 + 170, PW - 58, -Y0 - 170, inset=36, valign="CenterAlign")
files["Spreads/Spread_sp_back.xml"] = spread_file("sp_back", inner); spreads.append("sp_back")

# Master spread A: running heads + folio
mp = (f'<Page Self="ms_A_p" Name="A" AppliedMaster="n" GeometricBounds="0 0 {PH} {PW}" ItemTransform="1 0 0 1 0 {Y0}" '
      f'OverrideList="" MasterPageTransform="1 0 0 1 0 0" TabOrder="" GridStartingPoint="TopOutside" UseMasterGrid="true">'
      f'<MarginPreference ColumnCount="2" ColumnGutter="{GUT}" Top="{MT}" Bottom="{MB}" Left="{ML}" Right="{MR}" '
      f'ColumnDirection="Horizontal" ColumnsPositions="0 {COLW} {COLW + GUT} {FULLW}"/></Page>')
mp += tframe("tf_hdr_l", "u_hdr_l", X1, Y0 + 24, X1 + 200, Y0 + 38)
mp += tframe("tf_hdr_r", "u_hdr_r", X2 - 260, Y0 + 24, X2, Y0 + 38)
mp += tframe("tf_folio", "u_folio", X1, -Y0 - 34, X2, -Y0 - 20)
files["MasterSpreads/MasterSpread_ms_A.xml"] = (HDR + f'<idPkg:MasterSpread {NS} DOMVersion="{DOM}"><MasterSpread Self="ms_A" Name="A-Master" '
    f'NamePrefix="A" BaseName="Master" ShowMasterItems="true" PageCount="1" OverriddenPageItemProps="" PrimaryTextFrame="n" '
    f'ItemTransform="1 0 0 1 0 0">{mp}</MasterSpread></idPkg:MasterSpread>')

# ------------------------------------------------------------------ resources
def color(name, rgb):
    return (f'<Color Self="Color/{name}" Model="Process" Space="RGB" ColorValue="{rgb}" ColorOverride="Normal" '
            f'AlternateSpace="NoAlternateColor" AlternateColorValue="" Name="{name}" ColorEditable="true" ColorRemovable="true" '
            f'Visible="true" SwatchCreatorID="7937"/>')
graphic = (HDR + f'<idPkg:Graphic {NS} DOMVersion="{DOM}">'
    '<Color Self="Color/Black" Model="Process" Space="CMYK" ColorValue="0 0 0 100" ColorOverride="Specialblack" AlternateSpace="NoAlternateColor" AlternateColorValue="" Name="Black" ColorEditable="false" ColorRemovable="false" Visible="true" SwatchCreatorID="7937"/>'
    '<Color Self="Color/Paper" Model="Process" Space="CMYK" ColorValue="0 0 0 0" ColorOverride="Specialpaper" AlternateSpace="NoAlternateColor" AlternateColorValue="" Name="Paper" ColorEditable="true" ColorRemovable="false" Visible="true" SwatchCreatorID="7937"/>'
    '<Color Self="Color/Registration" Model="Registration" Space="CMYK" ColorValue="100 100 100 100" ColorOverride="Specialregistration" AlternateSpace="NoAlternateColor" AlternateColorValue="" Name="Registration" ColorEditable="false" ColorRemovable="false" Visible="true" SwatchCreatorID="7937"/>'
    + color("Sea", "29 79 110") + color("Deep", "14 42 59") + color("Shade", "233 227 211") + color("MapBlue", "227 238 246")
    + color("MapLine", "91 141 179") + color("MapInk", "22 58 82") + color("Ink2", "61 58 51") + color("Rule", "201 193 174")
    + color("Gold", "255 210 122") + color("CoverPale", "214 230 239") +
    '<Swatch Self="Swatch/None" Name="None" ColorEditable="false" ColorRemovable="false" Visible="true" SwatchCreatorID="7937"/>'
    '<StrokeStyle Self="StrokeStyle/$ID/Solid" Name="$ID/Solid"/>'
    '<StrokeStyle Self="StrokeStyle/$ID/ThickThin" Name="$ID/ThickThin"/>'
    '<StrokeStyle Self="StrokeStyle/$ID/ThinThick" Name="$ID/ThinThick"/>'
    '</idPkg:Graphic>')

def font_family(fid, fam, styles):
    fs = "".join(f'<Font Self="{fid}Font{fam} {s}" FontFamily="{fam}" Name="{fam} {s}" PostScriptName="$ID/" Status="Installed" '
                 f'FontStyleName="{s}" FontType="TrueType" WritingScript="0" FullName="{fam} {s}" FullNameNative="{fam} {s}" '
                 f'FontStyleNameNative="{s}" PlatformName="$ID/" Version=""/>' for s in styles)
    return f'<FontFamily Self="{fid}" Name="{fam}">{fs}</FontFamily>'
fonts = (HDR + f'<idPkg:Fonts {NS} DOMVersion="{DOM}">' + font_family("di1", BASK, ["Regular", "Bold", "Italic"])
         + font_family("di2", FRAUN, ["Regular", "Bold", "Black", "Italic"]) + '</idPkg:Fonts>')

styles = (HDR + f'<idPkg:Styles {NS} DOMVersion="{DOM}">'
    '<RootCharacterStyleGroup Self="u79"><CharacterStyle Self="CharacterStyle/$ID/[No character style]" Imported="false" Name="$ID/[No character style]"/>'
    + "".join(CHAR_STYLES.values()) + '</RootCharacterStyleGroup>'
    '<RootParagraphStyleGroup Self="u78">'
    f'<ParagraphStyle Self="ParagraphStyle/$ID/[No paragraph style]" Name="$ID/[No paragraph style]" Imported="false" FillColor="Color/Black" '
    f'FontStyle="Regular" PointSize="9" Justification="LeftAlign" Hyphenation="true" SpaceBefore="0" SpaceAfter="0">'
    f'<Properties><AppliedFont type="string">{BASK}</AppliedFont><Leading type="enumeration">Auto</Leading></Properties></ParagraphStyle>'
    '<ParagraphStyle Self="ParagraphStyle/$ID/NormalParagraphStyle" Name="$ID/NormalParagraphStyle" Imported="false">'
    '<Properties><BasedOn type="object">ParagraphStyle/$ID/[No paragraph style]</BasedOn></Properties></ParagraphStyle>'
    + "".join(PARA_STYLES) + '</RootParagraphStyleGroup>'
    '<TOCStyle Self="TOCStyle/$ID/DefaultTOCStyleName" Name="$ID/DefaultTOCStyleName" Title="Contents" TitleStyle="ParagraphStyle/$ID/[No paragraph style]" RunIn="false" IncludeHidden="false" IncludeBookDocuments="false" CreateBookmarks="true" SetTitleInFrame="false"/>'
    '<RootCellStyleGroup Self="u8a"><CellStyle Self="CellStyle/$ID/[None]" Name="$ID/[None]" AppliedParagraphStyle="ParagraphStyle/$ID/[No paragraph style]"/></RootCellStyleGroup>'
    '<RootTableStyleGroup Self="u8c"><TableStyle Self="TableStyle/$ID/[No table style]" Name="$ID/[No table style]"/>'
    '<TableStyle Self="TableStyle/$ID/[Basic Table]" Name="$ID/[Basic Table]"><Properties><BasedOn type="object">TableStyle/$ID/[No table style]</BasedOn></Properties></TableStyle></RootTableStyleGroup>'
    '<RootObjectStyleGroup Self="u97"><ObjectStyle Self="ObjectStyle/$ID/[None]" Name="$ID/[None]"/>'
    '<ObjectStyle Self="ObjectStyle/$ID/[Normal Graphics Frame]" Name="$ID/[Normal Graphics Frame]"><Properties><BasedOn type="object">ObjectStyle/$ID/[None]</BasedOn></Properties></ObjectStyle>'
    '<ObjectStyle Self="ObjectStyle/$ID/[Normal Text Frame]" Name="$ID/[Normal Text Frame]"><Properties><BasedOn type="object">ObjectStyle/$ID/[None]</BasedOn></Properties></ObjectStyle>'
    '</RootObjectStyleGroup></idPkg:Styles>')

npages = INTERIOR_PAGES + 2
prefs = (HDR + f'<idPkg:Preferences {NS} DOMVersion="{DOM}">'
    f'<DocumentPreference PageHeight="{PH}" PageWidth="{PW}" PagesPerDocument="{npages}" FacingPages="false" '
    f'DocumentBleedTopOffset="9" DocumentBleedBottomOffset="9" DocumentBleedInsideOrLeftOffset="9" DocumentBleedOutsideOrRightOffset="9" '
    f'DocumentBleedUniformSize="true" AllowPageShuffle="true" OverprintBlack="true" ColumnDirection="Horizontal" Intent="PrintIntent" PageBinding="LeftToRight"/>'
    f'<MarginPreference ColumnCount="2" ColumnGutter="{GUT}" Top="{MT}" Bottom="{MB}" Left="{ML}" Right="{MR}" ColumnDirection="Horizontal" ColumnsPositions="0 {COLW} {COLW + GUT} {FULLW}"/>'
    f'<TextPreference SmartTextReflow="true" AddPages="EndOfStory" LimitToMasterTextFrames="false" PreserveFacingPageSpreads="false" DeleteEmptyPages="true"/>'
    '</idPkg:Preferences>')

backing = HDR + f'<idPkg:BackingStory {NS} DOMVersion="{DOM}"><XmlStory Self="u_bs" AppliedTOCStyle="n" TrackChanges="false" StoryTitle="$ID/" AppliedNamedGrid="n"><ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/$ID/NormalParagraphStyle"><CharacterStyleRange AppliedCharacterStyle="CharacterStyle/$ID/[No character style]"/></ParagraphStyleRange></XmlStory></idPkg:BackingStory>'
tags = HDR + f'<idPkg:Tags {NS} DOMVersion="{DOM}"><XMLTag Self="XMLTag/Root" Name="Root"><Properties><TagColor type="enumeration">LightBlue</TagColor></Properties></XMLTag></idPkg:Tags>'

all_stories = [story] + small_stories
files["Resources/Graphic.xml"] = graphic
files["Resources/Fonts.xml"] = fonts
files["Resources/Styles.xml"] = styles
files["Resources/Preferences.xml"] = prefs
files["XML/BackingStory.xml"] = backing
files["XML/Tags.xml"] = tags
for s in all_stories:
    files[f"Stories/Story_{s.sid}.xml"] = s.xml()

designmap = (HDR + '<?aid style="50" type="document" readerVersion="6.0" featureSet="257" product="15.0(209)" ?>\n'
    f'<Document {NS} DOMVersion="{DOM}" Self="d" StoryList="{" ".join(s.sid for s in all_stories)}" Name="KR1-Fortress-of-Kingsreach.indd" '
    'ZeroPoint="0 0" ActiveLayer="ub3" CMYKProfile="U.S. Web Coated (SWOP) v2" RGBProfile="sRGB IEC61966-2.1" '
    'SolidColorIntent="UseColorSettings" AfterBlendingIntent="UseColorSettings" DefaultImageIntent="UseColorSettings" '
    'RGBPolicy="PreserveEmbeddedProfiles" CMYKPolicy="CombinationOfPreserveAndSafeCmyk" AccurateLABSpots="false">'
    '<Language Self="Language/$ID/English%3a USA" Name="$ID/English: USA" SingleQuotes="&#8216;&#8217;" DoubleQuotes="&#8220;&#8221;" '
    'PrimaryLanguageName="$ID/English" SublanguageName="$ID/USA" Id="269" HyphenationVendor="Hunspell" SpellingVendor="Hunspell"/>'
    '<idPkg:Graphic src="Resources/Graphic.xml"/><idPkg:Fonts src="Resources/Fonts.xml"/><idPkg:Styles src="Resources/Styles.xml"/>'
    '<idPkg:Preferences src="Resources/Preferences.xml"/><idPkg:Tags src="XML/Tags.xml"/>'
    '<Layer Self="ub3" Name="Layer 1" Visible="true" Locked="false" IgnoreWrap="false" ShowGuides="true" LockGuides="false" UI="true" '
    'Expendable="true" Printable="true"><Properties><LayerColor type="enumeration">LightBlue</LayerColor></Properties></Layer>'
    '<idPkg:MasterSpread src="MasterSpreads/MasterSpread_ms_A.xml"/>'
    + "".join(f'<idPkg:Spread src="Spreads/Spread_{s}.xml"/>' for s in spreads)
    + f'<Section Self="sec1" Length="{npages}" Name="" ComparisonName="" PageNumberStyle="Arabic" ContinueNumbering="false" '
      f'IncludeSectionPrefix="false" PageNumberFormat="" Marker="" PageStart="pg_cover" SectionPrefix="" PageNumberStart="1"/>'
    '<idPkg:BackingStory src="XML/BackingStory.xml"/>'
    + "".join(f'<idPkg:Story src="Stories/Story_{s.sid}.xml"/>' for s in all_stories)
    + '</Document>')
files["designmap.xml"] = designmap

# META-INF
files["META-INF/container.xml"] = (HDR + '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
    '<rootfiles><rootfile full-path="designmap.xml" media-type="text/xml"/></rootfiles></container>')

with zipfile.ZipFile(OUT, "w") as z:
    z.writestr(zipfile.ZipInfo("mimetype"), "application/vnd.adobe.indesign-idml-package", compress_type=zipfile.ZIP_STORED)
    order = ["designmap.xml", "META-INF/container.xml"] + sorted(k for k in files if k not in ("designmap.xml", "META-INF/container.xml"))
    for k in order:
        z.writestr(k, files[k], compress_type=zipfile.ZIP_DEFLATED)
print("wrote", OUT, "paragraphs:", len(story.parts), "tables:", tcount[0])

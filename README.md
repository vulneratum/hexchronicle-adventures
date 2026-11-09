# Hex Chronicle Adventures

Old-school adventure modules for the [Hex Chronicle](https://hexchronicle.com) world, written in plain text and built into finished books.

The Markdown and YAML here are the **master copy**. The PDF, the DesignCraft/InDesign layout, and (later) Foundry VTT modules are all built from them; never edit a built file by hand.

## Modules

| Code | Title | Levels | Home hex | Folder |
|---|---|---|---|---|
| KR1 | The Fortress of Kingsreach | 1–3 | 2863-127 | [`KR1-fortress-of-kingsreach/`](KR1-fortress-of-kingsreach/) |

## Layout

Each module lives in its own folder:

```
KR1-fortress-of-kingsreach/
  src/               the module text, one Markdown file per chapter
  cover.html         front cover
  style.css          TSR-style print layout
  fonts/             bundled fonts (SIL Open Font License)
  hexchronicle.yaml  the module's home hex and site addresses on the Hex Chronicle map
  build.py           Markdown -> HTML
  render.js          HTML -> PDF (Playwright/Chromium)
  make_idml.py       HTML -> IDML for DesignCraft or InDesign
```

## Building a module

Requirements: Python 3 with `markdown`, `beautifulsoup4`, `lxml` and `pillow`, and Node.js with `playwright` (Chromium).

```
pip install -r requirements.txt
npm install
npx playwright install chromium

cd KR1-fortress-of-kingsreach
python build.py                 # writes out/kingsreach.html
node render.js out/kingsreach.html out/KR1-Fortress-of-Kingsreach.pdf
python make_idml.py             # writes out/KR1-Fortress-of-Kingsreach.idml
```


## Releases

Each finished version of a module is published as a GitHub Release with its PDF and DesignCraft package attached, so every version stays downloadable.

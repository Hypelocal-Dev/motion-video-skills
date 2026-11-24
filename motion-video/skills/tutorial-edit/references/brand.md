# Brand: guidelines to theme.json

Goal: every card, caption and chip uses the brand's colors and type, and the logo
closes the video. Do this once per brand, then save it as a kit.

## 1. Read the guidelines

- Try the Read tool on the PDF first. It needs poppler for page images
  (`brew install poppler`; ask before installing).
- Without poppler on macOS, render pages with PDFKit (no install needed). Save this as
  `work/pdf_pages.swift` and run `swift work/pdf_pages.swift brand/guidelines.pdf work/brand-pages`:

  ```swift
  import PDFKit; import AppKit
  let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1]))!
  let out = CommandLine.arguments[2]
  try? FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)
  for i in 0..<doc.pageCount {
    let p = doc.page(at: i)!; let r = p.bounds(for: .mediaBox)
    let img = p.thumbnail(of: NSSize(width: 1200, height: 1200 * r.height / r.width), for: .mediaBox)
    let rep = NSBitmapImageRep(data: img.tiffRepresentation!)!
    try! rep.representation(using: .png, properties: [:])!
      .write(to: URL(fileURLWithPath: "\(out)/p\(String(format: "%02d", i + 1)).png"))
  }
  ```

  Tile the pages into one sheet to find the color and type pages, then read those at
  full size. Take hex values from the page text, never by eye from a screenshot.

## 2. Write brand/theme.json

Map the palette onto the theme keys (format: `plan-format.md`):

- `ink`: the main brand accent. If the brand has two blues, the brighter one.
- `deep`: the darker partner of the accent, for big numbers.
- `paper` and `bg`: the brand's white or lightest tint, nudged toward the accent.
- `dark`: the brand's near-black. `soft`: a mid gray from the palette.
- `head_font` / `body_font`: the brand's heading and body fonts. Check each is on Google
  Fonts; if not, pick the nearest family and say so.
- `wordmark`: the brand name as the logo writes it. `logo`: the logo file in `brand/`
  for light backgrounds (SVG first), and `logo_on_dark` for the light-colored version
  when the brand has one. A logo PNG needs a transparent background. Open an SVG and
  check it holds paths, not a wrapped PNG.

Never redraw a logo with text when a logo file exists. If there's no file, use the
wordmark and tell the person the logo is a stand-in.

## 3. Confirm and save

Show the palette as one line (`ink #2F6BFF, deep #123A9C, ...`) and the fonts. After a
yes, save the kit: `python3 $MV/tutorial_new.py brand-save <name> <folder>`. The next
project starts with `--brand <name>`. Kits stay on this machine; never commit one.

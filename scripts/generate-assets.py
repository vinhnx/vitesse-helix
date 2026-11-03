#!/usr/bin/env python3
"""Generate README artwork for vitesse-helix straight from the theme file.

Keeps docs/ images in sync with vitesse-black.toml: colors are read from the
[palette] table, so a palette change is reflected by re-running this script.
"""

import html
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
THEME = ROOT / "vitesse-black.toml"
OUT = ROOT / "assets"

# (palette key, label, what Helix uses it for)
SWATCHES = [
    ("black", "black", "background #000000"),
    ("fg", "fg", "ui.text / default foreground"),
    ("fg_dim", "fg_dim", "statusline, inactive text"),
    ("comment", "comment", "comments (italic)"),
    ("teal", "teal", "keyword, tag, function.special"),
    ("rust_red", "rust_red", "operator, storage.type"),
    ("green", "green", "function, entity"),
    ("teal_light", "teal_light", "type, type.builtin"),
    ("teal_num", "teal_num", "constant.numeric"),
    ("brown", "brown", "constant, variable.builtin"),
    ("olive", "olive", "variable.other.member, property"),
    ("salmon", "salmon", "string, markup.link"),
    ("orange", "orange", "attribute, variable"),
    ("pink", "pink", "namespace"),
    ("yellow", "yellow", "character escape, search match"),
    ("red", "red", "error, diff.minus"),
    ("blue", "blue", "info, diff.delta"),
    ("orange_soft", "orange_soft", "variable"),
]

# (text, palette key) runs, rendered like a small Rust source file
CODE = [
    [("fn ", "teal"), ("main", "green"), ("() {", "delimiter")],
    [
        ("    let ", "teal"),
        ("count", "orange_soft"),
        (": ", "delimiter"),
        ("u32", "teal_light"),
        (" = ", "rust_red"),
        ("42", "teal_num"),
        (";", "delimiter"),
    ],
    [("    // muted, italic comment", "comment")],
    [
        ("    println!", "green"),
        ("(", "delimiter"),
        ('"hello world"', "salmon"),
        (", ", "delimiter"),
        ("count", "orange_soft"),
        (");", "delimiter"),
    ],
    [("}", "delimiter")],
]


def load_palette() -> dict[str, str]:
    data = tomllib.loads(THEME.read_text())
    return {k: v.lstrip("#") for k, v in data["palette"].items()}


def swatch_svg(pal: dict[str, str]) -> str:
    cols, cw, ch = 3, 280, 62
    rows = (len(SWATCHES) + cols - 1) // cols
    width, height = cols * cw + 24, rows * ch + 56
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Vitesse color palette">',
        f'<rect width="{width}" height="{height}" fill="#{pal["black"]}"/>',
        f'<text x="16" y="30" font-family="ui-monospace,Menlo,monospace" '
        f'font-size="15" fill="#{pal["fg"]}" font-weight="600">'
        f"Vitesse \u2014 palette</text>",
    ]
    for i, (key, label, desc) in enumerate(SWATCHES):
        col, row = i % cols, i // cols
        x = 16 + col * cw
        y = 52 + row * ch
        color = pal[key]
        out += [
            f'<rect x="{x}" y="{y}" width="34" height="34" rx="6" fill="#{color}" '
            f'stroke="#{pal["selection_strong"]}" stroke-width="1"/>',
            f'<text x="{x + 44}" y="{y + 15}" font-family="ui-monospace,Menlo,monospace" '
            f'font-size="12.5" fill="#{pal["fg"]}" font-weight="600">{label}</text>',
            f'<text x="{x + 44}" y="{y + 29}" font-family="ui-monospace,Menlo,monospace" '
            f'font-size="11" fill="#{pal["comment"]}">#{color}</text>',
        ]
    out.append("</svg>")
    return "\n".join(out)


def code_svg(pal: dict[str, str]) -> str:
    width, line_h, pad = 640, 26, 18
    height = line_h * len(CODE) + pad * 2 + 30
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Vitesse applied to Rust code">',
        f'<rect width="{width}" height="{height}" fill="#{pal["black"]}"/>',
    ]
    y = pad
    for n, line in enumerate(CODE, start=1):
        y += line_h
        out.append(
            f'<text x="{pad}" y="{y}" font-family="ui-monospace,Menlo,monospace" '
            f'font-size="13" fill="#{pal["linenr"]}">{n}</text>'
        )
        x = pad + 34
        for text, key in line:
            color = pal.get(key, pal["fg"])
            italic = ' font-style="italic"' if key == "comment" else ""
            out.append(
                f'<text x="{x}" y="{y}" font-family="ui-monospace,Menlo,monospace" '
                f'font-size="13" fill="#{color}"{italic} xml:space="preserve">'
                f"{html.escape(text)}</text>"
            )
            x += len(text) * 7.85
    # statusline strip
    sy = height - 30
    out += [
        f'<rect x="0" y="{sy}" width="{width}" height="30" fill="#{pal["black"]}"/>',
        f'<rect x="0" y="{sy}" width="46" height="30" fill="#{pal["teal"]}"/>',
        f'<text x="11" y="{sy + 20}" font-family="ui-monospace,Menlo,monospace" '
        f'font-size="12.5" font-weight="700" fill="#{pal["black"]}">NOR</text>',
        f'<text x="58" y="{sy + 20}" font-family="ui-monospace,Menlo,monospace" '
        f'font-size="12" fill="#{pal["fg_dim"]}">main.rs</text>',
    ]
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    pal = load_palette()
    OUT.mkdir(exist_ok=True)
    (OUT / "palette.svg").write_text(swatch_svg(pal))
    (OUT / "screenshot.svg").write_text(code_svg(pal))
    print(f"wrote {OUT / 'palette.svg'}")
    print(f"wrote {OUT / 'screenshot.svg'}")


if __name__ == "__main__":
    main()

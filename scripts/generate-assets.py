#!/usr/bin/env python3
"""Generate README artwork for the Vitesse Helix themes.

Every color is read from the theme files' own `[palette]` tables, so the docs
cannot drift from the themes. Run after `port-themes.py`.
"""

import html
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

VARIANTS = [
    "vitesse-black",
    "vitesse-dark",
    "vitesse-dark-soft",
    "vitesse-light",
    "vitesse-light-soft",
]

# (palette key, label, what Helix uses it for)
SWATCHES = [
    ("bg", "bg", "editor background"),
    ("fg", "fg", "ui.text / default foreground"),
    ("fg_dim", "fg_dim", "statusline, inactive text"),
    ("comment", "comment", "comments (italic)"),
    ("c_keyword", "keyword", "keyword, tag"),
    ("c_keyword_storage", "storage", "storage.type"),
    ("c_function", "function", "function, entity"),
    ("c_type", "type", "type, type.builtin"),
    ("c_constant_numeric", "number", "constant.numeric"),
    ("c_constant", "constant", "constant"),
    ("c_variable_other_member", "member", "property, member"),
    ("c_string", "string", "string"),
    ("c_attribute", "attribute", "attribute, variable"),
    ("c_namespace", "namespace", "namespace"),
    ("c_constant_character_escape", "escape", "character escape"),
    ("error", "error", "error, diff.minus"),
    ("info", "info", "info, diff.delta"),
]

CODE = [
    [("fn ", "c_keyword"), ("main", "c_function"), ("() {", "c_punctuation")],
    [
        ("    let ", "c_keyword"),
        ("count", "c_attribute"),
        (": ", "c_punctuation"),
        ("u32", "c_type"),
        (" = ", "c_keyword_operator"),
        ("42", "c_constant_numeric"),
        (";", "c_punctuation"),
    ],
    [("    // muted, italic comment", "comment")],
    [
        ("    println!", "c_function"),
        ("(", "c_punctuation"),
        ('"hello world"', "c_string"),
        (", ", "c_punctuation"),
        ("count", "c_attribute"),
        (");", "c_punctuation"),
    ],
    [("}", "c_punctuation")],
]


def load(variant: str) -> dict[str, str]:
    data = tomllib.loads((ROOT / f"{variant}.toml").read_text())
    return {k: v.lstrip("#") for k, v in data["palette"].items()}


def swatch_svg(variant: str, pal: dict[str, str]) -> str:
    cols, cw, ch = 3, 280, 62
    rows = (len(SWATCHES) + cols - 1) // cols
    width, height = cols * cw + 24, rows * ch + 56
    border = pal["selection_strong"]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Vitesse palette ({variant})">',
        f'<rect width="{width}" height="{height}" fill="#{pal["bg"]}"/>',
        f'<text x="16" y="30" font-family="ui-monospace,Menlo,monospace" '
        f'font-size="15" fill="#{pal["fg"]}" font-weight="600">'
        f"Vitesse \u2014 palette</text>",
    ]
    for i, (key, label, _desc) in enumerate(SWATCHES):
        col, row = i % cols, i // cols
        x, y = 16 + col * cw, 52 + row * ch
        color = pal.get(key, pal["fg"])
        out += [
            f'<rect x="{x}" y="{y}" width="34" height="34" rx="6" fill="#{color}" '
            f'stroke="#{border}" stroke-width="1"/>',
            f'<text x="{x + 44}" y="{y + 15}" font-family="ui-monospace,Menlo,monospace" '
            f'font-size="12.5" fill="#{pal["fg"]}" font-weight="600">{label}</text>',
            f'<text x="{x + 44}" y="{y + 29}" font-family="ui-monospace,Menlo,monospace" '
            f'font-size="11" fill="#{pal["comment"]}">#{color}</text>',
        ]
    out.append("</svg>")
    return "\n".join(out)


def code_svg(variant: str, pal: dict[str, str]) -> str:
    width, line_h, pad = 640, 26, 18
    height = line_h * len(CODE) + pad * 2 + 30
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Vitesse applied to Rust code ({variant})">',
        f'<rect width="{width}" height="{height}" fill="#{pal["bg"]}"/>',
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
    sy = height - 30
    out += [
        f'<rect x="0" y="{sy}" width="{width}" height="30" fill="#{pal["bg"]}"/>',
        f'<rect x="0" y="{sy}" width="46" height="30" fill="#{pal["normal_bg"]}"/>',
        f'<text x="11" y="{sy + 20}" font-family="ui-monospace,Menlo,monospace" '
        f'font-size="12.5" font-weight="700" fill="#{pal["fg_bright"]}">NOR</text>',
        f'<text x="58" y="{sy + 20}" font-family="ui-monospace,Menlo,monospace" '
        f'font-size="12" fill="#{pal["fg_dim"]}">main.rs</text>',
    ]
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    for variant in VARIANTS:
        pal = load(variant)
        (ASSETS / f"{variant}-palette.svg").write_text(swatch_svg(variant, pal))
        (ASSETS / f"{variant}.svg").write_text(code_svg(variant, pal))
        print(f"wrote assets/{variant}.svg and assets/{variant}-palette.svg")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Port the Vitesse theme family from VS Code to Helix.

Reads the upstream theme JSON (vendored under `upstream/`) and writes one Helix
theme per variant into the repo root. Keeping this generated means all five
variants stay consistent with each other and with upstream.

Key adaptation: Helix's theme loader reads only the first six digits of an
`#rrggbbaa` color and IGNORES the alpha channel, while Vitesse leans on
translucency everywhere. Every color here is therefore explicitly alpha-blended
onto the variant's own background *except* the base foreground, where blending
would wash out all code. See `NOTES` below.
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / "upstream"

VARIANTS = [
    # (upstream json, helix filename, background override or None)
    ("vitesse-black.json", "vitesse-black.toml", None),
    ("vitesse-dark.json", "vitesse-dark.toml", None),
    ("vitesse-dark-soft.json", "vitesse-dark-soft.toml", None),
    ("vitesse-light.json", "vitesse-light.toml", None),
    ("vitesse-light-soft.json", "vitesse-light-soft.toml", None),
]

# What each Helix scope maps to, and which upstream token scope it comes from.
# `None` means "take it from `colors`, not `tokenColors`".
TOKENS = {
    "attribute": "entity.other.attribute-name",
    "type": "support.type.primitive,entity.name.type",
    "type.builtin": "support.type.primitive,entity.name.type",
    "constructor": "entity",
    "constant": "constant",
    "constant.builtin": "support.constant",
    "constant.builtin.boolean": "constant.language.boolean",
    "constant.character": "string",
    "constant.character.escape": "string.regexp constant.character.escape",
    "constant.numeric": "constant.numeric",
    "string": "string",
    "string.regexp": "source.regexp,string.regexp",
    "string.special": "constant.other.reference.link",
    "comment": "comment",
    "variable": "variable,identifier",
    "variable.builtin": "constant",
    "variable.other.member": "property",
    "label": "constant",
    "keyword": "keyword",
    "keyword.storage": "storage",
    "keyword.storage.type": "storage.type",
    "keyword.operator": "keyword.operator",
    "operator": "keyword.operator",
    "function": "entity.name.function",
    "function.method": "entity.name.function",
    "function.macro": "entity.name.function",
    "tag": "entity.name.tag,tag.html",
    "namespace": "namespace",
    "special": "keyword",
    "punctuation": "delimiter.bracket,delimiter",
    "punctuation.delimiter": "delimiter.bracket,delimiter",
    "punctuation.bracket": "delimiter.bracket,delimiter",
    # markup scopes take their color from elsewhere; see MARKUP below.

    "markup.raw": "markup.raw",
    "markup.link.url": "constant.other.reference.link",
}


def expand(hex_str: str) -> str:
    """`#abc`, `#aabbcc` and `#aabbccdd` all become 8-digit lowercase."""
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 6:
        h += "ff"
    return h.lower()


def blend(fg: str, bg: str) -> str:
    f, b = expand(fg), expand(bg)
    a = int(f[6:8], 16) / 255
    out = []
    for i in (0, 2, 4):
        c = round(int(f[i : i + 2], 16) * a + int(b[i : i + 2], 16) * (1 - a))
        out.append(f"{c:02x}")
    return "#" + "".join(out)


def opaque(hex_str: str) -> str:
    """First six digits, for colors used as-is (no compositing)."""
    h = expand(hex_str)
    return "#" + h[:6]


def luminance(hex_str: str) -> float:
    h = opaque(hex_str).lstrip("#")
    channels = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def build_token_index(data: dict) -> dict[str, str]:
    """Map a VS Code scope string to its foreground color."""
    index: dict[str, str] = {}
    for entry in data.get("tokenColors", []):
        scope = entry.get("scope")
        if isinstance(scope, list):
            scope = ",".join(scope)
        fg = entry.get("settings", {}).get("foreground")
        if not scope or not fg:
            continue
        for part in scope.split(","):
            index.setdefault(part.strip(), fg)
    return index


def port(json_name: str, out_name: str) -> tuple[str, list[str]]:
    data = json.loads((UPSTREAM / json_name).read_text())
    colors = data["colors"]
    tokens = build_token_index(data)

    raw_bg = colors.get("editor.background", "#000000")
    bg = opaque(raw_bg)
    is_light = luminance(bg) > 0.5

    def tok(scope_key: str) -> str:
        """Resolve a scope, or the first scope of a comma-separated chain."""
        for part in (p.strip() for p in scope_key.split(",")):
            if part in tokens:
                return opaque(tokens[part])
        return opaque(tokens.get("keyword", "#4d9375"))

    # Values that must stay readable: take the 6-digit source, not a blend.
    # Blending `#758575dd` onto the background dims dark-variant comments below
    # WCAG AA, while the source color already has enough contrast. The light
    # variants use an intentionally soft gray upstream, so it is kept verbatim
    # there too; that is the designer's choice, not a bug.
    fg = opaque(colors.get("editor.foreground", "#dbd7ca"))
    comment_color = opaque(tokens.get("comment", "#758575dd"))
    palette = {
        "bg": bg,
        # Popups sit above the editor; VSCode uses the widget/list surface.
        # Using editor.background here would make popups invisible on variants
        # whose background is already #000.
        "bg_popup": blend(
            colors.get("list.hoverBackground",
                       colors.get("editorWidget.background", "#121212")), bg),
        "bg_border": blend("#00000033" if is_light else "#ffffff1f", bg),
        "cursorline": blend(
            colors.get("editor.lineHighlightBackground", "#121212"), bg
        ),
        "selection": blend(colors.get("editor.selectionBackground", "#eeeeee18"), bg),
        # Must read as a raised surface above the editor background. VSCode's
        # list.activeSelectionBackground equals the editor bg in these themes,
        # so derive it from a translucent white/black instead.
        "selection_strong": blend(
            "#ffffff26" if luminance(bg) < 0.5 else "#00000020", bg
        ),
        "linenr": blend(colors.get("editorLineNumber.foreground", "#dedcd550"), bg),
        "linenr_active": opaque(
            colors.get("editorLineNumber.activeForeground", "#bfbaaa")
        ),
        "indent": blend(colors.get("editorIndentGuide.background", "#ffffff15"), bg),
        "whitespace": blend(
            colors.get("editorIndentGuide.background", "#ffffff15"), bg
        ),
        "fg": fg,
        "fg_bright": "#393a34" if is_light else "#ffffff",
        # Dim foreground for hints/inactive UI. statusBar.foreground is too
        # bright to read as "dim"; gutter/comment colors are the right weight.
        # Dim but still readable text (statusline/hints). Blending the line
        # number color yields something too dark for text, so start from a
        # 60% version of the foreground instead.
        "fg_dim": blend(fg + "99", bg),
        "delimiter": blend(tokens.get("delimiter.bracket,delimiter", "#444444"), bg),
        "comment": comment_color,
        "error": opaque(colors.get("editorError.foreground", "#cb7676")),
        "warning": opaque(colors.get("editorWarning.foreground", "#d4976c")),
        "info": opaque(colors.get("editorInfo.foreground", "#6394bf")),
        "hint": opaque(colors.get("editorHint.foreground", "#4d9375")),
        "match_fg": opaque(
            colors.get("editor.findMatchBackground", "#e6cc77")[:7]
            if len(colors.get("editor.findMatchBackground", "#e6cc77")) >= 7
            else "#e6cc77"
        ),
        # Bracket-match surface: a visible tint of the match color rather than
        # upstream's near-invisible #4d937520 on a black background.
        "match_bg": blend("#e6cc7733" if luminance(bg) < 0.5 else "#1c6b4820", bg),
        "diff_plus": blend(
            colors.get("diffEditor.insertedTextBackground", "#4d937550"), bg
        ),
        "diff_minus": blend(
            colors.get("diffEditor.removedTextBackground", "#ab595950"), bg
        ),
    }
    # mode indicator backgrounds need readable black/white text
    mode_bg = {
        "normal": palette["hint"],
        "insert": palette["error"] if is_light else "#80a665",
        "select": palette["warning"],
    }
    # Pick whichever of black/white reads better on the mode background
    # instead of assuming a direction from the theme family.
    def best_fg(bg_hex: str) -> str:
        return "#000000" if contrast("#000000", bg_hex) >= contrast("#ffffff", bg_hex) else "#ffffff"

    mode_fg_by_scope = {
        "normal": best_fg(mode_bg["normal"]),
        "insert": best_fg(mode_bg["insert"]),
        "select": best_fg(mode_bg["select"]),
    }

    lines = [
        f"# Vitesse ({pathlib.Path(out_name).stem}) for Helix",
        "# Generated by scripts/port-themes.py from upstream/vitesse-*.json",
        f"# Upstream: https://github.com/antfu/vscode-theme-vitesse ({data.get('name', '')})",
        "#",
        "# Helix ignores the alpha channel of #rrggbbaa, so translucent colors are",
        "# alpha-blended onto this variant's background here. The base foreground",
        "# keeps its source value; blending it would wash out all code text.",
        "",
        '"ui.background" = { bg = "bg" }',
        '"ui.text" = { fg = "fg" }',
        '"ui.text.focus" = { fg = "fg_bright", modifiers = ["bold"] }',
        '"ui.text.inactive" = { fg = "fg_dim" }',
        '"ui.text.info" = { fg = "fg" }',
        '"ui.text.directory" = { fg = "c_keyword" }',
        '"ui.window" = { fg = "bg_border" }',
        '"ui.background.separator" = { fg = "bg_border" }',
        "",
        '"ui.cursor" = { fg = "bg", bg = "fg" }',
        '"ui.cursor.primary" = { fg = "bg", bg = "fg" }',
        '"ui.cursor.normal" = { fg = "bg", bg = "fg" }',
        '"ui.cursor.insert" = { fg = "bg", bg = "fg" }',
        '"ui.cursor.select" = { fg = "bg", bg = "fg" }',
        '"ui.cursor.match" = { fg = "match_fg", modifiers = ["bold"] }',
        '"ui.cursor.primary.match" = { fg = "match_fg", modifiers = ["bold"] }',
        "",
        '"ui.selection" = { bg = "selection" }',
        '"ui.selection.primary" = { bg = "selection_strong" }',
        "",
        '"ui.cursorline.primary" = { bg = "cursorline" }',
        '"ui.cursorline.secondary" = { bg = "cursorline" }',
        '"ui.cursorcolumn.primary" = { bg = "cursorline" }',
        '"ui.cursorcolumn.secondary" = { bg = "cursorline" }',
        "",
        '"ui.linenr" = { fg = "linenr" }',
        '"ui.linenr.selected" = { fg = "linenr_active" }',
        '"ui.gutter" = { bg = "bg" }',
        '"ui.gutter.selected" = { bg = "cursorline" }',
        "",
        '"ui.statusline" = { fg = "fg_dim", bg = "bg" }',
        f'"ui.statusline.normal" = {{ fg = "{mode_fg_by_scope["normal"]}", bg = "normal_bg", modifiers = ["bold"] }}',
        f'"ui.statusline.insert" = {{ fg = "{mode_fg_by_scope["insert"]}", bg = "insert_bg", modifiers = ["bold"] }}',
        f'"ui.statusline.select" = {{ fg = "{mode_fg_by_scope["select"]}", bg = "select_bg", modifiers = ["bold"] }}',
        '"ui.statusline.inactive" = { fg = "fg_dim", bg = "bg" }',
        '"ui.statusline.separator" = { fg = "bg_border" }',
        "",
        '"ui.bufferline" = { fg = "fg_dim", bg = "cursorline" }',
        '"ui.bufferline.active" = { fg = "fg_bright", bg = "bg" }',
        '"ui.bufferline.background" = { bg = "cursorline" }',
        "",
        '"ui.popup" = { bg = "bg_popup", fg = "fg" }',
        '"ui.popup.info" = { bg = "bg_popup", fg = "fg" }',
        '"ui.menu" = { fg = "fg", bg = "bg_popup" }',
        '"ui.menu.border" = { fg = "bg_border" }',
        '"ui.menu.selected" = { fg = "fg_bright", bg = "selection_strong" }',
        '"ui.menu.scroll" = { fg = "bg_border", bg = "bg_popup" }',
        '"ui.picker" = { fg = "fg", bg = "bg_popup" }',
        '"ui.picker.header" = { fg = "fg_dim" }',
        '"ui.picker.header.column" = { fg = "fg_dim" }',
        '"ui.picker.header.column.active" = { fg = "c_keyword", modifiers = ["bold"] }',
        '"ui.help" = { fg = "fg", bg = "bg_popup" }',
        '"ui.info" = { fg = "fg", bg = "bg_popup" }',
        "",
        '"ui.virtual.whitespace" = { fg = "whitespace" }',
        '"ui.virtual.indent-guide" = { fg = "indent" }',
        '"ui.virtual.ruler" = { bg = "cursorline" }',
        '"ui.virtual.inlay-hint" = { fg = "fg_dim", bg = "bg" }',
        '"ui.virtual.jump-label" = { fg = "match_fg", modifiers = ["bold"] }',
        '"ui.virtual.wrap" = { fg = "fg_dim" }',
        "",
        '"ui.debug" = { fg = "error" }',
        '"ui.debug.active" = { fg = "warning" }',
        '"ui.debug.breakpoint" = { fg = "error" }',
        '"ui.highlight" = { bg = "selection_strong" }',
        '"ui.highlight.frameline" = { bg = "selection_strong" }',
        '"ui.match_paren" = { bg = "match_bg", fg = "match_fg" }',
        "",
        "# diagnostics",
        '"error" = { fg = "error", modifiers = ["underlined"] }',
        '"warning" = { fg = "warning" }',
        '"info" = { fg = "info" }',
        '"hint" = { fg = "hint" }',
        '"diagnostic.error" = { underline = { color = "error", style = "curl" } }',
        '"diagnostic.warning" = { underline = { color = "warning", style = "curl" } }',
        '"diagnostic.info" = { underline = { color = "info", style = "curl" } }',
        '"diagnostic.hint" = { underline = { color = "hint", style = "curl" } }',
        '"diagnostic.unnecessary" = { modifiers = ["dim"] }',
        '"diagnostic.deprecated" = { modifiers = ["crossed_out"] }',
        "",
        "# syntax",
    ]

    # Syntax scopes: each gets its own palette entry so the file stays readable.
    syntax_entries = []
    for helix_scope, upstream_scope in TOKENS.items():
        color = tok(upstream_scope)
        key = "c_" + helix_scope.replace(".", "_")
        palette[key] = color
        modifiers = {"comment": '["italic"]', "markup.heading": '["bold"]'}.get(helix_scope)
        if modifiers:
            syntax_entries.append(
                f'"{helix_scope}" = {{ fg = "{key}", modifiers = {modifiers} }}'
            )
        else:
            syntax_entries.append(f'"{helix_scope}" = {{ fg = "{key}" }}')

    # Nested scopes inherit from their parent in practice; spell out the ones
    # whose upstream token differs so they do not silently fall back.
    extra = [
        ("comment.line", "comment", True),
        ("comment.block", "comment", True),
        ("comment.line.documentation", "comment", True),
        ("comment.block.documentation", "comment", True),
        ("variable.parameter", "variable.parameter.function", False),
        ("variable.other", "variable,identifier", False),
        ("variable.other.member.private", "property", False),
        ("keyword.control", "keyword", False),
        ("keyword.control.conditional", "keyword", False),
        ("keyword.control.repeat", "keyword", False),
        ("keyword.control.import", "keyword", False),
        ("keyword.control.return", "keyword", False),
        ("keyword.control.exception", "keyword", False),
        ("keyword.directive", "keyword", False),
        ("keyword.function", "keyword", False),
        ("keyword.storage.modifier", "keyword", False),
        ("constant.numeric.integer", "constant.numeric", False),
        ("constant.numeric.float", "constant.numeric", False),
        ("function.builtin", "entity.name.function", False),
        ("function.special", "entity.name.function", False),
        ("function.method.private", "entity.name.function", False),
        ("type.enum.variant", "entity.other.attribute-name", False),
        ("tag.builtin", "entity.name.tag,tag.html", False),
        ("string.special.path", "constant.other.reference.link", False),
        ("string.special.url", "markup.underline.link.markdown", False),
        ("string.special.symbol", "constant", False),
        ("string.special.key", "property", False),
        ("punctuation.special", "delimiter.bracket,delimiter", False),
        ("markup.list.numbered", "delimiter.bracket,delimiter", False),
        ("markup.list.unnumbered", "delimiter.bracket,delimiter", False),
        ("markup.raw.block", "markup.raw", False),
        ("markup.link.label", "entity.other.attribute-name", False),
        ("markup.link.text", "constant.other.reference.link", False),
        ("markup.link", "constant.other.reference.link", False),
        ("markup.raw.inline", "markup.raw", False),
    ]
    for helix_scope, upstream_scope, italic in extra:
        color = tok(upstream_scope)
        key = "c_" + helix_scope.replace(".", "_")
        palette[key] = color
        if italic:
            lines.append(f'"{helix_scope}" = {{ fg = "{key}", modifiers = ["italic"] }}')
        else:
            lines.append(f'"{helix_scope}" = {{ fg = "{key}" }}')

    lines.append('"comment.unused" = { fg = "comment", modifiers = ["italic"] }')
    palette["c_markup_heading"] = tok("markup.heading")
    palette["c_markup_quote"] = tok("markup.quote")
    palette["c_markup_raw"] = tok("markup.raw")
    palette["c_markup_link_url"] = tok("markup.underline.link.markdown")
    if luminance(palette["c_markup_link_url"]) > 0.6 and luminance(bg) < 0.5:
        # upstream's link color is near-white on dark; prefer the string accent
        palette["c_markup_link_url"] = tok("constant.other.reference.link")
    palette["c_markup_link"] = tok("constant.other.reference.link")
    palette["c_string_special_url"] = palette["c_markup_link_url"]
    palette["c_markup_link_inline"] = tok("constant.other.reference.link")
    lines.append('"markup.heading" = { fg = "c_markup_heading", modifiers = ["bold"] }')
    lines.append('"markup.quote" = { fg = "c_markup_quote", modifiers = ["italic"] }')
    lines.append('"markup.bold" = { fg = "c_markup_bold", modifiers = ["bold"] }')
    lines.append('"markup.italic" = { fg = "c_markup_italic", modifiers = ["italic"] }')
    palette["c_markup_bold"] = palette["fg"]
    palette["c_markup_italic"] = palette["fg"]
    for level in (1, 2, 3, 4):
        lines.append(
            f'"markup.heading.{level}" = {{ fg = "c_markup_heading", modifiers = ["bold"] }}')

    lines += syntax_entries
    lines += [
        "",
        "# diff & misc",
        '"diff.plus" = { fg = "c_function" }',
        '"diff.minus" = { fg = "error" }',
        '"diff.delta" = { fg = "info" }',
        '"diff.plus.gutter" = { fg = "c_function" }',
        '"diff.minus.gutter" = { fg = "error" }',
        '"diff.delta.gutter" = { fg = "info" }',
        '"markup.heading.marker" = { fg = "c_markup_heading", modifiers = ["bold"] }',
        '"markup.list" = { fg = "c_punctuation" }',
        '"markup.list.checked" = { fg = "c_function" }',
        '"markup.list.unchecked" = { fg = "c_punctuation" }',
        '"markup.strikethrough" = { modifiers = ["crossed_out"] }',
        "",
        "[palette]",
        f'bg = "{palette["bg"]}"',
        f'bg_popup = "{palette["bg_popup"]}"',
        f'bg_border = "{palette["bg_border"]}"',
        f'cursorline = "{palette["cursorline"]}"',
        f'selection = "{palette["selection"]}"',
        f'selection_strong = "{palette["selection_strong"]}"',
        f'match_bg = "{palette["match_bg"]}"',
        f'linenr = "{palette["linenr"]}"',
        f'linenr_active = "{palette["linenr_active"]}"',
        f'indent = "{palette["indent"]}"',
        f'whitespace = "{palette["whitespace"]}"',
        f'normal_bg = "{mode_bg["normal"]}"',
        f'insert_bg = "{mode_bg["insert"]}"',
        f'select_bg = "{mode_bg["select"]}"',
        f'fg = "{palette["fg"]}"',
        f'fg_bright = "{palette["fg_bright"]}"',
        f'fg_dim = "{palette["fg_dim"]}"',
        f'delimiter = "{palette["delimiter"]}"',
        f'comment = "{palette["comment"]}"',
        "",
    ]
    seen = set()
    for line in lines:
        pass
    # emit remaining syntax palette entries
    header_keys = {
        "bg",
        "bg_popup",
        "bg_border",
        "cursorline",
        "selection",
        "selection_strong",
        "match_bg",
        "linenr",
        "linenr_active",
        "indent",
        "whitespace",
        "normal_bg",
        "insert_bg",
        "select_bg",
        "fg",
        "fg_bright",
        "fg_dim",
        "delimiter",
        "comment",
    }
    for key in sorted(palette):
        if key in header_keys:
            continue
        # avoid duplicating diagnostics keys
        pass

    # diagnostics colors are referenced by name but not yet in palette
    extra_pal = {
        "error": palette["error"],
        "warning": palette["warning"],
        "info": palette["info"],
        "hint": palette["hint"],
    }
    for k, v in extra_pal.items():
        lines.append(f'{k} = "{v}"')
    for key in sorted(palette):
        if key in header_keys or key in extra_pal:
            continue
        lines.append(f'{key} = "{palette[key]}"')

    text = "\n".join(lines) + "\n"

    # report contrast for the primary text color
    report = [
        f"  {out_name}: bg={bg} fg={fg} contrast={contrast(fg, bg)}:1",
        f"    comment={palette['comment']} ({contrast(palette['comment'], bg)}:1)",
    ]
    return text, report


def main() -> None:
    all_reports = []
    for json_name, out_name, _ in VARIANTS:
        text, report = port(json_name, out_name)
        (ROOT / out_name).write_text(text)
        all_reports += report
    print("\n".join(all_reports))


if __name__ == "__main__":
    main()

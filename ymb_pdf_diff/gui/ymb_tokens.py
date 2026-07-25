# -*- coding: utf-8 -*-
"""YMB共通デザイントークン(Qt/Python向け)。

このファイルは ymb-ui の tools/gen_python_tokens.py が
tokens/ymb-base.css から生成している。直接編集しないこと。
編集すると次の配布で上書きされ、他のYMBアプリとの整合も崩れる。

QSSはCSS変数を解釈しないため、値を文字列として持つ。
"""

# テーマで変わらない値(アクセント・書体・角丸・余白など)
COMMON = {
    "accent":              '#c3002f',
    "accent_fg":           '#ffffff',
    "accent_hover":        '#e0103f',
    "font":                '"Segoe UI", "Yu Gothic UI", "Meiryo", sans-serif',
    "font_mono":           '"Cascadia Mono", "Consolas", monospace',
    "fs_base":             '13px',
    "fs_h1":               '18px',
    "fs_label":            '12px',
    "fs_small":            '11px',
    "radius_md":           '6px',
    "radius_sm":           '4px',
    "space_lg":            '12px',
    "space_md":            '8px',
    "space_sm":            '6px',
    "space_xl":            '20px',
    "space_xs":            '4px',
    "toolbar_bg":          '#1f2430',
    "toolbar_btn_bg":      '#353c4d',
    "toolbar_btn_bg_hover": '#424a5e',
    "toolbar_fg":          '#eeeeee',
    "toolbar_input_bg":    '#2a3040',
    "toolbar_input_border": '#3a4156',
    "toolbar_label":       '#aab2c5',
    "toolbar_status":      '#ffd166',
}

# 明るいテーマの面・文字・意味色
LIGHT = {
    "accent_tint":         '#fde8ec',
    "bg":                  '#f5f6f8',
    "border":              '#dddddd',
    "border_soft":         '#eeeeee',
    "danger":              '#c0392b',
    "diff_add_bg":         '#d9f4dd',
    "diff_add_fg":         '#14532b',
    "diff_del_bg":         '#fbdada',
    "diff_del_fg":         '#7f1414',
    "fg":                  '#222222',
    "fg_dim":              '#555555',
    "fg_muted":            '#777777',
    "good":                '#1d7a32',
    "link":                '#0b5ed7',
    "row_hover":           '#f8f8f8',
    "surface":             '#ffffff',
    "surface_alt":         '#f7f7f7',
    "warning":             '#a06800',
}

# 暗いテーマの面・文字・意味色
DARK = {
    "accent_tint":         '#3a1e24',
    "bg":                  '#1e1e1e',
    "border":              '#3a3a40',
    "border_soft":         '#2a2a2e',
    "danger":              '#ff6b6b',
    "diff_add_bg":         '#1c4029',
    "diff_add_fg":         '#8fe3a6',
    "diff_del_bg":         '#4a1f22',
    "diff_del_fg":         '#f0a3a8',
    "fg":                  '#eaeaea',
    "fg_dim":              '#9a9aa4',
    "fg_muted":            '#888888',
    "good":                '#4caf50',
    "link":                '#4fc1ff',
    "row_hover":           '#33333a',
    "surface":             '#2d2d30',
    "surface_alt":         '#252528',
    "warning":             '#e0a800',
}


def palette(dark_mode=False):
    """テーマ非依存の値と、指定テーマの色をまとめた辞書を返す。"""
    merged = dict(COMMON)
    merged.update(DARK if dark_mode else LIGHT)
    return merged

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按颜色分组合并 COLR v1 层并导出 SVG（emoji_layer_00.svg ...）
同时输出 metadata JSON（fields: emoji_char, emoji_code, layers[]; each layer entry包含 merged layer indices, glyph names, color, hex, svg_file）
依赖: fonttools, svgwrite
"""
import os, sys, json, math
from collections import OrderedDict
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
import svgwrite

# ========== 配置 ==========
FONT_PATH = r"Z:\2025\emoji140\font\NotoColorEmoji-Regular.ttf"
EMOJI_CHAR = "👹"
OUTPUT_DIR = r"Z:\2025\emoji140\emoji_layers"
PALETTE_INDEX = 0
SVG_SIZE = 256
PAD_DIGITS = 2   # 文件编号位数，改为 3 当层数超过 100 用 03d

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== 加载字体 ==========
font = TTFont(FONT_PATH)
cmap = font.getBestCmap()
glyph_set = font.getGlyphSet()

if "COLR" not in font or "CPAL" not in font:
    raise SystemExit("字体缺少 COLR 或 CPAL 表")

colr_tbl = font["COLR"].table
cpal = font["CPAL"]
try:
    palette = cpal.palettes[PALETTE_INDEX]
except Exception:
    palette = cpal.palettes[0]

# ========== 工具函数 ==========
def find_glyph_for_sequence(cmap_table, emoji_str):
    if not emoji_str:
        return None
    try:
        g = cmap_table.get(ord(emoji_str[0]))
        if g:
            return g
    except Exception:
        pass
    for ch in emoji_str:
        try:
            g = cmap_table.get(ord(ch))
            if g:
                return g
        except Exception:
            pass
    return None

def bgra_to_rgba_tuple(bgra):
    if isinstance(bgra, (list, tuple)):
        if len(bgra) >= 4:
            b,g,r,a = bgra[:4]
        elif len(bgra) == 3:
            b,g,r = bgra[:3]; a = 255
        else:
            raise ValueError("未知 palette 颜色结构")
        return (int(r), int(g), int(b), int(a))
    try:
        seq = list(bgra)
        if len(seq) >= 4:
            b,g,r,a = seq[:4]; return (int(r), int(g), int(b), int(a))
    except Exception:
        pass
    raise ValueError("无法解析 palette 条目")

def rgba_to_hex(rgba):
    r,g,b,a = rgba
    return "#{:02x}{:02x}{:02x}".format(r,g,b)

def find_color_index_in_paint(paint):
    if paint is None:
        return None
    for fld in ("ColorIndex","colorID","PaletteIndex","paletteIndex","colorIndex","PaletteIdx"):
        if hasattr(paint, fld):
            try:
                v = getattr(paint, fld)
                if v is None:
                    continue
                return int(v)
            except Exception:
                pass
    for child_attr in ("Paints","children","Components","Layers","LayerArray","PaintList","Paint"):
        if hasattr(paint, child_attr):
            try:
                cont = getattr(paint, child_attr)
                if isinstance(cont, (list, tuple)):
                    for c in cont:
                        ci = find_color_index_in_paint(c)
                        if ci is not None:
                            return ci
                else:
                    ci = find_color_index_in_paint(cont)
                    if ci is not None:
                        return ci
            except Exception:
                pass
    return None

def extract_glyphs_from_paint(paint, out_glyphs):
    if paint is None:
        return
    for fld in ("GlyphName","Glyph","GlyphID","BaseGlyph","BaseGlyphID","glyphName","glyph","glyphID"):
        if hasattr(paint, fld):
            val = getattr(paint, fld)
            if isinstance(val, str):
                out_glyphs.append(val); return
            else:
                try:
                    gid = int(val)
                    go = font.getGlyphOrder()
                    if 0 <= gid < len(go):
                        out_glyphs.append(go[gid]); return
                except Exception:
                    pass
    for child_attr in ("Paints","children","Components","Layers","LayerArray","PaintList","Paint"):
        if hasattr(paint, child_attr):
            try:
                cont = getattr(paint, child_attr)
                if isinstance(cont, (list, tuple)):
                    for c in cont:
                        extract_glyphs_from_paint(c, out_glyphs)
                else:
                    extract_glyphs_from_paint(cont, out_glyphs)
            except Exception:
                pass

# ========== 定位 BaseGlyphPaintRecord ==========
bgl = getattr(colr_tbl, "BaseGlyphList", None)
if not bgl:
    raise SystemExit("BaseGlyphList 未找到")

records = None
for name in ("BaseGlyphPaintRecord","BaseGlyphPaint","BaseGlyphRecords","BaseGlyphPaintRecords","BaseGlyphRecordArray","BaseGlyphRecord"):
    if hasattr(bgl, name):
        records = getattr(bgl, name); break
if records is None and hasattr(bgl, "__iter__"):
    try:
        records = list(bgl)
    except Exception:
        records = None
if not records:
    raise SystemExit("无法读取 BaseGlyph paint records")

glyph_name = find_glyph_for_sequence(cmap, EMOJI_CHAR)
if not glyph_name:
    raise SystemExit(f"找不到 glyph for emoji: {EMOJI_CHAR}")

matched = None
for rec in (records if isinstance(records, (list,tuple)) else list(records)):
    base = getattr(rec, "BaseGlyph", None) or getattr(rec, "BaseGlyphID", None) or getattr(rec, "baseGlyph", None)
    if base == glyph_name:
        matched = rec; break
    try:
        if isinstance(base, int):
            go = font.getGlyphOrder()
            if 0 <= base < len(go) and go[base] == glyph_name:
                matched = rec; break
    except Exception:
        pass
if not matched:
    raise SystemExit("未匹配到目标 BaseGlyph 记录")

paint_field = getattr(matched, "Paint", None) or getattr(matched, "BasePaint", None) or getattr(matched, "paint", None)
first = getattr(matched, "FirstLayerIndex", None) or (getattr(paint_field, "FirstLayerIndex", None) if paint_field is not None else None)
num = getattr(matched, "NumLayers", None) or (getattr(paint_field, "NumLayers", None) if paint_field is not None else None)
if first is None or num is None:
    raise SystemExit("无法读取 FirstLayerIndex/NumLayers")
first = int(first); num = int(num)

# ========== 读取 layer_paints ==========
layer_list = getattr(colr_tbl, "LayerList", None)
if not layer_list:
    raise SystemExit("LayerList 未找到")

layer_paint_array = None
for fname in ("Paint","LayerRecordArray","LayerRecords","LayerRecordArray"):
    if hasattr(layer_list, fname):
        layer_paint_array = getattr(layer_list, fname); break
if layer_paint_array is None and hasattr(colr_tbl, "LayerRecordArray"):
    layer_paint_array = getattr(colr_tbl, "LayerRecordArray")
if layer_paint_array is None:
    raise SystemExit("无法找到 LayerRecordArray")

try:
    layer_paints = list(layer_paint_array)
except Exception:
    try:
        layer_paints = list(layer_list.Paint)
    except Exception:
        raise SystemExit("无法将 layer_paint_array 转为 list")

total_layers = len(layer_paints)
start = max(0, min(first, total_layers))
end = min(total_layers, start + max(0, min(num, total_layers - start)))

# ========== 按颜色分组收集 path ==========
# color_key => { "rgba":..., "hex":..., "subpaths": [ {layer_index_global, layer_index_local, glyph, path} ] }
groups = OrderedDict()
original_layers = []
diagnostics = []

for local_idx, global_idx in enumerate(range(start, end)):
    paint = layer_paints[global_idx]
    glyphs = []
    extract_glyphs_from_paint(paint, glyphs)
    color_idx = find_color_index_in_paint(paint)
    if color_idx is None and paint_field is not None:
        color_idx = find_color_index_in_paint(paint_field)
    if color_idx is None:
        chosen = None
        for i, entry in enumerate(palette):
            try:
                r,g,b,a = bgra_to_rgba_tuple(entry)
                if a > 0:
                    chosen = i; break
            except Exception:
                continue
        color_idx = chosen if chosen is not None else 0
    try:
        rgba = bgra_to_rgba_tuple(palette[color_idx])
        hex_color = rgba_to_hex(rgba)
    except Exception:
        rgba = (0,0,0,255); hex_color = rgba_to_hex(rgba)
        diagnostics.append({"layer_index_global": global_idx, "error": "palette_lookup_failed"})

    if not glyphs:
        diagnostics.append({"layer_index_global": global_idx, "paint_repr": repr(paint)[:400], "color_idx": int(color_idx), "hex": hex_color})
        # create placeholder entry in original_layers and continue
        original_layers.append({
            "layer_index_global": global_idx,
            "layer_index_local": local_idx,
            "glyph_name": None,
            "color": {"r": int(rgba[0]), "g": int(rgba[1]), "b": int(rgba[2])},
            "hex": hex_color,
        })
        continue

    for gi, lname in enumerate(glyphs):
        try:
            pen = SVGPathPen(glyph_set)
            glyph_set[lname].draw(pen)
            path_data = pen.getCommands()
        except Exception as e:
            diagnostics.append({"layer_index_global": global_idx, "glyph": lname, "error": "extract_path_failed", "exc": str(e)})
            continue

        # add to group for this hex
        if hex_color not in groups:
            groups[hex_color] = {"rgba": {"r": int(rgba[0]), "g": int(rgba[1]), "b": int(rgba[2]), "a": int(rgba[3])},
                                 "subpaths": []}
        groups[hex_color]["subpaths"].append({
            "layer_index_global": global_idx,
            "layer_index_local": local_idx,
            "glyph_name": lname,
            "path": path_data
        })

        original_layers.append({
            "layer_index_global": global_idx,
            "layer_index_local": local_idx,
            "glyph_name": lname,
            "color": {"r": int(rgba[0]), "g": int(rgba[1]), "b": int(rgba[2])},
            "hex": hex_color
        })

# ========== 导出每个颜色为单个 SVG（命名 emoji_layer_00.svg ...） ==========
exported_layers = []
for idx, (hex_color, info) in enumerate(groups.items()):
    safe_name = f"emoji_layer_{idx:0{PAD_DIGITS}d}.svg"
    out_path = os.path.join(OUTPUT_DIR, safe_name)
    dwg = svgwrite.Drawing(out_path, size=(SVG_SIZE, SVG_SIZE))
    for sp in info["subpaths"]:
        dwg.add(dwg.path(d=sp["path"], style=f"fill:{hex_color};stroke:none", transform=f"scale(1,-1) translate(0,-{SVG_SIZE})"))
    dwg.save()
    exported_layers.append({
        "layer_index": idx,
        "merged_layer_indices": [int(sp["layer_index_global"]) for sp in info["subpaths"]],
        "glyph_names": [sp["glyph_name"] for sp in info["subpaths"]],
        "color": {"r": int(info["rgba"]["r"]), "g": int(info["rgba"]["g"]), "b": int(info["rgba"]["b"])},
        "hex": hex_color,
        "svg_file": safe_name
    })
    print(f"[INFO] 导出颜色组 {hex_color} -> {safe_name} ({len(info['subpaths'])} subpaths)")

# ========== 写 metadata JSON（符合你示例格式） ==========
out = {
    "emoji_char": EMOJI_CHAR,
    "emoji_code": f"U+{ord(EMOJI_CHAR[0]):04X}",
    "layers": exported_layers,
    "original_layers": original_layers,
    "diagnostics": diagnostics
}
with open(os.path.join(OUTPUT_DIR, "emoji_layers_metadata.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print("Done. 导出位于:", OUTPUT_DIR)

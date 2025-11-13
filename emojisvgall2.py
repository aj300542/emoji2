#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COLR v1 彩色 emoji 批量导出为按颜色分组的 SVG + metadata
依赖: fonttools, svgwrite
保存结构:
  OUTPUT_ROOT/
    U+XXXX/            <- per-emoji dir (UNICODE_FORMAT)
      emoji_layer_00.svg
      emoji_layer_01.svg
      emoji_layers_metadata.json
"""
import os
import sys
import json
import math
import hashlib
import re
from collections import OrderedDict

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
import svgwrite

# ========== 批量配置（修改为你的路径/参数） ==========
FONT_PATH = r"Z:\2025\emoji140\font\NotoColorEmoji-Regular.ttf"
OUTPUT_ROOT = r"Z:\2025\emoji140\emoji_export"  # 批量根目录：每个 emoji 对应 UNICODE_FORMAT 子目录
PALETTE_INDEX = 0
SVG_SIZE = 256
PAD_DIGITS = 2          # SVG 编号位数（02d）
MIN_PATH_LENGTH = 0.5   # 过滤短路径阈值（像素）
UNICODE_FORMAT = "U+{:04X}"  # 子目录命名格式

# ========== 初始化 ==========
os.makedirs(OUTPUT_ROOT, exist_ok=True)

# ========== 加载字体 ==========
try:
    font = TTFont(FONT_PATH)
except Exception as e:
    raise SystemExit(f"加载字体失败：{e}")

if "COLR" not in font or "CPAL" not in font:
    raise SystemExit("字体缺少 COLR 或 CPAL 表，无法生成彩色图层")

colr_tbl = font["COLR"].table
cpal = font["CPAL"]
try:
    palette = cpal.palettes[PALETTE_INDEX]
except Exception:
    palette = cpal.palettes[0]
    print(f"警告：未找到索引 {PALETTE_INDEX} 的调色板，使用默认调色板")

cmap = font.getBestCmap()
glyph_set = font.getGlyphSet()

# ========== 工具函数 ==========
def find_glyph_for_sequence(cmap_table, emoji_str):
    """尽量返回 emoji_str 中第一个可映射的 glyph 名称"""
    if not emoji_str:
        return None
    for ch in emoji_str:
        try:
            g = cmap_table.get(ord(ch))
            if g:
                return g
        except Exception:
            pass
    try:
        return cmap_table.get(ord(emoji_str[0]))
    except Exception:
        return None

def bgra_to_rgba_tuple(bgra):
    """BGRA 转 RGBA 元组 (r,g,b,a)"""
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
    """RGBA 转 #rrggbb（忽略 alpha）"""
    r,g,b,a = rgba
    return "#{:02x}{:02x}{:02x}".format(r,g,b)

def find_color_index_in_paint(paint):
    """从 Paint 结构递归提取颜色索引（多字段兼容）"""
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
    for child_attr in ("Paints","children","Components","Layers","LayerArray","PaintList","Paint","Fill"):
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
    """从 Paint 结构递归提取 glyph 名称或 glyph id"""
    if paint is None:
        return
    for fld in ("GlyphName","Glyph","GlyphID","BaseGlyph","BaseGlyphID","glyphName","glyph","glyphID"):
        if hasattr(paint, fld):
            val = getattr(paint, fld)
            if isinstance(val, str):
                out_glyphs.append(val)
                return
            else:
                try:
                    gid = int(val)
                    go = font.getGlyphOrder()
                    if 0 <= gid < len(go):
                        out_glyphs.append(go[gid])
                        return
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

def ensure_path_closed(path_data):
    """确保路径闭合（添加 Z 指令）"""
    if not path_data or path_data.strip() == "":
        return ""
    last_cmd = path_data.strip()[-1].upper()
    if last_cmd != "Z":
        return f"{path_data.strip()} Z"
    return path_data

def is_valid_path(path_data):
    """过滤无效路径（空路径或仅含 M/Z）"""
    if not path_data or path_data.strip() == "":
        return False
    valid_cmds = {"L", "C", "Q", "S", "T", "A", "Z"}
    cmd_chars = [c.upper() for c in path_data if c.isalpha()]
    return any(cmd in valid_cmds for cmd in cmd_chars)

def remove_duplicate_paths(subpaths):
    """同色组内去重，基于 path 数据哈希（标准化）"""
    seen_hashes = set()
    unique_subpaths = []
    for sp in subpaths:
        path_data = sp.get("path", "")
        path_data_norm = re.sub(r"\s+", "", path_data).upper()
        path_hash = hashlib.md5(path_data_norm.encode("utf-8")).hexdigest()
        if path_hash not in seen_hashes:
            seen_hashes.add(path_hash)
            unique_subpaths.append(sp)
    return unique_subpaths

# ========== 变换矩阵支持 ==========
def matrix_multiply(a, b):
    return [
        [
            a[0][0]*b[0][0] + a[0][1]*b[1][0] + a[0][2]*b[2][0],
            a[0][0]*b[0][1] + a[0][1]*b[1][1] + a[0][2]*b[2][1],
            a[0][0]*b[0][2] + a[0][1]*b[1][2] + a[0][2]*b[2][2],
        ],
        [
            a[1][0]*b[0][0] + a[1][1]*b[1][0] + a[1][2]*b[2][0],
            a[1][0]*b[0][1] + a[1][1]*b[1][1] + a[1][2]*b[2][1],
            a[1][0]*b[0][2] + a[1][1]*b[1][2] + a[1][2]*b[2][2],
        ],
        [0,0,1]
    ]

def transform_translate(tx, ty):
    return [[1,0,tx],[0,1,ty],[0,0,1]]

def transform_scale(sx, sy):
    return [[sx,0,0],[0,sy,0],[0,0,1]]

def transform_rotate(rad):
    c = math.cos(rad); s = math.sin(rad)
    return [[c,-s,0],[s,c,0],[0,0,1]]

def transform_affine(a,b,c,d,e,f):
    return [[a,c,e],[b,d,f],[0,0,1]]

def extract_transform_from_paint(paint):
    """从 paint 节点递归提取 3x3 变换矩阵（支持多种命名）"""
    M = [[1,0,0],[0,1,0],[0,0,1]]
    if paint is None:
        return M
    local_M = [[1,0,0],[0,1,0],[0,0,1]]
    t = getattr(paint, "Transform", None) or getattr(paint, "transform", None)
    if t is not None:
        xx = getattr(t, "xx", None)
        if xx is not None:
            xx = float(xx); xy = float(getattr(t, "xy", 0)); yx = float(getattr(t, "yx", 0)); yy = float(getattr(t, "yy", 1))
            dx = float(getattr(t, "dx", 0)); dy = float(getattr(t, "dy", 0))
            local_M = [[xx, xy, dx],[yx, yy, dy],[0,0,1]]
        else:
            a = getattr(t, "a", None)
            if a is not None:
                a = float(a); b = float(getattr(t, "b", 0)); c = float(getattr(t, "c", 0))
                d = float(getattr(t, "d", 1)); e = float(getattr(t, "e", 0)); f = float(getattr(t, "f", 0))
                local_M = transform_affine(a,b,c,d,e,f)
    if hasattr(paint, "Translate") or hasattr(paint, "translate"):
        tr = getattr(paint, "Translate", None) or getattr(paint, "translate", None)
        if hasattr(tr, "dx") or hasattr(tr, "dy"):
            tx = float(getattr(tr, "dx", getattr(tr, "x", 0)))
            ty = float(getattr(tr, "dy", getattr(tr, "y", 0)))
            local_M = matrix_multiply(local_M, transform_translate(tx, ty))
    if hasattr(paint, "Scale") or hasattr(paint, "scale"):
        sc = getattr(paint, "Scale", None) or getattr(paint, "scale", None)
        sx = float(getattr(sc, "sx", getattr(sc, "x", getattr(sc, "sx", 1))))
        sy = float(getattr(sc, "sy", getattr(sc, "y", getattr(sc, "sy", sx))))
        local_M = matrix_multiply(local_M, transform_scale(sx, sy))
    if hasattr(paint, "Rotate") or hasattr(paint, "rotate"):
        ro = getattr(paint, "Rotate", None) or getattr(paint, "rotate", None)
        angle = getattr(ro, "angle", None)
        if angle is None:
            angle = getattr(ro, "deg", None) or getattr(ro, "degrees", None) or getattr(ro, "radians", None)
        if angle is not None:
            try:
                angle = float(angle)
                if abs(angle) > 2*math.pi:
                    rad = math.radians(angle)
                else:
                    rad = float(angle)
                local_M = matrix_multiply(local_M, transform_rotate(rad))
            except Exception:
                pass
    if hasattr(paint, "Affine") or hasattr(paint, "affine"):
        af = getattr(paint, "Affine", None) or getattr(paint, "affine", None)
        a = float(getattr(af, "a", 1)); b = float(getattr(af, "b", 0))
        c = float(getattr(af, "c", 0)); d = float(getattr(af, "d", 1))
        e = float(getattr(af, "e", 0)); f = float(getattr(af, "f", 0))
        local_M = matrix_multiply(local_M, transform_affine(a,b,c,d,e,f))
    child_matrices = []
    for child_attr in ("Paints","children","Components","Layers","LayerArray","PaintList","Paint"):
        if hasattr(paint, child_attr):
            try:
                cont = getattr(paint, child_attr)
                if isinstance(cont, (list, tuple)):
                    for c in cont:
                        cm = extract_transform_from_paint(c)
                        if cm != [[1,0,0],[0,1,0],[0,0,1]]:
                            child_matrices.append(cm)
                else:
                    cm = extract_transform_from_paint(cont)
                    if cm != [[1,0,0],[0,1,0],[0,0,1]]:
                        child_matrices.append(cm)
            except Exception:
                pass
    result = local_M
    for cm in child_matrices:
        result = matrix_multiply(result, cm)
    return result

def get_transformed_path(glyph_set, glyph_name, matrix):
    """使用 TransformPen 将 3x3 矩阵应用到 glyph 并输出 SVG path 数据"""
    xx = matrix[0][0]; xy = matrix[0][1]; dx = matrix[0][2]
    yx = matrix[1][0]; yy = matrix[1][1]; dy = matrix[1][2]
    pen = SVGPathPen(glyph_set)
    tpen = TransformPen(pen, (xx, yx, xy, yy, dx, dy))
    try:
        glyph_set[glyph_name].draw(tpen)
    except Exception:
        pen = SVGPathPen(glyph_set)
        glyph_set[glyph_name].draw(pen)
    path = pen.getCommands()
    return ensure_path_closed(path)

# ========== 定位 BaseGlyphPaintRecord 和 LayerList ==========
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
    layer_paints_global = list(layer_paint_array)
except Exception:
    try:
        layer_paints_global = list(layer_list.Paint)
    except Exception:
        raise SystemExit("无法将 layer_paint_array 转为 list")

# ========== 自动构建 EMOJI_LIST（从 COLR BaseGlyphList 中提取） ==========
def build_emoji_list_from_colr(records, cmap_table):
    """返回一个按记录顺序的 emoji 字符列表（尽量取每个 BaseGlyph 的第一个映射码点）"""
    emoji_chars = []
    glyph_to_cps = {}
    for cp, gname in cmap_table.items():
        glyph_to_cps.setdefault(gname, []).append(cp)

    recs = list(records) if not isinstance(records, (list, tuple)) else records
    for rec in recs:
        base = getattr(rec, "BaseGlyph", None) or getattr(rec, "BaseGlyphID", None) or getattr(rec, "baseGlyph", None)
        glyph_name = None
        if isinstance(base, str):
            glyph_name = base
        else:
            try:
                gid = int(base)
                go = font.getGlyphOrder()
                if 0 <= gid < len(go):
                    glyph_name = go[gid]
            except Exception:
                glyph_name = None

        if not glyph_name:
            continue

        cps = glyph_to_cps.get(glyph_name)
        if cps:
            cps_sorted = sorted(cps)
            chosen_cp = cps_sorted[0]
            try:
                emoji_chars.append(chr(chosen_cp))
            except Exception:
                continue
        else:
            continue

    seen = set()
    unique = []
    for ch in emoji_chars:
        if ch not in seen:
            seen.add(ch)
            unique.append(ch)
    return unique

EMOJI_LIST = build_emoji_list_from_colr(records, cmap)
print(f"[INFO] 从 COLR 记录生成 EMOJI_LIST，包含 {len(EMOJI_LIST)} 个条目")
with open(os.path.join(OUTPUT_ROOT, "emoji_list_from_colr.txt"), "w", encoding="utf-8") as ef:
    for ch in EMOJI_LIST:
        ef.write(ch + "\n")

# ========== 批量处理函数 ==========
processed_count = 0
success_count = 0
global_diagnostics = []

def process_one_emoji(emoji_char):
    out_diag = []
    exported_layers = []
    original_layers = []
    try:
        glyph_name = find_glyph_for_sequence(cmap, emoji_char)
        if not glyph_name:
            out_diag.append({"error": "glyph_not_found", "emoji": emoji_char})
            return {"success": False, "diagnostics": out_diag}

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
            out_diag.append({"error": "baseglyph_record_not_matched", "emoji": emoji_char})
            return {"success": False, "diagnostics": out_diag}

        paint_field = getattr(matched, "Paint", None) or getattr(matched, "BasePaint", None) or getattr(matched, "paint", None)
        first = getattr(matched, "FirstLayerIndex", None) or (getattr(paint_field, "FirstLayerIndex", None) if paint_field is not None else None)
        num = getattr(matched, "NumLayers", None) or (getattr(paint_field, "NumLayers", None) if paint_field is not None else None)
        if first is None or num is None:
            out_diag.append({"error": "layer_index_missing", "emoji": emoji_char})
            return {"success": False, "diagnostics": out_diag}
        first = int(first); num = int(num)

        total_layers = len(layer_paints_global)
        start = max(0, min(first, total_layers))
        end = min(total_layers, start + max(0, min(num, total_layers - start)))

        groups = OrderedDict()

        for local_idx, global_idx in enumerate(range(start, end)):
            paint = layer_paints_global[global_idx]
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
            except Exception as e:
                rgba = (0,0,0,255); hex_color = rgba_to_hex(rgba)
                out_diag.append({"layer_index_global": global_idx, "error": "palette_lookup_failed", "exc": str(e)})

            if not glyphs:
                out_diag.append({"layer_index_global": global_idx, "paint_repr": repr(paint)[:400], "color_idx": int(color_idx), "hex": hex_color})
                original_layers.append({
                    "layer_index_global": global_idx,
                    "layer_index_local": local_idx,
                    "glyph_name": None,
                    "color": {"r": int(rgba[0]), "g": int(rgba[1]), "b": int(rgba[2])},
                    "hex": hex_color,
                })
                continue

            matrix = extract_transform_from_paint(paint)

            for gi, lname in enumerate(glyphs):
                try:
                    path_data = get_transformed_path(glyph_set, lname, matrix)
                    path_data = ensure_path_closed(path_data)
                    if not is_valid_path(path_data):
                        out_diag.append({"layer_index_global": global_idx, "glyph": lname, "error": "invalid_path_skipped"})
                        continue
                except Exception as e:
                    out_diag.append({"layer_index_global": global_idx, "glyph": lname, "error": "extract_path_failed", "exc": str(e)})
                    continue

                if hex_color not in groups:
                    groups[hex_color] = {"rgba": {"r": int(rgba[0]), "g": int(rgba[1]), "b": int(rgba[2]), "a": int(rgba[3])},
                                         "subpaths": []}
                groups[hex_color]["subpaths"].append({
                    "layer_index_global": global_idx,
                    "layer_index_local": local_idx,
                    "glyph_name": lname,
                    "path": path_data,
                    "matrix": matrix
                })

                original_layers.append({
                    "layer_index_global": global_idx,
                    "layer_index_local": local_idx,
                    "glyph_name": lname,
                    "color": {"r": int(rgba[0]), "g": int(rgba[1]), "b": int(rgba[2])},
                    "hex": hex_color,
                    "matrix": matrix
                })

        # 输出目录（按 emoji codepoints 组成名称）
        codepoints = ["{:04X}".format(ord(ch)) for ch in emoji_char]
        subdir_name = "-".join([UNICODE_FORMAT.format(int(cp,16)) for cp in codepoints])
        out_dir = os.path.join(OUTPUT_ROOT, subdir_name)
        os.makedirs(out_dir, exist_ok=True)

        exported_layers = []
        for idx, (hex_color, info) in enumerate(groups.items()):
            unique_subpaths = remove_duplicate_paths(info["subpaths"])
            if not unique_subpaths:
                out_diag.append({"export_layer_index": idx, "hex_color": hex_color, "error": "no_valid_subpaths_skipped"})
                continue
            safe_name = f"emoji_layer_{idx:0{PAD_DIGITS}d}.svg"
            out_path = os.path.join(out_dir, safe_name)
            dwg = svgwrite.Drawing(out_path, size=(SVG_SIZE, SVG_SIZE))
            for sp in unique_subpaths:
                dwg.add(dwg.path(d=sp["path"], fill=hex_color, stroke="none",
                                 transform=f"scale(1,-1) translate(0,-{SVG_SIZE})"))
            dwg.save()
            exported_layers.append({
                "layer_index": idx,
                "merged_layer_indices": [int(sp["layer_index_global"]) for sp in unique_subpaths],
                "glyph_names": [sp["glyph_name"] for sp in unique_subpaths],
                "color": {"r": int(info["rgba"]["r"]), "g": int(info["rgba"]["g"]), "b": int(info["rgba"]["b"])},
                "hex": hex_color,
                "svg_file": safe_name,
                "paths_count": len(unique_subpaths)
            })

        meta = {
            "emoji_char": emoji_char,
            "emoji_codepoints": ["U+{:04X}".format(ord(ch)) for ch in emoji_char],
            "layers": exported_layers,
            "original_layers": original_layers,
            "diagnostics": out_diag
        }
        meta_path = os.path.join(out_dir, "emoji_layers_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(meta, mf, indent=2, ensure_ascii=False)
        return {"success": True, "diagnostics": out_diag, "exported": len(exported_layers), "out_dir": out_dir}
    except Exception as e:
        return {"success": False, "diagnostics": [{"exception": str(e)}]}

# ========== 批量循环 ==========
for emoji in EMOJI_LIST:
    processed_count += 1
    print(f"[{processed_count}] 处理 emoji: {emoji!r}")
    res = process_one_emoji(emoji)
    if res.get("success"):
        success_count += 1
        print(f"  -> 成功: 导出 {res.get('exported',0)} 图层 到 {res.get('out_dir')}")
    else:
        print(f"  -> 失败: {res.get('diagnostics')}")
    global_diagnostics.append({"emoji": emoji, "result": res})

# 全局汇总
summary = {
    "processed": processed_count,
    "succeeded": success_count,
    "failed": processed_count - success_count,
    "details": global_diagnostics
}
summary_path = os.path.join(OUTPUT_ROOT, "batch_summary.json")
with open(summary_path, "w", encoding="utf-8") as sf:
    json.dump(summary, sf, indent=2, ensure_ascii=False)

print("\nBatch done.")
print(f"Processed: {processed_count}, Succeeded: {success_count}, Failed: {processed_count - success_count}")
print("Summary saved to", summary_path)

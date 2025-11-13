#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 COLR v1 导出按颜色/渐变分组的 SVG 并产出 metadata JSON（包含 gradient 描述）
依赖: fonttools, svgwrite
修改顶部配置后运行
"""
import os
import json
import math
import hashlib
import re
from collections import OrderedDict

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
import svgwrite

# ========== 配置 ==========
FONT_PATH = r"Z:\2025\emoji140\font\NotoColorEmoji-Regular.ttf"
EMOJI_CHAR = "👹"      # 支持单字符或序列（取首有效码点对应 glyph）
OUTPUT_DIR = r"Z:\2025\emoji140\emoji_layers"
PALETTE_INDEX = 0
SVG_SIZE = 256
PAD_DIGITS = 2
MIN_PATH_LENGTH = 0.5

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== 加载字体 ==========
try:
    font = TTFont(FONT_PATH)
except Exception as e:
    raise SystemExit(f"加载字体失败: {e}")

if "COLR" not in font or "CPAL" not in font:
    raise SystemExit("字体缺少 COLR 或 CPAL 表")

colr_tbl = font["COLR"].table
cpal = font["CPAL"]
try:
    palette = cpal.palettes[PALETTE_INDEX]
except Exception:
    palette = cpal.palettes[0]
    print(f"[WARN] 使用默认调色板 (index fallback)")

cmap = font.getBestCmap()
glyph_set = font.getGlyphSet()

# ========== 基础工具 ==========
def find_glyph_for_sequence(cmap_table, emoji_str):
    if not emoji_str:
        return None
    for ch in emoji_str:
        g = cmap_table.get(ord(ch))
        if g:
            return g
    return cmap_table.get(ord(emoji_str[0])) if emoji_str else None

def bgra_to_rgba_tuple(bgra):
    if isinstance(bgra, (list, tuple)):
        if len(bgra) >= 4:
            b,g,r,a = bgra[:4]
        elif len(bgra) == 3:
            b,g,r = bgra[:3]; a = 255
        else:
            raise ValueError("未知 palette 颜色结构")
        return (int(r), int(g), int(b), int(a))
    seq = list(bgra)
    if len(seq) >= 4:
        b,g,r,a = seq[:4]; return (int(r), int(g), int(b), int(a))
    raise ValueError("无法解析 palette 条目")

def rgba_to_hex(rgba):
    r,g,b,a = rgba
    return "#{:02x}{:02x}{:02x}".format(r,g,b)

def remove_duplicate_paths(subpaths):
    seen = set()
    unique = []
    for sp in subpaths:
        p = sp.get("path","")
        norm = re.sub(r"\s+","",p).upper()
        h = hashlib.md5(norm.encode("utf-8")).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(sp)
    return unique

def ensure_path_closed(path):
    if not path:
        return ""
    if path.strip()[-1].upper() != "Z":
        return path.strip() + " Z"
    return path

def is_valid_path(path):
    if not path or path.strip()=="":
        return False
    return any(c in path for c in "lLcCqQsStTaAzZ")

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
    M = [[1,0,0],[0,1,0],[0,0,1]]
    if paint is None:
        return M
    local = [[1,0,0],[0,1,0],[0,0,1]]
    t = getattr(paint, "Transform", None) or getattr(paint, "transform", None)
    if t is not None:
        xx = getattr(t, "xx", None)
        if xx is not None:
            try:
                xx = float(xx); xy = float(getattr(t,"xy",0)); yx = float(getattr(t,"yx",0)); yy = float(getattr(t,"yy",1))
                dx = float(getattr(t,"dx",0)); dy = float(getattr(t,"dy",0))
                local = [[xx, xy, dx],[yx, yy, dy],[0,0,1]]
            except Exception:
                pass
        else:
            a = getattr(t,"a",None)
            if a is not None:
                try:
                    a = float(a); b = float(getattr(t,"b",0)); c = float(getattr(t,"c",0))
                    d = float(getattr(t,"d",1)); e = float(getattr(t,"e",0)); f = float(getattr(t,"f",0))
                    local = transform_affine(a,b,c,d,e,f)
                except Exception:
                    pass
    tr = getattr(paint,"Translate", None) or getattr(paint,"translate", None)
    if tr is not None:
        try:
            tx = float(getattr(tr,"dx", getattr(tr,"x",0)))
            ty = float(getattr(tr,"dy", getattr(tr,"y",0)))
            local = matrix_multiply(local, transform_translate(tx, ty))
        except Exception:
            pass
    sc = getattr(paint,"Scale", None) or getattr(paint,"scale", None)
    if sc is not None:
        try:
            sx = float(getattr(sc,"sx", getattr(sc,"x",1)))
            sy = float(getattr(sc,"sy", getattr(sc,"y",sx)))
            local = matrix_multiply(local, transform_scale(sx, sy))
        except Exception:
            pass
    ro = getattr(paint,"Rotate", None) or getattr(paint,"rotate", None)
    if ro is not None:
        angle = getattr(ro,"angle", None)
        if angle is None:
            angle = getattr(ro,"deg", None) or getattr(ro,"degrees", None) or getattr(ro,"radians", None)
        if angle is not None:
            try:
                angle = float(angle)
                if abs(angle) > 2*math.pi:
                    rad = math.radians(angle)
                else:
                    rad = float(angle)
                local = matrix_multiply(local, transform_rotate(rad))
            except Exception:
                pass
    af = getattr(paint,"Affine", None) or getattr(paint,"affine", None)
    if af is not None:
        try:
            a = float(getattr(af,"a",1)); b = float(getattr(af,"b",0))
            c = float(getattr(af,"c",0)); d = float(getattr(af,"d",1))
            e = float(getattr(af,"e",0)); f = float(getattr(af,"f",0))
            local = matrix_multiply(local, transform_affine(a,b,c,d,e,f))
        except Exception:
            pass
    child_mats = []
    for child_attr in ("Paints","children","Components","Layers","LayerArray","PaintList","Paint"):
        if hasattr(paint, child_attr):
            try:
                cont = getattr(paint, child_attr)
                if isinstance(cont, (list,tuple)):
                    for c in cont:
                        cm = extract_transform_from_paint(c)
                        if cm != [[1,0,0],[0,1,0],[0,0,1]]:
                            child_mats.append(cm)
                else:
                    cm = extract_transform_from_paint(cont)
                    if cm != [[1,0,0],[0,1,0],[0,0,1]]:
                        child_mats.append(cm)
            except Exception:
                pass
    res = local
    for cm in child_mats:
        res = matrix_multiply(res, cm)
    return res

def get_transformed_path(glyph_set, glyph_name, matrix):
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

# ========== 定位 COLR records 和 layer list ==========
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

layer_list = getattr(colr_tbl,"LayerList", None)
if not layer_list:
    raise SystemExit("LayerList 未找到")

layer_paint_array = None
for fname in ("Paint","LayerRecordArray","LayerRecords","LayerRecordArray"):
    if hasattr(layer_list, fname):
        layer_paint_array = getattr(layer_list, fname); break
if layer_paint_array is None and hasattr(colr_tbl,"LayerRecordArray"):
    layer_paint_array = getattr(colr_tbl,"LayerRecordArray")
if layer_paint_array is None:
    raise SystemExit("无法找到 LayerRecordArray")

try:
    layer_paints = list(layer_paint_array)
except Exception:
    try:
        layer_paints = list(layer_list.Paint)
    except Exception:
        raise SystemExit("无法将 layer_paint_array 转为 list")

# ========== 定位目标 glyph record ==========
glyph_name = find_glyph_for_sequence(cmap, EMOJI_CHAR)
if not glyph_name:
    raise SystemExit(f"找不到 glyph for emoji: {EMOJI_CHAR}")

matched = None
for rec in (records if isinstance(records,(list,tuple)) else list(records)):
    base = getattr(rec,"BaseGlyph", None) or getattr(rec,"BaseGlyphID", None) or getattr(rec,"baseGlyph", None)
    if base == glyph_name:
        matched = rec; break
    try:
        if isinstance(base,int):
            go = font.getGlyphOrder()
            if 0 <= base < len(go) and go[base] == glyph_name:
                matched = rec; break
    except Exception:
        pass
if not matched:
    raise SystemExit("未匹配到目标 BaseGlyph 记录")

paint_field = getattr(matched,"Paint", None) or getattr(matched,"BasePaint", None) or getattr(matched,"paint", None)
first = getattr(matched,"FirstLayerIndex", None) or (getattr(paint_field,"FirstLayerIndex", None) if paint_field is not None else None)
num = getattr(matched,"NumLayers", None) or (getattr(paint_field,"NumLayers", None) if paint_field is not None else None)
if first is None or num is None:
    raise SystemExit("无法读取 FirstLayerIndex/NumLayers")
first = int(first); num = int(num)
total_layers = len(layer_paints)
start = max(0, min(first, total_layers))
end = min(total_layers, start + max(0, min(num, total_layers - start)))

# ========== 渐变提取器（更宽容的命名/嵌套支持） ==========
def extract_gradient_from_paint(paint):
    if paint is None:
        return None
    # 可能承载渐变信息的候选字段名（尽量覆盖命名差异）
    cand_names = ("PaintLinearGradient","PaintRadialGradient","LinearGradient","RadialGradient",
                  "ColorLine","ColorLines","ColorStops","Stops","StopList","StopsList","Stop")
    candidates = []
    for n in cand_names:
        if hasattr(paint, n):
            try:
                candidates.append(getattr(paint, n))
            except Exception:
                pass
    # 如果 paint 本身是一个 stops 列表
    try:
        if isinstance(paint, (list,tuple)) and len(paint)>0 and not isinstance(paint[0], (str,bytes)):
            candidates.append(paint)
    except Exception:
        pass
    # 递归子节点查找
    if not candidates:
        for child in ("Paints","children","Components","Layers","LayerArray","PaintList","Paint","Fill"):
            if hasattr(paint, child):
                try:
                    cont = getattr(paint, child)
                    if isinstance(cont, (list,tuple)):
                        for c in cont:
                            g = extract_gradient_from_paint(c)
                            if g:
                                return g
                    else:
                        g = extract_gradient_from_paint(cont)
                        if g:
                            return g
                except Exception:
                    pass
        return None

    g = candidates[0]
    # 尝试获取 stops 源
    stops_src = None
    if hasattr(g, "ColorLine"):
        stops_src = getattr(g, "ColorLine")
    elif hasattr(g, "Stops"):
        stops_src = getattr(g, "Stops")
    elif isinstance(g, (list,tuple)):
        stops_src = g
    else:
        if hasattr(paint, "ColorLine"):
            stops_src = getattr(paint, "ColorLine")
        elif hasattr(paint, "Stops"):
            stops_src = getattr(paint, "Stops")

    stops = []
    if stops_src:
        try:
            seq = list(stops_src) if not isinstance(stops_src, (str,bytes)) else [stops_src]
            for s in seq:
                off = None
                for of in ("Offset","offset","StopOffset","stopOffset","Position","position"):
                    if hasattr(s, of):
                        try:
                            off = float(getattr(s, of))
                        except Exception:
                            off = None
                        break
                colval = None
                for cf in ("Color","color","PaletteIndex","colorIndex","ColorIndex"):
                    if hasattr(s, cf):
                        colval = getattr(s, cf)
                        break
                rgba = None
                if isinstance(colval, (list,tuple)):
                    try:
                        rgba = bgra_to_rgba_tuple(colval)
                    except Exception:
                        rgba = None
                else:
                    try:
                        if colval is not None:
                            ci = int(colval)
                            rgba = bgra_to_rgba_tuple(palette[ci])
                    except Exception:
                        rgba = None
                if rgba is None and hasattr(s, "Paint"):
                    ci = find_color_index_in_paint(getattr(s,"Paint"))
                    if ci is not None:
                        try:
                            rgba = bgra_to_rgba_tuple(palette[ci])
                        except Exception:
                            rgba = None
                if rgba is None:
                    continue
                stops.append({"offset": (off if off is not None else None), "rgba":[int(rgba[0]),int(rgba[1]),int(rgba[2]),int(rgba[3])]})
        except Exception:
            pass

    if not stops:
        return None

    # 归一化 offsets
    if any(s["offset"] is None for s in stops):
        n = len(stops)
        for i,s in enumerate(stops):
            if s["offset"] is None:
                s["offset"] = i/(n-1) if n>1 else 0.0

    coords = {}
    # linear coords
    for fset in (("x0","y0","x1","y1"),("X0","Y0","X1","Y1"),("x0","y0","x2","y2")):
        if all(hasattr(g,f) for f in fset):
            try:
                coords = {f: float(getattr(g,f)) for f in fset}
                break
            except Exception:
                pass
    # radial coords
    if not coords:
        for fset in (("cx","cy","r"),("centerX","centerY","radius"),("cx","cy","radius")):
            if all(hasattr(g,f) for f in fset):
                try:
                    coords = {f: float(getattr(g,f)) for f in fset}
                    break
                except Exception:
                    pass

    grad_type = "linear" if "x0" in coords else ("radial" if "cx" in coords or "r" in coords else "unknown")
    return {"type": grad_type, "coords": coords, "stops": stops, "transform": extract_transform_from_paint(paint)}

# ========== 主循环：收集 paths 并检测渐变 ==========
groups = OrderedDict()
original_layers = []
diagnostics = []
paint_dump = []

for local_idx, global_idx in enumerate(range(start, end)):
    paint = layer_paints[global_idx]
    # optional: record paint repr for diagnostics
    try:
        paint_dump.append({"global_index": global_idx, "repr": repr(paint)[:800]})
    except Exception:
        paint_dump.append({"global_index": global_idx, "repr": "<repr error>"})

    # extract glyph(s)
    glyphs = []
    # reuse earlier helper
    def extract_glyphs_from_obj(p, out):
        if p is None: return
        for fld in ("GlyphName","Glyph","GlyphID","BaseGlyph","BaseGlyphID","glyphName","glyph","glyphID"):
            if hasattr(p, fld):
                val = getattr(p, fld)
                if isinstance(val, str):
                    out.append(val); return
                else:
                    try:
                        gid = int(val); go = font.getGlyphOrder()
                        if 0 <= gid < len(go):
                            out.append(go[gid]); return
                    except Exception:
                        pass
        for child in ("Paints","children","Components","Layers","LayerArray","PaintList","Paint"):
            if hasattr(p, child):
                try:
                    cont = getattr(p, child)
                    if isinstance(cont, (list,tuple)):
                        for c in cont: extract_glyphs_from_obj(c, out)
                    else: extract_glyphs_from_obj(cont, out)
                except Exception:
                    pass
    extract_glyphs_from_obj(paint, glyphs)

    # color index fallback
    def find_color_index_in_p(p):
        if p is None: return None
        for fld in ("ColorIndex","colorID","PaletteIndex","paletteIndex","colorIndex","PaletteIdx"):
            if hasattr(p, fld):
                try:
                    v = getattr(p, fld)
                    if v is None: continue
                    return int(v)
                except Exception:
                    pass
        for child in ("Paints","children","Components","Layers","LayerArray","PaintList","Paint","Fill"):
            if hasattr(p, child):
                try:
                    cont = getattr(p, child)
                    if isinstance(cont, (list,tuple)):
                        for c in cont:
                            ci = find_color_index_in_p(c)
                            if ci is not None: return ci
                    else:
                        ci = find_color_index_in_p(cont)
                        if ci is not None: return ci
                except Exception:
                    pass
        return None

    color_idx = find_color_index_in_p(paint)
    if color_idx is None and paint_field is not None:
        color_idx = find_color_index_in_p(paint_field)
    if color_idx is None:
        # fallback first visible palette entry
        chosen = None
        for i,entry in enumerate(palette):
            try:
                r,g,b,a = bgra_to_rgba_tuple(entry)
                if a>0: chosen = i; break
            except Exception:
                pass
        color_idx = chosen if chosen is not None else 0

    try:
        rgba = bgra_to_rgba_tuple(palette[color_idx])
    except Exception:
        rgba = (0,0,0,255)
    hex_color = rgba_to_hex(rgba)

    if not glyphs:
        diagnostics.append({"global": global_idx, "note":"no glyph extracted", "hex": hex_color})
        original_layers.append({
            "layer_index_global": global_idx,
            "layer_index_local": local_idx,
            "glyph_name": None,
            "color": {"r": rgba[0], "g": rgba[1], "b": rgba[2]},
            "hex": hex_color,
            "matrix": extract_transform_from_paint(paint),
            "gradient": None
        })
        continue

    matrix = extract_transform_from_paint(paint)
    grad = extract_gradient_from_paint(paint)  # None or dict

    for gi, lname in enumerate(glyphs):
        try:
            path_data = get_transformed_path(glyph_set, lname, matrix)
            path_data = ensure_path_closed(path_data)
            if not is_valid_path(path_data):
                diagnostics.append({"global": global_idx, "glyph": lname, "err":"invalid_path"})
                continue
        except Exception as e:
            diagnostics.append({"global": global_idx, "glyph": lname, "err": str(e)})
            continue

        # grouping key: gradient hash when present else hex_color
        if grad:
            gkey = "GRADIENT_" + hashlib.md5(json.dumps(grad, sort_keys=True).encode("utf-8")).hexdigest()[:12]
            if gkey not in groups:
                groups[gkey] = {"gradient": grad, "rgba": {"r": rgba[0], "g": rgba[1], "b": rgba[2], "a": rgba[3]}, "subpaths": []}
            groups[gkey]["subpaths"].append({"layer_index_global": global_idx, "layer_index_local": local_idx, "glyph_name": lname, "path": path_data, "matrix": matrix})
            group_info = groups[gkey]
        else:
            if hex_color not in groups:
                groups[hex_color] = {"gradient": None, "rgba": {"r": rgba[0], "g": rgba[1], "b": rgba[2], "a": rgba[3]}, "subpaths": []}
            groups[hex_color]["subpaths"].append({"layer_index_global": global_idx, "layer_index_local": local_idx, "glyph_name": lname, "path": path_data, "matrix": matrix})
            group_info = groups[hex_color]

        original_layers.append({
            "layer_index_global": global_idx,
            "layer_index_local": local_idx,
            "glyph_name": lname,
            "color": {"r": rgba[0], "g": rgba[1], "b": rgba[2]},
            "hex": hex_color,
            "matrix": matrix,
            "gradient": grad
        })

# 保存 paint dump for debugging
with open(os.path.join(OUTPUT_DIR, "paint_repr_dump.json"), "w", encoding="utf-8") as fd:
    json.dump(paint_dump, fd, indent=2, ensure_ascii=False)

# ========== 导出 SVG（支持 gradient defs） ==========
exported = []
for idx, (key, info) in enumerate(groups.items()):
    subs = remove_duplicate_paths(info["subpaths"])
    if not subs:
        diagnostics.append({"group": key, "err":"no_valid_subpaths"})
        continue

    svg_name = f"emoji_layer_{idx:0{PAD_DIGITS}d}.svg"
    svg_path = os.path.join(OUTPUT_DIR, svg_name)
    dwg = svgwrite.Drawing(svg_path, size=(SVG_SIZE, SVG_SIZE))
    defs = dwg.defs

    fill_ref = None
    gradient_meta = None

    if info.get("gradient"):
        grad = info["gradient"]
        gid = "g_" + hashlib.md5(json.dumps(grad, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        stops = grad.get("stops", [])
        # linear or fallback
        if grad["type"] in ("linear","unknown"):
            x0 = grad["coords"].get("x0", 0) if isinstance(grad.get("coords",{}), dict) else 0
            y0 = grad["coords"].get("y0", 0) if isinstance(grad.get("coords",{}), dict) else 0
            x1 = grad["coords"].get("x1", 1) if isinstance(grad.get("coords",{}), dict) else 1
            y1 = grad["coords"].get("y1", 0) if isinstance(grad.get("coords",{}), dict) else 0
            lg = dwg.linearGradient(id=gid, start=(x0, y0), end=(x1, y1))
            for s in stops:
                rgba = s["rgba"]
                color_hex = "#{:02x}{:02x}{:02x}".format(rgba[0], rgba[1], rgba[2])
                opacity = rgba[3]/255.0
                lg.add_stop_color(offset=str(s["offset"]), color=color_hex, opacity=opacity)
            defs.add(lg)
            fill_ref = f"url(#{gid})"
            gradient_meta = {"id": gid, "type":"linear", "coords": {"x0":x0,"y0":y0,"x1":x1,"y1":y1}, "stops": stops}
        elif grad["type"]=="radial":
            cx = grad["coords"].get("cx", 0.5)
            cy = grad["coords"].get("cy", 0.5)
            r = grad["coords"].get("r", 0.5)
            rg = dwg.radialGradient(id=gid, center=(cx, cy), r=r)
            for s in stops:
                rgba = s["rgba"]
                color_hex = "#{:02x}{:02x}{:02x}".format(rgba[0], rgba[1], rgba[2])
                opacity = rgba[3]/255.0
                rg.add_stop_color(offset=str(s["offset"]), color=color_hex, opacity=opacity)
            defs.add(rg)
            fill_ref = f"url(#{gid})"
            gradient_meta = {"id": gid, "type":"radial", "coords": {"cx":cx,"cy":cy,"r":r}, "stops": stops}
        else:
            # fallback to first stop color
            s0 = stops[0]
            fill_ref = "#{:02x}{:02x}{:02x}".format(s0["rgba"][0], s0["rgba"][1], s0["rgba"][2])
            gradient_meta = None
    else:
        rgba = (info["rgba"]["r"], info["rgba"]["g"], info["rgba"]["b"], info["rgba"]["a"])
        fill_ref = "#{:02x}{:02x}{:02x}".format(rgba[0], rgba[1], rgba[2])

    # add paths
    for sp in subs:
        dwg.add(dwg.path(d=sp["path"], fill=fill_ref, stroke="none", transform=f"scale(1,-1) translate(0,-{SVG_SIZE})"))
    dwg.save()

    exported.append({
        "layer_index": idx,
        "group_key": key,
        "merged_layer_indices": [int(sp["layer_index_global"]) for sp in subs],
        "glyph_names": [sp["glyph_name"] for sp in subs],
        "color": {"r": int(info["rgba"]["r"]), "g": int(info["rgba"]["g"]), "b": int(info["rgba"]["b"])},
        "hex": "#{:02x}{:02x}{:02x}".format(int(info["rgba"]["r"]), int(info["rgba"]["g"]), int(info["rgba"]["b"])),
        "svg_file": svg_name,
        "paths_count": len(subs),
        "gradient": gradient_meta
    })
    print(f"[INFO] exported {svg_name} (paths {len(subs)}, gradient={'yes' if gradient_meta else 'no'})")

# ========== 写 metadata ==========
out = {
    "emoji_char": EMOJI_CHAR,
    "emoji_code": f"U+{ord(EMOJI_CHAR[0]):04X}" if EMOJI_CHAR else None,
    "layers": exported,
    "original_layers": original_layers,
    "diagnostics": diagnostics
}
meta_file = os.path.join(OUTPUT_DIR, "emoji_layers_metadata.json")
with open(meta_file, "w", encoding="utf-8") as mf:
    json.dump(out, mf, indent=2, ensure_ascii=False)

print("Done. SVGs and metadata written to:", OUTPUT_DIR)

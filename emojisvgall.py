#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理所有emoji（按颜色分组逻辑）
每个emoji生成独立U+XXXX目录（存于emoji_export），保留原JSON格式和SVG颜色分组规则
依赖: fonttools, svgwrite
"""
import os, sys, json, math, hashlib
from collections import OrderedDict
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
import svgwrite

# ========== 批量配置（根据需求修改） ==========
FONT_PATH = r"Z:\2025\emoji140\font\NotoColorEmoji-Regular.ttf"
OUTPUT_ROOT = r"Z:\2025\emoji140\emoji_export"  # 批量根目录：每个emoji对应U+XXXX子目录
PALETTE_INDEX = 0
SVG_SIZE = 256
PAD_DIGITS = 2  # SVG编号位数（02d）
MIN_PATH_LENGTH = 0.5  # 过滤短路径阈值
UNICODE_FORMAT = "U+{:04X}"  # 子目录命名格式

# ========== 全局初始化 ==========
os.makedirs(OUTPUT_ROOT, exist_ok=True)
processed_count = 0  # 总处理emoji数
success_count = 0    # 成功处理数
global_diagnostics = []  # 全局错误记录

# ========== 核心工具函数（完全保留原逻辑） ==========
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

def extract_glyphs_from_paint(paint, out_glyphs, glyph_order):
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
                    if 0 <= gid < len(glyph_order):
                        out_glyphs.append(glyph_order[gid]); return
                except Exception:
                    pass
    for child_attr in ("Paints","children","Components","Layers","LayerArray","PaintList","Paint"):
        if hasattr(paint, child_attr):
            try:
                cont = getattr(paint, child_attr)
                if isinstance(cont, (list, tuple)):
                    for c in cont:
                        extract_glyphs_from_paint(c, out_glyphs, glyph_order)
                else:
                    extract_glyphs_from_paint(cont, out_glyphs, glyph_order)
            except Exception:
                pass

# ========== 路径优化工具函数（完全保留原逻辑） ==========
def ensure_path_closed(path_data):
    if not path_data or path_data.strip() == "":
        return ""
    last_cmd = path_data.strip()[-1].upper()
    if last_cmd != "Z":
        return f"{path_data.strip()} Z"
    return path_data

def is_valid_path(path_data):
    if not path_data or path_data.strip() == "":
        return False
    valid_cmds = {"L", "C", "Q", "S", "T", "A", "Z"}
    cmd_chars = [c.upper() for c in path_data if c.isalpha()]
    return any(cmd in valid_cmds for cmd in cmd_chars)

def remove_duplicate_paths(subpaths):
    seen_hashes = set()
    unique_subpaths = []
    for sp in subpaths:
        path_data = sp["path"].replace(" ", "").upper()
        path_hash = hashlib.md5(path_data.encode()).hexdigest()
        if path_hash not in seen_hashes:
            seen_hashes.add(path_hash)
            unique_subpaths.append(sp)
    return unique_subpaths

# ========== 单个emoji处理函数（基于原逻辑，适配批量目录） ==========
def process_single_emoji(font, cmap, glyph_set, glyph_order, palette, emoji_char):
    """处理单个emoji：按颜色分组生成SVG+JSON，保存到U+XXXX目录"""
    global processed_count, success_count
    processed_count += 1
    emoji_code = ord(emoji_char)
    emoji_dir_name = UNICODE_FORMAT.format(emoji_code)
    emoji_output_dir = os.path.join(OUTPUT_ROOT, emoji_dir_name)
    os.makedirs(emoji_output_dir, exist_ok=True)  # 创建当前emoji的专属目录
    local_diagnostics = []

    try:
        # 1. 定位当前emoji的glyph（原逻辑）
        glyph_name = find_glyph_for_sequence(cmap, emoji_char)
        if not glyph_name:
            msg = "未找到对应glyph"
            local_diagnostics.append({"error": "no_glyph", "msg": msg})
            return False, msg

        # 2. 定位BaseGlyphPaintRecord（原逻辑）
        colr_tbl = font["COLR"].table
        bgl = getattr(colr_tbl, "BaseGlyphList", None)
        if not bgl:
            msg = "COLR表无BaseGlyphList"
            local_diagnostics.append({"error": "no_base_glyph_list", "msg": msg})
            return False, msg

        # 查找目标glyph的图层记录
        records = None
        for name in ("BaseGlyphPaintRecord","BaseGlyphPaint","BaseGlyphRecords","BaseGlyphPaintRecords","BaseGlyphRecordArray","BaseGlyphRecord"):
            if hasattr(bgl, name):
                records = getattr(bgl, name); break
        if records is None and hasattr(bgl, "__iter__"):
            records = list(bgl)
        if not records:
            msg = "无法读取BaseGlyph记录"
            local_diagnostics.append({"error": "no_base_records", "msg": msg})
            return False, msg

        matched = None
        for rec in (records if isinstance(records, (list,tuple)) else list(records)):
            base = getattr(rec, "BaseGlyph", None) or getattr(rec, "BaseGlyphID", None) or getattr(rec, "baseGlyph", None)
            if base == glyph_name:
                matched = rec; break
            try:
                if isinstance(base, int) and 0 <= base < len(glyph_order) and glyph_order[base] == glyph_name:
                    matched = rec; break
            except Exception:
                pass
        if not matched:
            msg = "无对应COLR图层记录（非彩色emoji）"
            local_diagnostics.append({"error": "no_colr_record", "msg": msg})
            return False, msg

        # 3. 提取图层范围（原逻辑）
        paint_field = getattr(matched, "Paint", None) or getattr(matched, "BasePaint", None) or getattr(matched, "paint", None)
        first = getattr(matched, "FirstLayerIndex", None) or (getattr(paint_field, "FirstLayerIndex", None) if paint_field else None)
        num = getattr(matched, "NumLayers", None) or (getattr(paint_field, "NumLayers", None) if paint_field else None)
        if first is None or num is None:
            msg = "无法读取图层范围"
            local_diagnostics.append({"error": "no_layer_range", "msg": msg})
            return False, msg
        first = int(first); num = int(num)

        # 4. 读取layer_paints（原逻辑）
        layer_list = getattr(colr_tbl, "LayerList", None)
        if not layer_list:
            msg = "COLR表无LayerList"
            local_diagnostics.append({"error": "no_layer_list", "msg": msg})
            return False, msg

        layer_paint_array = None
        for fname in ("Paint","LayerRecordArray","LayerRecords","LayerRecordArray"):
            if hasattr(layer_list, fname):
                layer_paint_array = getattr(layer_list, fname); break
        if layer_paint_array is None and hasattr(colr_tbl, "LayerRecordArray"):
            layer_paint_array = getattr(colr_tbl, "LayerRecordArray")
        if layer_paint_array is None:
            msg = "无法找到LayerRecordArray"
            local_diagnostics.append({"error": "no_layer_paint_array", "msg": msg})
            return False, msg

        try:
            layer_paints = list(layer_paint_array)
        except Exception:
            try:
                layer_paints = list(layer_list.Paint)
            except Exception:
                msg = "无法转换layer_paint为列表"
                local_diagnostics.append({"error": "layer_paint_convert_fail", "msg": msg})
                return False, msg

        # 计算有效图层范围
        total_layers = len(layer_paints)
        start = max(0, min(first, total_layers))
        end = min(total_layers, start + max(0, min(num, total_layers - start)))
        if start >= end:
            msg = "无有效图层"
            local_diagnostics.append({"error": "no_valid_layers", "msg": msg})
            return False, msg

        # 5. 按颜色分组收集路径（原逻辑）
        groups = OrderedDict()
        original_layers = []
        for local_idx, global_idx in enumerate(range(start, end)):
            paint = layer_paints[global_idx]
            glyphs = []
            extract_glyphs_from_paint(paint, glyphs, glyph_order)  # 传入glyph_order
            color_idx = find_color_index_in_paint(paint)

            # 颜色索引fallback
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

            # 颜色转换
            try:
                rgba = bgra_to_rgba_tuple(palette[color_idx])
                hex_color = rgba_to_hex(rgba)
            except Exception as e:
                rgba = (0,0,0,255); hex_color = rgba_to_hex(rgba)
                local_diagnostics.append({"layer_global": global_idx, "error": "palette_lookup_failed", "exc": str(e)})

            # 处理无glyph情况
            if not glyphs:
                local_diagnostics.append({"layer_global": global_idx, "paint_repr": repr(paint)[:400], "color_idx": int(color_idx), "hex": hex_color})
                original_layers.append({
                    "layer_index_global": global_idx,
                    "layer_index_local": local_idx,
                    "glyph_name": None,
                    "color": {"r": int(rgba[0]), "g": int(rgba[1]), "b": int(rgba[2])},
                    "hex": hex_color,
                })
                continue

            # 收集并优化路径
            for gi, lname in enumerate(glyphs):
                try:
                    pen = SVGPathPen(glyph_set)
                    glyph_set[lname].draw(pen)
                    path_data = pen.getCommands()

                    # 路径优化流水线
                    path_data = ensure_path_closed(path_data)
                    if not is_valid_path(path_data):
                        local_diagnostics.append({"layer_global": global_idx, "glyph": lname, "error": "invalid_path_skipped"})
                        continue

                    # 加入颜色组
                    if hex_color not in groups:
                        groups[hex_color] = {
                            "rgba": {"r": int(rgba[0]), "g": int(rgba[1]), "b": int(rgba[2]), "a": int(rgba[3])},
                            "subpaths": []
                        }
                    groups[hex_color]["subpaths"].append({
                        "layer_index_global": global_idx,
                        "layer_index_local": local_idx,
                        "glyph_name": lname,
                        "path": path_data
                    })

                    # 记录原始图层
                    original_layers.append({
                        "layer_index_global": global_idx,
                        "layer_index_local": local_idx,
                        "glyph_name": lname,
                        "color": {"r": int(rgba[0]), "g": int(rgba[1]), "b": int(rgba[2])},
                        "hex": hex_color
                    })
                except Exception as e:
                    local_diagnostics.append({"layer_global": global_idx, "glyph": lname, "error": "extract_path_failed", "exc": str(e)})
                    continue

        # 6. 导出颜色组SVG和JSON（原逻辑，目录改为当前emoji的U+XXXX目录）
        if not groups:
            msg = "无有效颜色组"
            local_diagnostics.append({"error": "no_valid_color_groups", "msg": msg})
            return False, msg

        exported_layers = []
        for idx, (hex_color, info) in enumerate(groups.items()):
            unique_subpaths = remove_duplicate_paths(info["subpaths"])
            if not unique_subpaths:
                local_diagnostics.append({"export_layer": idx, "hex_color": hex_color, "error": "no_unique_subpaths"})
                continue

            # SVG保存到当前emoji的目录
            svg_filename = f"emoji_layer_{idx:0{PAD_DIGITS}d}.svg"
            svg_path = os.path.join(emoji_output_dir, svg_filename)
            dwg = svgwrite.Drawing(svg_path, size=(SVG_SIZE, SVG_SIZE))
            for sp in unique_subpaths:
                dwg.add(dwg.path(
                    d=sp["path"],
                    style=f"fill:{hex_color};stroke:none",
                    transform=f"scale(1,-1) translate(0,-{SVG_SIZE})"
                ))
            dwg.save()

            # 构建exported_layers（完全保留原格式）
            exported_layers.append({
                "layer_index": idx,
                "merged_layer_indices": [int(sp["layer_index_global"]) for sp in unique_subpaths],
                "glyph_names": [sp["glyph_name"] for sp in unique_subpaths],
                "color": {"r": int(info["rgba"]["r"]), "g": int(info["rgba"]["g"]), "b": int(info["rgba"]["b"])},
                "hex": hex_color,
                "svg_file": svg_filename
            })
            print(f"[INFO] {emoji_dir_name}：导出颜色组 {hex_color} -> {svg_filename}（{len(unique_subpaths)}个子路径）")

        # 生成JSON（保存到当前emoji的目录）
        out_json = {
            "emoji_char": emoji_char,
            "emoji_code": UNICODE_FORMAT.format(emoji_code),
            "layers": exported_layers,
            "original_layers": original_layers,
            "diagnostics": local_diagnostics
        }
        json_path = os.path.join(emoji_output_dir, "emoji_layers_metadata.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(out_json, f, indent=2, ensure_ascii=False)

        success_count += 1
        return True, f"成功（{len(exported_layers)}个颜色组图层）"

    except Exception as e:
        err_msg = f"意外错误：{str(e)[:50]}"
        local_diagnostics.append({"error": "unexpected_error", "exc": str(e)})
        # 保存错误JSON，便于排查
        err_json = {
            "emoji_char": emoji_char,
            "emoji_code": UNICODE_FORMAT.format(emoji_code),
            "error": err_msg,
            "diagnostics": local_diagnostics
        }
        err_json_path = os.path.join(emoji_output_dir, "error_metadata.json")
        with open(err_json_path, "w", encoding="utf-8") as f:
            json.dump(err_json, f, indent=2, ensure_ascii=False)
        global_diagnostics.append({"emoji_code": UNICODE_FORMAT.format(emoji_code), "error": err_msg})
        return False, err_msg

# ========== 批量处理主函数 ==========
def batch_process_all_emojis():
    try:
        # 1. 预加载字体资源（只加载一次，提升效率）
        print(f"[批量] 正在加载字体：{FONT_PATH}")
        font = TTFont(FONT_PATH)
        cmap = font.getBestCmap()
        glyph_set = font.getGlyphSet()
        glyph_order = font.getGlyphOrder()

        # 验证COLR/CPAL表（原逻辑）
        if "COLR" not in font or "CPAL" not in font:
            raise SystemExit("字体缺少COLR或CPAL表，无法处理彩色emoji")
        cpal = font["CPAL"]
        # 获取调色板
        try:
            palette = cpal.palettes[PALETTE_INDEX]
        except Exception:
            palette = cpal.palettes[0]
            print(f"[批量] 警告：未找到调色板{PALETTE_INDEX}，使用默认调色板")

        # 2. 筛选所有emoji的Unicode（覆盖常见emoji区间）
        print("[批量] 正在筛选字体中的emoji...")
        emoji_list = []
        for code in cmap.keys():
            # 筛选emoji Unicode范围（排除普通字符）
            if (0x00A9 <= code <= 0x00AE or  # 版权、注册商标
                0x203C <= code <= 0x2B5F or  # 符号类emoji
                0x1F000 <= code <= 0x1FFFF): # 主要emoji区间（含表情、符号、旗帜等）
                try:
                    emoji_char = chr(code)
                    emoji_list.append(emoji_char)
                except Exception:
                    continue
        total_emojis = len(emoji_list)
        print(f"[批量] 筛选完成：共{total_emojis}个候选emoji，开始批量处理\n")

        # 3. 循环处理每个emoji
        for idx, emoji_char in enumerate(emoji_list, 1):
            emoji_code = UNICODE_FORMAT.format(ord(emoji_char))
            progress = f"[{idx}/{total_emojis}]"
            success, msg = process_single_emoji(font, cmap, glyph_set, glyph_order, palette, emoji_char)
            print(f"{progress} {emoji_code}（{emoji_char}）：{msg}")

        # 4. 输出批量处理报告
        print("\n" + "-"*80)
        print("[批量处理完成]")
        print(f"总候选emoji数：{total_emojis}")
        print(f"实际处理数：{processed_count}")
        print(f"成功数：{success_count}")
        print(f"失败数：{processed_count - success_count}")
        print(f"批量根目录：{OUTPUT_ROOT}")
        print(f"全局错误数：{len(global_diagnostics)}")

        # 保存批量报告
        batch_report = {
            "total_candidate_emojis": total_emojis,
            "processed_count": processed_count,
            "success_count": success_count,
            "failed_count": processed_count - success_count,
            "output_root": OUTPUT_ROOT,
            "font_path": FONT_PATH,
            "global_diagnostics": global_diagnostics,
            "process_time": os.popen('date /t').read().strip() + " " + os.popen('time /t').read().strip()
        }
        report_path = os.path.join(OUTPUT_ROOT, "batch_process_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(batch_report, f, indent=2, ensure_ascii=False)
        print(f"批量报告已保存：{report_path}")

    except KeyboardInterrupt:
        print(f"\n[批量] 用户中断处理！已处理{processed_count}个，成功{success_count}个")
        # 中断时保存临时报告
        temp_report = {
            "interrupted": True,
            "processed_count": processed_count,
            "success_count": success_count,
            "global_diagnostics": global_diagnostics
        }
        temp_report_path = os.path.join(OUTPUT_ROOT, "batch_interrupted_report.json")
        with open(temp_report_path, "w", encoding="utf-8") as f:
            json.dump(temp_report, f, indent=2, ensure_ascii=False)
        print(f"临时报告已保存：{temp_report_path}")
    except Exception as e:
        print(f"[批量] 初始化失败：{str(e)}", file=sys.stderr)
        sys.exit(1)

# ========== 启动批量处理 ==========
if __name__ == "__main__":
    batch_process_all_emojis()
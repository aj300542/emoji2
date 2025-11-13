#!/usr/bin/env python3
import os
from pathlib import Path

# 配置：修改为你的目标目录
TARGET_DIR = r"Z:\2025\gif\new"
DRY_RUN = False  # True 仅打印预览，False 执行重命名
VERBOSE = True

def find_files_to_rename(root: Path):
    pattern = "U+*s.gif"
    for p in root.iterdir():
        if p.is_file() and p.match(pattern):
            yield p

def new_name_for(path: Path) -> Path:
    name = path.name
    # 只删除最后一个's'，且确保是紧接在扩展名前
    if name.lower().endswith("s.gif"):
        new_name = name[:-5] + ".gif"  # remove trailing 's' before '.gif'
        return path.with_name(new_name)
    return path

def main():
    root = Path(TARGET_DIR)
    if not root.exists() or not root.is_dir():
        print(f"目标目录不存在或不是文件夹: {root}")
        return

    to_rename = []
    for p in find_files_to_rename(root):
        target = new_name_for(p)
        if target == p:
            continue
        to_rename.append((p, target))

    if not to_rename:
        print("未发现需要重命名的文件。")
        return

    print(f"共发现 {len(to_rename)} 个候选文件：")
    for src, dst in to_rename:
        print(f"  {src.name}  ->  {dst.name}")

    if DRY_RUN:
        print("\nDRY RUN 模式，未实际执行重命名。将 DRY_RUN = False 后再运行以执行改名。")
        return

    # 实际执行重命名（检查冲突）
    for src, dst in to_rename:
        if dst.exists():
            print(f"跳过（目标已存在）: {src.name} -> {dst.name}")
            continue
        try:
            src.rename(dst)
            if VERBOSE:
                print(f"已重命名: {src.name} -> {dst.name}")
        except Exception as e:
            print(f"重命名失败: {src.name} -> {dst.name} ; 错误: {e}")

if __name__ == "__main__":
    main()

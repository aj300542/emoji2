import os
import glob
import time
from PIL import Image

# 根目录：修改为你的 PNG 输出目录
ROOT_DIR = r"Z:\2025\emoji140\emoji_export"
FRAME_PREFIX = "frame_"
FRAME_EXT = ".png"
GIF_DURATION = 200  # 每帧间隔（毫秒）
MIN_FRAMES = 10     # 最少帧数才生成 GIF

def find_frame_groups(root_dir):
    frame_groups = {}
    for root, dirs, files in os.walk(root_dir):
        frames = sorted(
            [f for f in files if f.startswith(FRAME_PREFIX) and f.endswith(FRAME_EXT)],
            key=lambda f: int(''.join(filter(str.isdigit, f)) or 0)
        )
        if len(frames) >= MIN_FRAMES:
            frame_groups[root] = frames
    return frame_groups

def infer_emojicode_from_path(path):
    parts = path.replace("\\", "/").split("/")
    for part in reversed(parts):
        if part.startswith("U+") and len(part) >= 5:
            return part
    return "emoji"

def convert_frames_to_gif(frame_dir, frame_files, output_name):
    images = []
    for fname in frame_files:
        fpath = os.path.join(frame_dir, fname)
        try:
            img = Image.open(fpath).convert("RGBA")  # 保留透明背景
            images.append(img)
        except Exception as e:
            print(f"⚠️ 无法读取图像: {fpath} ({e})")

    if not images:
        print(f"❌ 没有有效帧: {frame_dir}")
        return False

    gif_path = os.path.join(frame_dir, output_name + ".gif")
    try:
        images[0].save(
            gif_path,
            save_all=True,
            append_images=images[1:],
            duration=GIF_DURATION,
            loop=0,
            disposal=2  # 清除上一帧，避免残影
            # 不设置 transparency 参数，避免误判物体为透明
        )
        print(f"✅ 生成GIF: {gif_path}")
        return True
    except Exception as e:
        print(f"❌ GIF生成失败: {gif_path} ({e})")
        return False

def format_time(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m{secs}s"

def batch_convert():
    frame_groups = find_frame_groups(ROOT_DIR)
    total = len(frame_groups)
    if total == 0:
        print("未找到任何帧组。")
        return

    print(f"📦 共发现 {total} 组帧，开始生成GIF：")
    start_time = time.time()
    completed = 0
    failed = 0
    durations = []

    for i, (frame_dir, frame_files) in enumerate(frame_groups.items(), 1):
        emojicode = infer_emojicode_from_path(frame_dir)
        print(f"\n🔹 正在处理 ({i}/{total}): {emojicode} in {frame_dir}")
        t0 = time.time()
        success = convert_frames_to_gif(frame_dir, frame_files, emojicode)
        t1 = time.time()
        elapsed = t1 - t0
        durations.append(elapsed)

        if success:
            completed += 1
        else:
            failed += 1

        avg_time = sum(durations) / len(durations)
        remaining = avg_time * (total - i)
        total_elapsed = time.time() - start_time
        progress = (i / total) * 100

        print(f"📈 进度: {progress:.1f}% | 已完成: {completed} | 失败: {failed} | 总数: {total}")
        print(f"⏱️ 当前耗时: {format_time(elapsed)} | 总耗时: {format_time(total_elapsed)} | 预计剩余: {format_time(remaining)}")

    print("\n🎉 批量GIF生成完成！")
    print(f"✅ 成功: {completed} | ❌ 失败: {failed} | 总数: {total}")
    print(f"⏱️ 总耗时: {format_time(time.time() - start_time)}")

if __name__ == "__main__":
    batch_convert()

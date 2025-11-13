import os
import glob
from PIL import Image

# 目标目录（只处理一个）
FRAME_DIR = r"Z:\2025\emoji140\emoji_export\U+1F36A"
FRAME_PREFIX = "frame_"
FRAME_EXT = ".png"
GIF_DURATION = 200  # 每帧间隔（毫秒）
OUTPUT_NAME = "U+2B1C"  # GIF 文件名（不含扩展名）

def convert_frames_to_gif(frame_dir, output_name):
    # 获取所有帧文件并按编号排序
    frame_files = sorted(
        glob.glob(os.path.join(frame_dir, f"{FRAME_PREFIX}*{FRAME_EXT}")),
        key=lambda f: int(''.join(filter(str.isdigit, os.path.basename(f))) or 0)
    )

    if not frame_files:
        print("❌ 未找到任何帧文件")
        return

    images = []
    for fpath in frame_files:
        try:
            img = Image.open(fpath).convert("RGBA")  # 保留透明通道
            images.append(img)
        except Exception as e:
            print(f"⚠️ 无法读取图像: {fpath} ({e})")

    if not images:
        print("❌ 没有有效帧")
        return

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
        print(f"✅ 成功生成 GIF: {gif_path}")
    except Exception as e:
        print(f"❌ GIF生成失败: {gif_path} ({e})")

if __name__ == "__main__":
    convert_frames_to_gif(FRAME_DIR, OUTPUT_NAME)

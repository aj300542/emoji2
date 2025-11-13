import os
import shutil

# 源目录（存放GIF文件的地方）
source_dir = r"Z:\2025\gif\new"
# 目标根目录（存放emojicode目录的地方）
target_root = r"Z:\2025\emoji140\emoji_export"

# 遍历源目录下的所有文件
for filename in os.listdir(source_dir):
    # 拼接完整的源文件路径
    source_path = os.path.join(source_dir, filename)
    
    # 只处理文件（跳过子文件夹），且只处理.gif后缀的文件
    if os.path.isfile(source_path) and filename.endswith(".gif"):
        # 提取emojicode（去掉末尾的.gif后缀）
        # 例如 "U+1F00C.gif" → "U+1F00C"
        emoji_code = os.path.splitext(filename)[0]
        
        # 构建目标目录路径（emoji_export下的emojicode目录）
        target_dir = os.path.join(target_root, emoji_code)
        
        # 检查目标目录是否存在
        if os.path.exists(target_dir) and os.path.isdir(target_dir):
            # 构建目标文件路径（移动后的路径）
            target_path = os.path.join(target_dir, filename)
            
            # 检查目标路径是否已存在同名文件
            if os.path.exists(target_path):
                print(f"跳过：{filename} 在 {target_dir} 中已存在")
            else:
                # 移动文件
                shutil.move(source_path, target_path)
                print(f"已移动：{filename} → {target_dir}")
        else:
            print(f"跳过：目标目录 {target_dir} 不存在")

print("批量移动完成！")
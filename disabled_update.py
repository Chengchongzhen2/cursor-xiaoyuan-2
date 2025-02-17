import os
import platform
import subprocess
import sys
from pathlib import Path


def get_updater_path():
    """获取不同操作系统下的更新器路径"""
    system = platform.system()
    home = Path.home()

    if system == "Windows":
        return Path(os.getenv("LOCALAPPDATA")) / "cursor-updater"
    elif system == "Darwin":  # macOS
        return home / "Library/Application Support/cursor-updater"
    elif system == "Linux":
        return home / ".config/cursor-updater"
    else:
        raise OSError(f"不支持的操作系统: {system}")


def disable_updates():
    """禁用 Cursor 自动更新"""
    try:
        updater_path = get_updater_path()

        # 如果目录存在，删除它
        if updater_path.is_dir():
            for item in updater_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    for subitem in item.iterdir():
                        subitem.unlink()
                    item.rmdir()
            updater_path.rmdir()
            print(f"✓ 已删除更新目录: {updater_path}")

        # 如果文件存在，先删除
        if updater_path.is_file():
            updater_path.unlink()

        # 创建阻止文件
        updater_path.touch()
        print(f"✓ 已创建阻止文件: {updater_path}")

    except Exception as e:
        print(f"错误: 禁用更新失败: {e}")
        return False

    return True


def main():
    print("开始禁用 Cursor 自动更新...")

    # 2. 禁用更新
    if disable_updates():
        print("\n✅ Cursor 自动更新已成功禁用")
        print("注意: 如需更新 Cursor，请手动下载并安装新版本")
    else:
        print("\n❌ 禁用自动更新失败")
        sys.exit(1)


if __name__ == "__main__":
    main()

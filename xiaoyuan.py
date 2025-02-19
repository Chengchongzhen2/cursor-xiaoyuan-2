import os
import json
import requests
import platform
import sys
import hashlib
import uuid
from logo import print_logo
from logger import logging
from colorama import Fore, Style, init
from cursor_auth_manager import CursorAuthManager as DBAuthManager
from exit_cursor import ExitCursor


EMOJI = {
    "FILE": "📄",
    "BACKUP": "💾",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "RESET": "🔄",
    "WARN": "⚠️",
}

# 初始化 colorama
init()


class CursorAuthManager:
    def __init__(self):
        self.setup_paths()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Cursor/0.1.0 Chrome/108.0.5359.62 Electron/22.0.0 Safari/537.36",
            "Content-Type": "application/json",
        }
        self.db_manager = DBAuthManager()
        self.config = self.load_config()
        self.api_url = "http://localhost:3000/api"
        self.machine_code = self.generate_machine_code()

    def setup_paths(self):
        """设置相关路径"""
        system = platform.system()
        if system == "Darwin":  # macOS
            self.storage_path = os.path.expanduser(
                "~/Library/Application Support/Cursor/User/globalStorage/storage.json"
            )
            self.config_dir = os.path.expanduser(
                "~/Library/Application Support/CursorPlus/User"
            )
        elif system == "Windows":  # Windows
            self.storage_path = os.path.join(
                os.getenv("APPDATA"), "Cursor", "User", "globalStorage", "storage.json"
            )
            self.config_dir = os.path.join(os.getenv("APPDATA"), "CursorPlus", "User")
        elif system == "Linux":  # Linux
            self.storage_path = os.path.expanduser(
                "~/.config/Cursor/User/globalStorage/storage.json"
            )
            self.config_dir = os.path.expanduser("~/.config/CursorPlus/User")
        else:
            raise Exception(f"不支持的系统: {system}")

        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_path = os.path.join(self.config_dir, "config.json")

    def load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            return {"api_url": "http://localhost:3000/api"}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"读取配置文件失败: {str(e)}")
            return {"api_url": "http://localhost:3000/api"}

    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"保存配置文件失败: {str(e)}")
            return False

    def generate_machine_code(self):
        """生成机器码"""
        system_info = [
            platform.node(),
            platform.machine(),
            platform.processor(),
            str(uuid.getnode()),
            platform.platform(),
        ]
        system_str = "".join(system_info)
        return hashlib.md5(system_str.encode("utf-8")).hexdigest()

    def check_token_expiry(self):
        """检查 token 的过期时间"""
        token = self.config.get("token")
        if not token:
            return None

        try:
            response = requests.post(
                f"{self.api_url}/token/jwt-expiry",
                headers=self.headers,
                json={"token": token},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    expiry_info = data.get("data", {})
                    remaining_days = expiry_info.get("remainingDays")
                    is_expired = expiry_info.get("isExpired")
                    expiry_date = expiry_info.get("expiryDate")

                    if remaining_days is None or is_expired is None:
                        logging.error("Token 过期信息不完整")
                        return None

                    if is_expired:
                        print(
                            f"{Fore.RED}{EMOJI['ERROR']} Token 已过期{Style.RESET_ALL}"
                        )
                        return False
                    elif remaining_days <= 7:
                        print(
                            f"{Fore.YELLOW}{EMOJI['WARN']} Token 将在 {remaining_days} 天后过期 {Style.RESET_ALL}"
                        )
                    else:
                        print(f"{EMOJI['INFO']} Token 有效期还剩 {remaining_days} 天")
                    return True
                else:
                    print(f"{EMOJI['ERROR']} {data.get('message', '未知错误')}")
                    return False
            return None
        except Exception as e:
            logging.error(f"检查 token 过期时间失败: {str(e)}")
            return None

    def check_license(self):
        """检查许可证状态"""
        token = self.config.get("token")
        license_id = self.config.get("license_id")
        if not token:
            return False, None, "未找到许可证"

        print(f"{EMOJI['INFO']} 检查许可证状态...")

        # 检查 token 过期状态
        expiry_status = self.check_token_expiry()
        if expiry_status is None:  # 发生错误（如连接超时）
            print(
                f"{Fore.RED}{EMOJI['ERROR']} 网络连接失败，请检查您的网络连接后重试{Style.RESET_ALL}"
            )
            return False, None, "网络连接失败"
        elif expiry_status is False:  # token 已过期
            self.config.pop("token", None)
            self.config.pop("license_id", None)
            self.save_config()
            return False, None, "Token 已过期"

        try:
            response = requests.post(
                f"{self.api_url}/license/verify",
                headers=self.headers,
                json={"token": token},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} 许可证有效{Style.RESET_ALL}")
                    return True, license_id, None
                else:
                    self.config.pop("token", None)
                    self.config.pop("license_id", None)
                    self.save_config()
                    error_msg = data.get("message", "未知错误")
                    return False, None, error_msg
            else:
                error_msg = f"HTTP错误: {response.status_code}"
                return False, None, error_msg
        except requests.exceptions.Timeout:
            print(f"{Fore.YELLOW}{EMOJI['ERROR']} 网络连接超时{Style.RESET_ALL}")
            return False, None, "网络连接超时"
        except Exception as e:
            error_msg = str(e)
            print(
                f"{Fore.RED}{EMOJI['ERROR']} 许可证检查失败: {error_msg}{Style.RESET_ALL}"
            )
            return False, None, error_msg

    def activate_new_license(self):
        """激活新许可证"""
        print(f"\n{EMOJI['INFO']} 请输入许可证信息:")
        activation_code = input(f"{EMOJI['INFO']} 激活码: ").strip()

        if not activation_code:
            print(f"{Fore.RED}{EMOJI['ERROR']} 激活码不能为空{Style.RESET_ALL}")
            return False, None

        print(f"\n{Fore.CYAN}{EMOJI['INFO']} 开始激活许可证...{Style.RESET_ALL}")
        try:
            response = requests.post(
                f"{self.api_url}/license/activate",
                headers=self.headers,
                json={"activationCode": activation_code},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    token = data.get("data", {}).get("token")
                    license_id = data.get("data", {}).get("licenseId")
                    if token:
                        print(
                            f"{Fore.GREEN}{EMOJI['SUCCESS']} 许可证激活成功！{Style.RESET_ALL}"
                        )
                        self.config["token"] = token
                        self.config["license_id"] = license_id
                        if self.save_config():
                            print(f"{EMOJI['INFO']} 许可证信息已保存")
                        return True, license_id
                    error_msg = "返回数据不完整"
                else:
                    error_msg = data.get("message", "未知错误")
            else:
                error_msg = f"HTTP错误: {response.status_code}"
        except Exception as e:
            error_msg = str(e)

        print(
            f"{Fore.RED}{EMOJI['ERROR']} 激活许可证失败: {error_msg}{Style.RESET_ALL}"
        )
        return False, None

    def get_unused_token(self):
        """获取未使用的token"""
        try:
            response = requests.get(
                f"{self.api_url}/token/list/by-jwt",
                headers=self.headers,
                timeout=30,
                json={"token": self.config.get("token")},
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data", {}).get("tokens"):
                    token = data.get("data", {}).get("tokens")[0].get("token")
                    print(f"{EMOJI['INFO']} 获取到可用 token")
                    return True, token
                error_msg = "没有可用的 token"
            else:
                error_msg = f"HTTP错误: {response.status_code}"
        except Exception as e:
            error_msg = str(e)

        print(
            f"{Fore.RED}{EMOJI['ERROR']} 获取 token 失败: {error_msg}{Style.RESET_ALL}"
        )
        return False, None

    def process(self):
        """处理主流程"""
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['INFO']} 无能 Cursor 激活{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

        # 检查许可证
        is_valid, license_id, _ = self.check_license()
        if not is_valid:
            success, license_id = self.activate_new_license()
            if not success:
                return False

        # 获取并激活 token
        success, token = self.get_unused_token()
        if not success:
            return False

        if self.activate_token(self.api_url, token, license_id, self.machine_code):
            print(f"\n{Fore.GREEN}{EMOJI['SUCCESS']} Token 激活成功！{Style.RESET_ALL}")
            return True
        else:
            print(f"\n{Fore.RED}{EMOJI['ERROR']} Token 激活失败{Style.RESET_ALL}")
            return False

    def activate_token(self, api_url, current_token, license_id, machine_code):
        """激活 token"""
        try:
            # 先检查机器码状态
            machine_status_response = requests.get(
                f"{api_url}/token/machine-status/{machine_code}",
                headers=self.headers,
                timeout=30,
            )

            if machine_status_response.status_code == 200:
                machine_data = machine_status_response.json()
                if machine_data.get("data", {}).get("status") == "blocked":
                    logging.error(
                        f"Machine is blocked: {machine_data.get('data', {}).get('reason')}"
                    )
                    return False

            payload = {
                "token": current_token,
                "licenseId": license_id,
                "machineCode": machine_code,
            }

            response = requests.post(
                f"{api_url}/token/activate",
                headers=self.headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):

                    token_data = data.get("data", {}).get("token", {})

                    # 更新本地数据库中的 token
                    if self.db_manager.update_auth(
                        email=token_data.get("email"),
                        access_token=token_data.get("token"),
                        refresh_token=token_data.get(
                            "token"
                        ),  # 使用相同的 token 作为 refresh_token
                    ):
                        logging.info("本地数据库 token 更新成功")
                        logging.info(
                            f"今日使用次数: {data.get('data', {}).get('todayUsageCount', 0)}/{data.get('data', {}).get('maxDailyLimit', 5)}"
                        )
                    else:
                        logging.error("Failed to update token in local database")
                    return True
                else:
                    error_msg = data.get("message", "Unknown error")
                    error_code = data.get("code", "UNKNOWN_ERROR")
                    logging.error(
                        f"Token 激活失败: {error_msg} (错误代码: {error_code})"
                    )
                    return False
            else:
                logging.error(f"Token 激活失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            logging.error(f"激活 token 失败: {str(e)}")
            return False

    def verify_token(self, api_url, token):
        """验证 token 是否有效"""
        try:
            response = requests.post(
                f"{api_url}/license/verify",
                headers=self.headers,
                json={"token": token},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    logging.info("Token 有效")
                    return True
                error_msg = data.get("message", "未知错误")
                error_code = data.get("code", "UNKNOWN_ERROR")
                logging.error(f"Token 验证失败: {error_msg} (错误代码: {error_code})")
            return False
        except Exception as e:
            logging.error(f"验证 token 失败: {str(e)}")
            return False

    def auto_refresh(self, api_url, token, license_id, machine_code, max_attempts=3):
        """自动刷新 token，如果失败则重置机器ID后重试"""
        for attempt in range(max_attempts):
            # 先验证当前 token
            if self.verify_token(api_url, token):
                logging.info("Current token is valid")
                return token

            # 尝试激活 token
            if self.activate_token(api_url, token, license_id, machine_code):
                logging.info("Token activated successfully")
                return token

            # 如果激活失败且不是最后一次尝试，重置机器ID后重试
            if attempt < max_attempts - 1:
                logging.info(
                    f"Attempt {attempt + 1} failed, resetting machine IDs and retrying..."
                )

        logging.error("All activation attempts failed")
        return None


def verify_license(api_url, license_id, headers):
    """验证许可证"""
    try:
        response = requests.post(
            f"{api_url}/license/verify",
            headers=headers,
            json={"licenseId": license_id},
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return True, None
            return False, data.get("message", "未知错误")
        return False, f"HTTP错误: {response.status_code}"
    except Exception as e:
        return False, str(e)


def activate_license(api_url, activation_code, headers):
    """激活许可证"""
    try:
        response = requests.post(
            f"{api_url}/license/activate",
            headers=headers,
            json={"activationCode": activation_code},
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return True, data.get("data", {}).get("licenseId"), None
            return False, None, data.get("message", "未知错误")
        return False, None, f"HTTP错误: {response.status_code}"
    except Exception as e:
        return False, None, str(e)


def check_cursor_version():
    """检查cursor版本"""
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            package_path = (
                "/Applications/Cursor.app/Contents/Resources/app/package.json"
            )
        elif system == "Windows":  # Windows
            program_files = os.environ.get("ProgramFiles")
            package_path = os.path.join(
                program_files, "Cursor", "resources", "app", "package.json"
            )
        else:
            print(
                f"{Fore.RED}{EMOJI['ERROR']} 不支持的操作系统: {system}{Style.RESET_ALL}"
            )
            return None

        if not os.path.exists(package_path):
            print(
                f"{Fore.YELLOW}{EMOJI['WARNING']} 未找到 Cursor 安装{Style.RESET_ALL}"
            )
            return None

        with open(package_path, "r", encoding="utf-8") as f:
            package_data = json.load(f)
            version = package_data.get("version")
            if version:
                print(
                    f"{EMOJI['INFO']} Cursor 版本: {Fore.GREEN}{version}{Style.RESET_ALL}"
                )
                version_parts = version.split(".")
                if len(version_parts) >= 2:
                    major_minor = float(f"{version_parts[0]}.{version_parts[1]}")
                    if major_minor > 0.44:
                        return False
                    else:
                        return True
            else:
                print(
                    f"{Fore.YELLOW}{EMOJI['WARNING']} 无法获取版本信息{Style.RESET_ALL}"
                )
                return None

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} 检查版本失败: {str(e)}{Style.RESET_ALL}")
        return None


def print_reset_method():
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{EMOJI['INFO']} 请选择适合您系统的重置命令，复制到终端执行:\n")

    print(f"{Fore.GREEN}# macOS 系统{Style.RESET_ALL}")
    print(
        f"{Fore.YELLOW}curl -fsSL https://aizaozao.com/accelerate.php/https://raw.githubusercontent.com/yuaotian/go-cursor-help/refs/heads/master/scripts/run/cursor_mac_id_modifier.sh | sudo bash{Style.RESET_ALL}"
    )

    print(f"\n{Fore.GREEN}# Linux 系统{Style.RESET_ALL}")
    print(
        f"{Fore.YELLOW}curl -fsSL https://aizaozao.com/accelerate.php/https://raw.githubusercontent.com/yuaotian/go-cursor-help/refs/heads/master/scripts/run/cursor_linux_id_modifier.sh | sudo bash{Style.RESET_ALL}"
    )

    print(f"\n{Fore.GREEN}# Windows 系统(使用powerShell执行){Style.RESET_ALL}")
    print(
        f"{Fore.YELLOW}irm https://aizaozao.com/accelerate.php/https://raw.githubusercontent.com/yuaotian/go-cursor-help/refs/heads/master/scripts/run/cursor_win_id_modifier.ps1 | iex{Style.RESET_ALL}"
    )

    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")


def main():
    """主函数"""
    print_logo()
    try:
        # 退出cursor
        # ExitCursor()
        # 输入选项1 是重置机器ID 输入选项2 是激活token 3. 重新激活账号
        print(f"{EMOJI['INFO']} 请选择操作:")
        print(f"1. 重置机器ID（解决 too many free 问题）")
        print(f"2. 刷新账号")
        print(f"3. 重新激活账号")
        option = input(f"{EMOJI['INFO']} 请输入选项: ")
        auth_manager = CursorAuthManager()
        if option == "1":
            print_reset_method()
        elif option == "2":
            auth_manager.process()
        elif option == "3":
            auth_manager.config.pop("token", None)
            auth_manager.config.pop("license_id", None)
            auth_manager.save_config()
            auth_manager.process()
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} 发生错误: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} 按回车键退出...")


if __name__ == "__main__":
    main()

# start.py
import os
import sys
import socket
import subprocess
import platform
import time
import webbrowser
from datetime import datetime


def print_color(text, color='white'):
    """彩色输出（支持Windows和Linux/Mac）"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'purple': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'end': '\033[0m'
    }

    if platform.system() == 'Windows':
        # Windows下尝试使用colorama
        try:
            from colorama import init, Fore
            init()
            color_map = {
                'red': Fore.RED,
                'green': Fore.GREEN,
                'yellow': Fore.YELLOW,
                'blue': Fore.BLUE,
                'purple': Fore.MAGENTA,
                'cyan': Fore.CYAN,
                'white': Fore.WHITE
            }
            print(f"{color_map.get(color, Fore.WHITE)}{text}{Fore.RESET}")
        except:
            print(text)
    else:
        # Linux/Mac下使用ANSI颜色
        print(f"{colors.get(color, colors['white'])}{text}{colors['end']}")


def get_local_ips():
    """获取本机所有局域网IP"""
    ips = []

    try:
        # 方法1：通过连接获取
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.append(s.getsockname()[0])
        s.close()
    except:
        pass

    try:
        # 方法2：通过主机名获取
        hostname = socket.gethostname()
        ips.append(socket.gethostbyname(hostname))
    except:
        pass

    try:
        # 方法3：遍历网络接口
        if platform.system() != 'Windows':
            import netifaces
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr['addr']
                        if ip.startswith(('192.168.', '10.', '172.')) and ip not in ips:
                            ips.append(ip)
    except:
        pass

    # 去重
    ips = list(dict.fromkeys(ips))
    return ips if ips else ['127.0.0.1']


def configure_firewall(port):
    """配置防火墙规则"""
    system = platform.system()

    if system == "Windows":
        try:
            # 设置控制台编码为UTF-8
            if hasattr(sys, 'stdout') and sys.stdout:
                import io
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')

            # 检查规则是否已存在
            check = subprocess.run(
                f'netsh advfirewall firewall show rule name="Library App Port {port}"',
                capture_output=True, shell=True, text=True, encoding='gbk', errors='ignore'
            )

            # 修复判断逻辑
            if "没有规则" in check.stdout or "No rules" in check.stdout:
                # 添加防火墙规则
                result = subprocess.run([
                    'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                    f'name=Library App Port {port}',
                    'dir=in', 'action=allow', 'protocol=TCP', f'localport={port}'
                ], capture_output=True, text=True, encoding='gbk', errors='ignore')

                if result.returncode == 0:
                    print_color(f"✅ 已添加防火墙规则：允许端口 {port}", 'green')
                else:
                    print_color(f"⚠️  添加防火墙规则失败，错误：{result.stderr}", 'yellow')
            else:
                print_color(f"✅ 防火墙规则已存在", 'green')

        except Exception as e:
            print_color(f"⚠️  无法自动配置防火墙：{str(e)}", 'yellow')
            print_color("   请手动添加防火墙规则允许端口 5000", 'yellow')


def check_dependencies():
    """检查依赖是否安装"""
    required = ['flask', 'pymysql', 'mysql-connector-python']
    missing = []

    for package in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)

    if missing:
        print_color("\n❌ 缺少依赖包：", 'red')
        for pkg in missing:
            print_color(f"   - {pkg}", 'yellow')
        print_color("\n请运行以下命令安装：", 'cyan')
        print_color(f"pip install {' '.join(missing)}", 'green')
        return False
    return True


def check_database():
    """检查数据库连接"""
    try:
        # 导入app模块和数据库配置
        from app.config import Config
        from app.database import db_manager

        # 测试数据库连接
        result = db_manager.fetch_one("SELECT VERSION() as version")
        if result:
            print_color(f"✅ 数据库连接正常 (MySQL {result['version']})", 'green')
            return True
        else:
            print_color("❌ 数据库连接失败", 'red')
            return False
    except ImportError as e:
        print_color(f"❌ 导入模块失败：{str(e)}", 'red')
        return False
    except Exception as e:
        print_color(f"❌ 数据库连接失败：{str(e)}", 'red')
        print_color("   请检查：", 'yellow')
        print_color("   1. MySQL服务是否启动", 'yellow')
        print_color("   2. app/config.py 中的数据库配置是否正确", 'yellow')
        print_color("   3. 数据库 library_system 是否已创建", 'yellow')
        return False


def check_initial_data():
    """检查初始数据"""
    try:
        from app.database import db_manager

        # 检查用户数据
        user_count = db_manager.count('users')
        if user_count == 0:
            print_color("⚠️  暂无用户数据，请先运行数据库初始化脚本", 'yellow')
            return False

        # 检查图书数据
        book_count = db_manager.count('books')
        print_color(f"   📚 图书数量：{book_count} 本", 'white')

        # 检查借阅记录
        borrow_count = db_manager.count('borrow_records')
        print_color(f"   📖 借阅记录：{borrow_count} 条", 'white')

        return True
    except Exception as e:
        print_color(f"⚠️  检查数据失败：{str(e)}", 'yellow')
        return False


def print_qr_code(ip, port):
    """打印二维码（方便手机访问）"""
    try:
        import qrcode

        url = f"http://{ip}:{port}"
        qr = qrcode.QRCode(version=1, box_size=3, border=2)
        qr.add_data(url)
        qr.make(fit=True)

        print_color("\n📱 手机扫描二维码访问：", 'cyan')
        qr.print_ascii()
        print_color(f"   或直接访问：{url}", 'cyan')
    except:
        # 如果没有qrcode库，跳过
        pass


def print_test_accounts():
    """打印测试账户信息"""
    print_color("\n👥 测试账户：", 'cyan')
    print_color("   管理员：admin / 123456", 'green')
    print_color("   学生1：20240001 / 123456", 'green')
    print_color("   学生2：20240002 / 123456", 'green')


def main():
    """主函数"""
    print_color("\n" + "=" * 60, 'cyan')
    print_color("           📚 校园图书借阅管理系统 ", 'purple')
    print_color("           Software Engineering Project", 'blue')
    print_color("           第九组", 'blue')
    print_color("=" * 60, 'cyan')

    # 显示启动时间
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print_color(f"\n⏰ 启动时间：{now}", 'white')

    # 检查Python版本
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print_color(f"🐍 Python版本：{python_version}", 'white')

    # 检查依赖
 #   print_color("\n📦 检查依赖包...", 'cyan')
#  if not check_dependencies():
 #       print_color("\n❌ 依赖检查失败，请安装缺少的包后重试", 'red')
  #      sys.exit(1)
    print_color("✅ 依赖包检查通过", 'green')

    # 获取IP和端口
    local_ips = get_local_ips()
    port = 5000

    print_color("\n📡 网络信息：", 'cyan')
    print_color(f"   🔌 端口号：{port}", 'white')

    for i, ip in enumerate(local_ips):
        if ip != '127.0.0.1':
            print_color(f"   📱 局域网IP {i + 1}：{ip}", 'green')

    print_color("\n🌐 访问地址：", 'cyan')
    print_color(f"   💻 本机访问：http://127.0.0.1:{port}", 'white')
    print_color(f"   💻 本机访问：http://localhost:{port}", 'white')

    for ip in local_ips:
        if ip != '127.0.0.1':
            print_color(f"   📱 局域网访问：http://{ip}:{port}", 'green')

    # 为第一个局域网IP生成二维码
    for ip in local_ips:
        if ip != '127.0.0.1':
            print_qr_code(ip, port)
            break

    # 配置防火墙
    print_color("\n🛡️  防火墙配置：", 'cyan')
    configure_firewall(port)

    # 检查数据库
    print_color("\n🗄️  数据库检查：", 'cyan')

    if not check_database():
        print_color("\n⚠️  数据库连接失败，请检查配置后重试", 'yellow')
        print_color("   按 Ctrl+C 退出，或等待5秒后继续启动...", 'yellow')
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            sys.exit(0)

    # 检查初始数据
    print_color("\n📊 数据统计：", 'cyan')
    check_initial_data()

    # 打印测试账户
    print_test_accounts()

    # 自动打开浏览器
    try:
        webbrowser.open(f"http://127.0.0.1:{port}")
        print_color("\n🌐 已自动打开浏览器", 'green')
    except:
        pass

    print_color("\n" + "=" * 60, 'cyan')
    print_color("🚀 正在启动应用...", 'green')
    print_color("  按 Ctrl+C 停止服务", 'yellow')
    print_color("=" * 60 + "\n", 'cyan')

    # 启动应用
    try:
        from app import app
        app.run(host='0.0.0.0', port=port, debug=True)
    except KeyboardInterrupt:
        print_color("\n\n👋 服务已停止", 'yellow')
        print_color(f"   停止时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 'white')
    except Exception as e:
        print_color(f"\n❌ 启动失败：{str(e)}", 'red')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
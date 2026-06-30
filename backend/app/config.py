# -*- coding: utf-8 -*-
"""
配置文件
"""
import os
import sys


def get_exe_dir():
    """获取可执行文件所在目录（打包后为exe目录，开发时为项目根目录）

    Returns:
        可执行文件所在目录的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        return os.path.dirname(sys.executable)
    else:
        # 开发模式：config.py 位于 backend/app/ 下
        # dirname×1 → backend/app
        # dirname×2 → backend
        # dirname×3 → 项目根目录
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_resource_dir():
    """获取资源文件目录（打包后为临时解压目录，开发时为项目根目录）

    Returns:
        资源文件目录的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，临时解压目录
        return sys._MEIPASS
    else:
        # 开发模式：config.py 位于 backend/app/ 下，需往上3级到项目根目录
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_data_dir():
    """获取数据存储目录（DB、日志、截图、模板等运行时产出）

    优先级：
    1. 环境变量 PATROL_DEV_OUTPUT_DIR → 开发模式 run_dev.py 设置，指向 run_dev/
    2. PyInstaller 打包 → exe 所在目录
    3. 直接运行 → 项目根目录

    Returns:
        数据存储目录的绝对路径
    """
    dev_dir = os.environ.get("PATROL_DEV_OUTPUT_DIR", "")
    if dev_dir:
        return dev_dir
    return get_exe_dir()


class Settings:
    """应用配置类"""

    # 应用名称
    APP_NAME = "巡检助手 WEBUI"

    # 应用版本
    APP_VERSION = "1.0.2"

    # 调试模式
    DEBUG = False

    # 服务监听地址
    HOST = "127.0.0.1"

    # 服务端口
    PORT = 8000

    # 启动后自动打开浏览器
    AUTO_OPEN_BROWSER = True

    # 数据库文件路径（放在数据目录下）
    DB_PATH = os.path.join(get_data_dir(), "patrol.db")

    # 日志目录（放在数据目录下）
    LOG_DIR = os.path.join(get_data_dir(), "log")

    # 截图目录 key，供外部使用
    SCREENSHOT_DIR = os.path.join(get_data_dir(), "screen")

    # 前端静态文件目录
    STATIC_DIR = os.path.join(get_resource_dir(), "web", "dist")

    # CORS 允许的源（开发模式允许所有来源）
    CORS_ORIGINS = [
        "http://localhost",
        "http://localhost:8080",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # CORS 允许的凭证
    CORS_ALLOW_CREDENTIALS = True

    # CORS 允许的方法
    CORS_ALLOW_METHODS = ["*"]

    # CORS 允许的请求头
    CORS_ALLOW_HEADERS = ["*"]


# 全局配置实例
settings = Settings()

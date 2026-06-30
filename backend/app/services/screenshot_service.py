# -*- coding: utf-8 -*-
"""
截图服务模块
提供全屏截图、URL管理、任务管理、快捷键监听等功能
"""
import os
import time
import ctypes
import webbrowser
import threading
from datetime import datetime
from PIL import ImageGrab
from pynput import keyboard
from app.database import db
from app.config import get_data_dir

# Windows 常量
SW_RESTORE = 9

# 加载 Win32 API
_user32 = ctypes.windll.user32


class ScreenshotService:
    """截图服务类"""

    def __init__(self):
        self.current_url = None
        self.current_ip = None
        self.current_task_id = None
        self.current_device_id = None
        self.screenshot_count = 0
        self.hotkey = '<alt>+q'
        self.is_listening = False
        self.listener = None

    def _get_screen_dir(self):
        """获取截图保存目录"""
        screen_dir = os.path.join(get_data_dir(), 'screen')
        if not os.path.exists(screen_dir):
            os.makedirs(screen_dir)
        return screen_dir

    def set_hotkey(self, hotkey_str):
        """设置截图快捷键"""
        self.hotkey = hotkey_str
        if self.is_listening:
            self.stop_listening()
            self.start_listening()

    def start_listening(self):
        """开始监听快捷键"""
        if self.is_listening:
            return True

        try:
            def on_capture():
                self.capture_screen()

            hotkey_map = {self.hotkey: on_capture}
            self.listener = keyboard.GlobalHotKeys(hotkey_map)
            self.listener.start()
            self.is_listening = True
            print(f"[截图服务] 快捷键监听已启动 ({self.hotkey})")
            return True
        except Exception as e:
            print(f"[截图服务] 启动监听失败: {str(e)}")
            return False

    def stop_listening(self):
        """停止监听快捷键"""
        if self.listener:
            self.listener.stop()
            self.listener = None
        self.is_listening = False
        print("[截图服务] 停止快捷键监听")

    def _bring_browser_to_front(self):
        """URL 跳转后将浏览器窗口拉到前台"""
        time.sleep(0.5)
        _user32.AllowSetForegroundWindow(-1)
        hwnd = _user32.GetForegroundWindow()
        if hwnd:
            if _user32.IsIconic(hwnd):
                _user32.ShowWindow(hwnd, SW_RESTORE)
            _user32.SetForegroundWindow(hwnd)
            print(f"[截图服务] 浏览器窗口已聚焦: {hwnd}")
        else:
            print("[截图服务] 未找到前台窗口")

    def set_active_url(self, url):
        """设置当前活跃URL（兼容旧接口）"""
        self.current_url = url
        self.current_ip = self._extract_ip_from_url(url)
        self.screenshot_count = db.get_screenshot_count_by_ip(self.current_ip)

        urls = db.get_screenshot_urls()
        for u in urls:
            if u['url'] == url:
                db.set_active_screenshot_url(u['id'])
                break

        webbrowser.open(url)

        if not self.is_listening:
            self.start_listening()

        threading.Thread(target=self._bring_browser_to_front, daemon=True).start()

        print(f"[截图服务] 设置活跃URL: {url}, IP: {self.current_ip}")
        return True

    def set_active_task_device(self, task_id, device_id):
        """设置任务中的活跃设备"""
        device = db.get_task_device_by_id(device_id)
        if not device:
            print(f"[截图服务] 设备不存在: {device_id}")
            return False

        db.set_active_task_device(task_id, device_id)

        self.current_task_id = task_id
        self.current_device_id = device_id
        self.current_url = device['url']
        self.current_ip = device['ip']
        self.screenshot_count = db.get_screenshot_count_by_ip(self.current_ip)

        webbrowser.open(device['url'])

        if not self.is_listening:
            self.start_listening()

        threading.Thread(target=self._bring_browser_to_front, daemon=True).start()

        print(f"[截图服务] 设置活跃设备: {device['ip']}, URL: {device['url']}")
        return True

    def capture_screen(self):
        """全屏截图（全局可用，不依赖活跃设备）"""
        try:
            screen_dir = self._get_screen_dir()

            # 计算文件名：有活跃设备用IP命名，否则用时间戳
            self.screenshot_count += 1
            if self.current_ip:
                if self.screenshot_count == 1:
                    filename = self.current_ip
                else:
                    filename = f"{self.current_ip}_{self.screenshot_count}"
            else:
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"screenshot_{ts}"

            file_path = os.path.join(screen_dir, f"{filename}.jpg")

            # PIL全屏截图
            img = ImageGrab.grab()
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(file_path, 'JPEG', quality=85, optimize=True)

            # 有活跃设备时记录到数据库
            if self.current_ip:
                db.add_screenshot_record(self.current_url, self.current_ip, file_path)

                if self.current_task_id and self.current_device_id:
                    db.increment_task_device_count(self.current_task_id, self.current_device_id)

            print(f"[截图服务] 全屏截图成功: {file_path}")
            return file_path
        except Exception as e:
            print(f"[截图服务] 截图异常: {str(e)}")
            self.screenshot_count -= 1
            return None

    def complete_current_device(self):
        """将当前设备标记为完成"""
        if self.current_task_id and self.current_device_id:
            db.complete_task_device(self.current_task_id, self.current_device_id)
            print(f"[截图服务] 设备已完成: {self.current_ip}")

    def get_status(self):
        """获取当前状态"""
        return {
            "current_url": self.current_url,
            "current_ip": self.current_ip,
            "current_task_id": self.current_task_id,
            "current_device_id": self.current_device_id,
            "screenshot_count": self.screenshot_count,
            "is_listening": self.is_listening,
            "hotkey": self.hotkey,
        }

    def _extract_ip_from_url(self, url):
        """从URL中提取IP地址"""
        try:
            url = url.replace('https://', '').replace('http://', '')
            ip = url.split(':')[0].split('/')[0]
            return ip
        except Exception:
            return ''

    def import_urls_from_text(self, text):
        """从文本导入URL列表"""
        try:
            urls = []
            for line in text.strip().split('\n'):
                url = line.strip()
                if url and (url.startswith('http://') or url.startswith('https://')):
                    urls.append(url)

            if urls:
                db.clear_screenshot_urls()
                db.add_screenshot_urls(urls)
                print(f"[截图服务] 导入 {len(urls)} 个URL")
                return len(urls)
            return 0
        except Exception as e:
            print(f"[截图服务] 导入URL失败: {str(e)}")
            return 0


# 全局截图服务实例
screenshot_service = ScreenshotService()

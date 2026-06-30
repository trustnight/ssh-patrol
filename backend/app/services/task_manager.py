# -*- coding: utf-8 -*-
"""
批量巡检任务管理器
"""
import time
import threading
import logging
from typing import Dict, List, Callable, Optional

logger = logging.getLogger(__name__)


class TaskManager:
    """批量巡检任务管理器

    管理批量巡检任务的状态、日志和回调机制，
    支持WebSocket实时日志推送。
    """

    def __init__(self):
        """初始化任务管理器"""
        self._tasks: Dict[str, dict] = {}
        self._task_logs: Dict[str, List[str]] = {}
        self._log_callbacks: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self._cleanup_timer = None
        self._cleanup_interval = 3600
        self._task_expire_time = 86400

    def create_task(self, task_id: str, total_devices: int, template_name: str,
                     devices: list = None, max_workers: int = 5) -> dict:
        """创建新的巡检任务

        Args:
            task_id: 任务ID
            total_devices: 总设备数
            template_name: 模板名称
            devices: 设备信息列表（用于延迟启动）
            max_workers: 最大并发数

        Returns:
            任务信息字典
        """
        with self._lock:
            task = {
                "task_id": task_id,
                "status": "pending",
                "total_devices": total_devices,
                "success_count": 0,
                "fail_count": 0,
                "progress": 0,
                "results": [],
                "template_name": template_name,
                "devices": devices or [],
                "max_workers": max_workers,
                "cancel_flag": False,
                "created_at": time.time(),
                "updated_at": time.time()
            }
            self._tasks[task_id] = task
            self._task_logs[task_id] = []
            self._log_callbacks[task_id] = []
            logger.info(f"创建巡检任务: {task_id}, 设备数: {total_devices}")
            return task.copy()

    def get_task_devices(self, task_id: str) -> Optional[dict]:
        """获取任务的设备和配置信息（用于延迟启动）

        Returns:
            dict with keys: devices, template_name, max_workers, 或 None
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            return {
                "devices": task.get("devices", []),
                "template_name": task.get("template_name", ""),
                "max_workers": task.get("max_workers", 5)
            }

    def update_task_status(self, task_id: str, **kwargs) -> Optional[dict]:
        """更新任务状态

        Args:
            task_id: 任务ID
            **kwargs: 要更新的字段

        Returns:
            更新后的任务信息，任务不存在返回None
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"更新任务状态失败，任务不存在: {task_id}")
                return None

            self._tasks[task_id].update(kwargs)
            self._tasks[task_id]["updated_at"] = time.time()
            return self._tasks[task_id].copy()

    def get_task(self, task_id: str) -> Optional[dict]:
        """获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典，不存在返回None
        """
        with self._lock:
            task = self._tasks.get(task_id)
            return task.copy() if task else None

    def append_log(self, task_id: str, log_text: str):
        """追加日志并触发回调

        Args:
            task_id: 任务ID
            log_text: 日志文本
        """
        with self._lock:
            if task_id not in self._task_logs:
                return

            self._task_logs[task_id].append(log_text)
            callbacks = list(self._log_callbacks.get(task_id, []))

        for callback in callbacks:
            try:
                callback(log_text)
            except Exception as e:
                logger.error(f"日志回调执行异常: {e}")

    def get_logs(self, task_id: str) -> List[str]:
        """获取任务日志列表

        Args:
            task_id: 任务ID

        Returns:
            日志列表
        """
        with self._lock:
            logs = self._task_logs.get(task_id, [])
            return list(logs)

    def register_log_callback(self, task_id: str, callback: Callable):
        """注册日志回调函数

        Args:
            task_id: 任务ID
            callback: 回调函数，接收log_text参数
        """
        with self._lock:
            if task_id not in self._log_callbacks:
                self._log_callbacks[task_id] = []
            self._log_callbacks[task_id].append(callback)
            logger.debug(f"注册日志回调: {task_id}")

    def unregister_log_callback(self, task_id: str, callback: Callable):
        """注销日志回调函数

        Args:
            task_id: 任务ID
            callback: 要注销的回调函数
        """
        with self._lock:
            if task_id in self._log_callbacks:
                try:
                    self._log_callbacks[task_id].remove(callback)
                    logger.debug(f"注销日志回调: {task_id}")
                except ValueError:
                    pass

    def add_device_result(self, task_id: str, result: dict):
        """添加设备巡检结果

        Args:
            task_id: 任务ID
            result: 设备巡检结果字典
        """
        with self._lock:
            if task_id not in self._tasks:
                return

            task = self._tasks[task_id]
            task["results"].append(result)

            if result.get("success"):
                task["success_count"] += 1
            else:
                task["fail_count"] += 1

            completed = task["success_count"] + task["fail_count"]
            task["progress"] = int(completed / task["total_devices"] * 100) if task["total_devices"] > 0 else 100
            task["updated_at"] = time.time()

    def complete_task(self, task_id: str, status: str = "completed"):
        """标记任务完成

        Args:
            task_id: 任务ID
            status: 完成状态（completed/failed）
        """
        with self._lock:
            if task_id not in self._tasks:
                return

            self._tasks[task_id]["status"] = status
            self._tasks[task_id]["progress"] = 100
            self._tasks[task_id]["updated_at"] = time.time()
            logger.info(f"巡检任务完成: {task_id}, 状态: {status}")

    def cleanup_expired_tasks(self):
        """清理过期的任务"""
        with self._lock:
            current_time = time.time()
            expired_tasks = []

            for task_id, task in self._tasks.items():
                age = current_time - task.get("updated_at", 0)
                if age > self._task_expire_time:
                    expired_tasks.append(task_id)

            for task_id in expired_tasks:
                del self._tasks[task_id]
                if task_id in self._task_logs:
                    del self._task_logs[task_id]
                if task_id in self._log_callbacks:
                    del self._log_callbacks[task_id]
                logger.info(f"清理过期任务: {task_id}")

    def start_cleanup_scheduler(self):
        """启动定时清理调度器"""
        def cleanup_loop():
            while True:
                time.sleep(self._cleanup_interval)
                try:
                    self.cleanup_expired_tasks()
                except Exception as e:
                    logger.error(f"任务清理异常: {e}")

        if self._cleanup_timer is None:
            self._cleanup_timer = threading.Thread(target=cleanup_loop, daemon=True)
            self._cleanup_timer.start()
            logger.info("任务清理调度器已启动")

    def get_all_tasks(self) -> List[dict]:
        """获取所有任务列表

        Returns:
            任务列表
        """
        with self._lock:
            return [task.copy() for task in self._tasks.values()]

    def cancel_task(self, task_id: str) -> bool:
        """取消一个正在运行的巡检任务

        设置 cancelled 标记，正在执行的设备巡检会检测到并跳过后续设备。

        Args:
            task_id: 任务ID

        Returns:
            是否成功标记为取消
        """
        with self._lock:
            if task_id not in self._tasks:
                return False
            task = self._tasks[task_id]
            if task.get("status") in ("completed", "cancelled"):
                return False
            task["cancel_flag"] = True
            task["status"] = "cancelling"
            task["updated_at"] = time.time()
            logger.info(f"任务已标记为取消: {task_id}")
            return True

    def is_cancelled(self, task_id: str) -> bool:
        """检查任务是否已被取消

        Args:
            task_id: 任务ID

        Returns:
            是否已取消
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            return task.get("cancel_flag", False)


task_manager = TaskManager()

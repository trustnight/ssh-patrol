# -*- coding: utf-8 -*-
"""
截图相关API路由
"""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.models.schemas import ApiResponse
from app.database import db
from app.config import get_data_dir
from app.services.screenshot_service import screenshot_service

router = APIRouter(prefix="/api/screenshot", tags=["截图管理"])


# ==================== 请求模型 ====================

class UrlImportRequest(BaseModel):
    """URL导入请求"""
    text: str


class SetActiveUrlRequest(BaseModel):
    """设置活跃URL请求"""
    url: str


class SetHotkeyRequest(BaseModel):
    """设置快捷键请求"""
    hotkey: str


class CreateTaskRequest(BaseModel):
    """创建截图任务请求（使用设备管理中的device_ids）"""
    name: str
    device_ids: List[int]


class SetActiveDeviceRequest(BaseModel):
    """设置活跃设备请求"""
    device_id: int


# ==================== URL管理（保留兼容） ====================

@router.post("/import-urls", response_model=ApiResponse, summary="导入URL列表")
def import_urls(request: UrlImportRequest):
    """从文本导入URL列表"""
    try:
        count = screenshot_service.import_urls_from_text(request.text)
        if count > 0:
            return ApiResponse(code=0, message=f"成功导入 {count} 个URL", data={"count": count})
        else:
            return ApiResponse(code=1, message="未找到有效的URL", data=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入URL失败: {str(e)}")


@router.get("/urls", response_model=ApiResponse, summary="获取URL列表")
def get_urls():
    """获取所有截图URL"""
    try:
        urls = db.get_screenshot_urls()
        return ApiResponse(code=0, message="success", data={"urls": urls})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取URL列表失败: {str(e)}")


@router.post("/clear-urls", response_model=ApiResponse, summary="清空URL列表")
def clear_urls():
    """清空所有截图URL"""
    try:
        db.clear_screenshot_urls()
        return ApiResponse(code=0, message="已清空", data=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")


# ==================== 截图任务管理 ====================

@router.get("/devices-with-url", response_model=ApiResponse, summary="获取有URL的设备列表")
def get_devices_with_url():
    """从设备管理列表中获取所有配置了URL的设备（供截图任务创建使用）"""
    try:
        devices = db.get_devices_with_url()
        return ApiResponse(code=0, message="success", data={"devices": devices})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备列表失败: {str(e)}")


@router.post("/tasks", response_model=ApiResponse, summary="创建截图任务")
def create_task(request: CreateTaskRequest):
    """创建截图任务（从设备管理列表中选择设备）"""
    try:
        task_id = db.create_screenshot_task(request.name, request.device_ids)
        if task_id:
            return ApiResponse(code=0, message="任务创建成功", data={"task_id": task_id})
        else:
            return ApiResponse(code=1, message="创建任务失败", data=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/tasks", response_model=ApiResponse, summary="获取任务列表")
def get_tasks():
    """获取所有截图任务"""
    try:
        tasks = db.get_screenshot_tasks()
        return ApiResponse(code=0, message="success", data={"tasks": tasks})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/tasks/{task_id}/devices", response_model=ApiResponse, summary="获取任务设备列表")
def get_task_devices(task_id: int):
    """获取截图任务的设备列表"""
    try:
        devices = db.get_screenshot_task_devices(task_id)
        return ApiResponse(code=0, message="success", data={"devices": devices})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备列表失败: {str(e)}")


@router.post("/tasks/{task_id}/set-active", response_model=ApiResponse, summary="设置活跃设备")
def set_active_device(task_id: int, request: SetActiveDeviceRequest):
    """设置当前活跃的截图设备"""
    try:
        success = screenshot_service.set_active_task_device(task_id, request.device_id)
        if success:
            return ApiResponse(code=0, message="已设置活跃设备并打开浏览器", data=screenshot_service.get_status())
        else:
            return ApiResponse(code=1, message="设置活跃设备失败", data=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置活跃设备失败: {str(e)}")


@router.post("/tasks/{task_id}/complete", response_model=ApiResponse, summary="完成当前设备")
def complete_device(task_id: int):
    """将当前活跃设备标记为完成"""
    try:
        screenshot_service.complete_current_device()
        return ApiResponse(code=0, message="设备已标记完成", data=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.delete("/tasks/{task_id}", response_model=ApiResponse, summary="删除截图任务")
def delete_task(task_id: int):
    """删除截图任务"""
    try:
        db.delete_screenshot_task(task_id)
        return ApiResponse(code=0, message="任务已删除", data=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


# ==================== 截图操作 ====================

@router.post("/set-active", response_model=ApiResponse, summary="设置活跃URL（兼容旧接口）")
def set_active_url(request: SetActiveUrlRequest):
    """设置当前活跃的截图URL"""
    try:
        success = screenshot_service.set_active_url(request.url)
        if success:
            return ApiResponse(code=0, message="已设置活跃URL并打开浏览器", data=screenshot_service.get_status())
        else:
            return ApiResponse(code=1, message="设置活跃URL失败", data=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置活跃URL失败: {str(e)}")


@router.post("/capture", response_model=ApiResponse, summary="执行全屏截图")
def capture():
    """执行全屏截图（不弹光标选区，全局可用）"""
    try:
        file_path = screenshot_service.capture_screen()
        if file_path:
            return ApiResponse(code=0, message="截图成功", data={"file_path": file_path})
        else:
            return ApiResponse(code=1, message="截图失败", data=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"截图失败: {str(e)}")


@router.get("/status", response_model=ApiResponse, summary="获取截图状态")
def get_status():
    """获取当前截图状态"""
    try:
        status = screenshot_service.get_status()
        return ApiResponse(code=0, message="success", data=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/set-hotkey", response_model=ApiResponse, summary="设置快捷键")
def set_hotkey(request: SetHotkeyRequest):
    """设置截图快捷键"""
    try:
        screenshot_service.set_hotkey(request.hotkey)
        return ApiResponse(code=0, message=f"快捷键已设置为: {request.hotkey}", data={"hotkey": request.hotkey})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置快捷键失败: {str(e)}")


@router.get("/history", response_model=ApiResponse, summary="获取截图历史")
def get_history(ip: Optional[str] = None):
    """获取截图历史记录"""
    try:
        records = db.get_screenshot_history(ip=ip)
        return ApiResponse(code=0, message="success", data={"records": records})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取截图历史失败: {str(e)}")


def _delete_file_safe(file_path):
    """安全删除本地截图文件，返回 True/False"""
    if not file_path:
        return False
    path = Path(file_path)
    if path.is_file():
        try:
            path.unlink()
            return True
        except OSError as e:
            print(f"删除文件失败: {file_path}, 错误: {e}")
            return False
    return False


def _normalize_path(file_path):
    """确保路径是绝对路径"""
    p = Path(file_path)
    if not p.is_absolute():
        # 相对于 exe 目录
        p = Path(get_data_dir()) / p
    return str(p)


@router.post("/clear-history", response_model=ApiResponse, summary="清空截图历史")
def clear_history():
    """清空所有截图历史记录，同时删除本地截图文件"""
    try:
        # 1. 获取所有截图文件路径
        file_paths = db.clear_screenshot_history()

        # 2. 删除本地文件（使用 pathlib 更健壮）
        deleted_count = 0
        fail_paths = []
        for fp in file_paths:
            fp = _normalize_path(fp)
            if _delete_file_safe(fp):
                deleted_count += 1
            else:
                fail_paths.append(fp)

        fail_count = len(fail_paths)
        msg = f"已清空 {len(file_paths)} 条记录，删除了 {deleted_count} 个文件"
        if fail_count > 0:
            msg += f"，{fail_count} 个文件删除失败"
            print(f"[截图] 删除失败的文件: {fail_paths}")

        return ApiResponse(
            code=0,
            message=msg,
            data={"total_records": len(file_paths), "deleted_files": deleted_count, "failed": fail_count}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空截图历史失败: {str(e)}")


@router.delete("/history/{record_id}", response_model=ApiResponse, summary="删除单条截图历史")
def delete_record(record_id: int):
    """删除单条截图历史记录，同时删除本地文件"""
    try:
        file_path = db.delete_screenshot_record(record_id)
        if file_path is None:
            return ApiResponse(code=1, message="记录不存在", data=None)

        file_path = _normalize_path(file_path)
        file_deleted = _delete_file_safe(file_path)

        return ApiResponse(
            code=0,
            message=f"已删除记录，本地文件{'已' if file_deleted else '未'}清理",
            data={"record_id": record_id, "file_deleted": file_deleted}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除截图记录失败: {str(e)}")

@router.post("/start-listening", response_model=ApiResponse, summary="启动快捷键监听")
def start_listening():
    """启动快捷键监听"""
    try:
        success = screenshot_service.start_listening()
        if success:
            return ApiResponse(code=0, message="快捷键监听已启动", data=screenshot_service.get_status())
        else:
            return ApiResponse(code=1, message="启动监听失败", data=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动监听失败: {str(e)}")


@router.post("/stop-listening", response_model=ApiResponse, summary="停止快捷键监听")
def stop_listening():
    """停止快捷键监听"""
    try:
        screenshot_service.stop_listening()
        return ApiResponse(code=0, message="快捷键监听已停止", data=screenshot_service.get_status())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止监听失败: {str(e)}")


@router.post("/open-folder", response_model=ApiResponse, summary="打开截图文件夹")
def open_folder():
    """打开截图保存文件夹"""
    try:
        screen_dir = os.path.join(get_data_dir(), 'screen')
        if not os.path.exists(screen_dir):
            os.makedirs(screen_dir)
        os.startfile(screen_dir)
        return ApiResponse(code=0, message="已打开文件夹", data={"path": screen_dir})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打开文件夹失败: {str(e)}")

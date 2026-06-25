# -*- coding: utf-8 -*-
"""
巡检相关API路由
"""
import os
import uuid
import asyncio
import threading
from typing import List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.models.schemas import (
    SinglePatrolRequest,
    BatchPatrolStartRequest,
    PatrolResult,
    CommandResult,
    ApiResponse
)
from app.database import db
from app.crypto_utils import crypto
from app.services.patrol_service import patrol_service
from app.services.task_manager import task_manager

router = APIRouter(prefix="/api/patrol", tags=["巡检管理"])


def _get_device_info_from_db(device_id):
    """从数据库获取设备信息"""
    device = db.get_device(device_id)
    if not device:
        return None
    return {
        "manufacturer": device["manufacturer"],
        "ip": device["ip"],
        "username": device["username"],
        "password": device["password"],
        "port": device["port"]
    }


def _run_batch_patrol(task_id, devices, template_name, max_workers):
    """后台线程执行批量巡检（asyncio异步版本）"""

    def append_log_safe(text):
        """日志追加"""
        task_manager.append_log(task_id, text)

    async def main():
        task_manager.update_task_status(task_id, status="running")

        append_log_safe(f"开始批量巡检\n")
        append_log_safe(f"设备数量: {len(devices)}\n")
        append_log_safe(f"命令模板: {template_name}\n")
        append_log_safe(f"并发数: {max_workers}\n\n")

        semaphore = asyncio.Semaphore(max(1, min(len(devices), max_workers)))

        async def patrol_device(device_info, device_index, total_devices):
            try:
                manufacturer = device_info.get("manufacturer", "Hillstone")
                ip = device_info.get("ip", "")
                username = device_info.get("username", "")
                password = device_info.get("password", "")
                port = int(device_info.get("port", 22))

                async with semaphore:
                    append_log_safe(f"\n[{ip}] ===== 开始巡检 (设备 {device_index}/{total_devices}) =====\n")

                    def device_output_func(text):
                        lines = text.split('\n')
                        prefixed_lines = []
                        for line in lines:
                            if line.strip():
                                prefixed_lines.append(f"[{ip}] {line}")
                            else:
                                prefixed_lines.append("")
                        append_log_safe('\n'.join(prefixed_lines))

                    success, cmd_results, error_msg = await patrol_service.patrol_single_device_asyncssh(
                        ip=ip,
                        port=port,
                        username=username,
                        password=password,
                        manufacturer=manufacturer,
                        template_name=template_name,
                        append_output_func=device_output_func
                    )

                    log_path = ""
                    if cmd_results:
                        log_path = patrol_service.save_patrol_results(
                            ip, cmd_results, template_name, manufacturer
                        )

                    db.add_patrol_record(
                        task_id=task_id,
                        ip=ip,
                        manufacturer=manufacturer,
                        template_name=template_name,
                        success=success,
                        log_path=log_path or ""
                    )

                    result = {
                        "ip": ip,
                        "success": success,
                        "results": [
                            {"command": cmd, "output": output, "error": error}
                            for cmd, output, error in cmd_results
                        ],
                        "error_msg": error_msg
                    }

                    task_manager.add_device_result(task_id, result)

                    if success:
                        append_log_safe(f"\n===== {ip}: 巡检成功 =====\n\n")
                    else:
                        append_log_safe(f"\n===== {ip}: 巡检失败 - {error_msg} =====\n\n")

                    return result

            except Exception as e:
                result = {
                    "ip": device_info.get("ip", "unknown"),
                    "success": False,
                    "results": [],
                    "error_msg": str(e)
                }
                task_manager.add_device_result(task_id, result)
                # 异常时也要写数据库记录
                db.add_patrol_record(
                    task_id=task_id,
                    ip=device_info.get("ip", "unknown"),
                    manufacturer=device_info.get("manufacturer", ""),
                    template_name=template_name,
                    success=False,
                    log_path=""
                )
                append_log_safe(f"\n===== {device_info.get('ip', 'unknown')}: 巡检异常 - {str(e)} =====\n\n")

        tasks = [
            patrol_device(device, idx + 1, len(devices))
            for idx, device in enumerate(devices)
        ]
        await asyncio.gather(*tasks)

        task = task_manager.get_task(task_id)
        success_count = task["success_count"] if task else 0
        fail_count = task["fail_count"] if task else 0

        append_log_safe("\n========== 巡检完成 ==========\n")
        append_log_safe(f"总设备数: {len(devices)}\n")
        append_log_safe(f"成功: {success_count}\n")
        append_log_safe(f"失败: {fail_count}\n")
        if len(devices) > 0:
            append_log_safe(f"成功率: {success_count / len(devices) * 100:.1f}%\n")
        append_log_safe("============================\n")

        task_manager.complete_task(task_id, "completed")

    try:
        asyncio.run(main())
    except Exception as e:
        task_manager.append_log(task_id, f"\n批量巡检异常: {str(e)}\n")
        task_manager.complete_task(task_id, "failed")


@router.post("/single", response_model=ApiResponse, summary="单设备巡检")
def single_patrol(request: SinglePatrolRequest):
    """单设备巡检（同步等待结果）

    Args:
        request: 巡检请求，可传device_id或device_info

    Returns:
        巡检结果
    """
    try:
        device_info = None

        if request.device_id is not None:
            device_info = _get_device_info_from_db(request.device_id)
            if not device_info:
                return ApiResponse(
                    code=1,
                    message="设备不存在",
                    data=None
                )
        elif request.device_info is not None:
            device_info = {
                "manufacturer": request.device_info.manufacturer,
                "ip": request.device_info.ip,
                "username": request.device_info.username,
                "password": request.device_info.password,
                "port": request.device_info.port
            }
        else:
            return ApiResponse(
                code=1,
                message="请提供device_id或device_info",
                data=None
            )

        success, cmd_results, error_msg = patrol_service.patrol_single_device(
            ip=device_info["ip"],
            port=device_info["port"],
            username=device_info["username"],
            password=device_info["password"],
            manufacturer=device_info["manufacturer"],
            template_name=request.template_name
        )

        log_path = ""
        if cmd_results:
            log_path = patrol_service.save_patrol_results(
                device_info["ip"], cmd_results, request.template_name, device_info["manufacturer"]
            )

        results = [
            {"command": cmd, "output": output, "error": error}
            for cmd, output, error in cmd_results
        ]

        return ApiResponse(
            code=0,
            message="巡检完成" if success else "巡检失败",
            data={
                "success": success,
                "ip": device_info["ip"],
                "results": results,
                "error_msg": error_msg,
                "log_path": log_path
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"巡检失败: {str(e)}")


@router.post("/batch/start", response_model=ApiResponse, summary="开始批量巡检")
def batch_patrol_start(request: BatchPatrolStartRequest):
    """开始批量巡检（异步执行，返回task_id）

    Args:
        request: 批量巡检请求，可传device_ids或devices

    Returns:
        task_id
    """
    try:
        devices = []

        if request.device_ids is not None and len(request.device_ids) > 0:
            for device_id in request.device_ids:
                device_info = _get_device_info_from_db(device_id)
                if device_info:
                    devices.append(device_info)
        elif request.devices is not None and len(request.devices) > 0:
            devices = [
                {
                    "manufacturer": d.manufacturer,
                    "ip": d.ip,
                    "username": d.username,
                    "password": d.password,
                    "port": d.port
                }
                for d in request.devices
            ]
        else:
            return ApiResponse(
                code=1,
                message="请提供device_ids或devices",
                data=None
            )

        if not devices:
            return ApiResponse(
                code=1,
                message="没有有效的设备",
                data=None
            )

        task_id = str(uuid.uuid4())

        task_manager.create_task(
            task_id=task_id,
            total_devices=len(devices),
            template_name=request.template_name
        )

        # 立即写入数据库记录，确保任务列表马上能看到
        for device in devices:
            db.add_patrol_record(
                task_id=task_id,
                ip=device.get("ip", ""),
                manufacturer=device.get("manufacturer", ""),
                template_name=request.template_name,
                success=False,
                log_path=""
            )

        thread = threading.Thread(
            target=_run_batch_patrol,
            args=(task_id, devices, request.template_name, request.max_workers),
            daemon=True
        )
        thread.start()

        return ApiResponse(
            code=0,
            message="批量巡检已开始",
            data={
                "task_id": task_id,
                "total_devices": len(devices)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"开始批量巡检失败: {str(e)}")


@router.get("/batch/status/{task_id}", response_model=ApiResponse, summary="查询批量巡检状态")
def batch_patrol_status(task_id: str):
    """查询批量巡检状态

    Args:
        task_id: 任务ID

    Returns:
        任务状态
    """
    try:
        task = task_manager.get_task(task_id)

        if not task:
            return ApiResponse(
                code=1,
                message="任务不存在",
                data=None
            )

        return ApiResponse(
            code=0,
            message="success",
            data={
                "task_id": task["task_id"],
                "status": task["status"],
                "total_devices": task["total_devices"],
                "success_count": task["success_count"],
                "fail_count": task["fail_count"],
                "progress": task["progress"],
                "results": task["results"]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询任务状态失败: {str(e)}")


@router.get("/tasks", response_model=ApiResponse, summary="运行中的任务列表")
def get_running_tasks():
    """获取内存中正在运行/等待的巡检任务"""
    try:
        tasks = task_manager.get_all_tasks()
        # 返回未完成的任务（pending/running/failed 都算活跃任务）
        running = [t for t in tasks if t.get("status") not in ("completed",)]
        return ApiResponse(
            code=0,
            message="success",
            data={"tasks": running}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/history", response_model=ApiResponse, summary="巡检历史列表")
def get_patrol_history(
    task_id: str = None,
    ip: str = None,
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量")
):
    """获取巡检历史列表

    Args:
        task_id: 任务ID筛选
        ip: IP筛选
        page: 页码
        page_size: 每页数量

    Returns:
        巡检历史列表（分页）
    """
    try:
        result = db.get_patrol_list(
            task_id=task_id,
            ip=ip,
            page=page,
            page_size=page_size
        )
        return ApiResponse(
            code=0,
            message="success",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取巡检历史失败: {str(e)}")


@router.get("/history/{record_id}", response_model=ApiResponse, summary="巡检历史详情")
def get_patrol_detail(record_id: int):
    """获取巡检历史详情

    Args:
        record_id: 记录ID

    Returns:
        巡检历史详情
    """
    try:
        record = db.get_patrol_detail(record_id)
        if not record:
            return ApiResponse(
                code=1,
                message="记录不存在",
                data=None
            )
        return ApiResponse(
            code=0,
            message="success",
            data={"record": record}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取巡检详情失败: {str(e)}")


class BatchDeleteRequest(BaseModel):
    task_ids: List[str]

@router.post("/history/batch-delete", response_model=ApiResponse, summary="批量删除巡检任务")
def batch_delete_patrol(request: BatchDeleteRequest):
    """批量删除巡检任务及其设备记录"""
    try:
        if not request.task_ids:
            return ApiResponse(code=1, message="请提供要删除的任务ID", data=None)
        deleted = db.delete_patrol_tasks(request.task_ids)
        return ApiResponse(code=0, message=f"已删除 {deleted} 条记录", data={"deleted": deleted})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")


@router.post("/open-folder/{record_id}", response_model=ApiResponse, summary="打开巡检结果文件夹")
def open_patrol_folder(record_id: int):
    """在资源管理器中打开巡检结果文件夹"""
    try:
        record = db.get_patrol_detail(record_id)
        if not record:
            return ApiResponse(code=1, message="记录不存在", data=None)
        log_path = record.get("log_path", "")
        if not log_path or not os.path.exists(log_path):
            return ApiResponse(code=1, message="文件夹不存在", data=None)
        os.startfile(log_path)
        return ApiResponse(code=0, message="已打开文件夹", data={"path": log_path})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打开文件夹失败: {str(e)}")


@router.get("/result/{record_id}", response_model=ApiResponse, summary="查看巡检结果")
def get_patrol_result(record_id: int):
    """读取巡检结果（按命令分行）

    Returns:
        命令列表 [{"name": "show version", "output": "..."}, ...]
    """
    try:
        record = db.get_patrol_detail(record_id)
        if not record:
            return ApiResponse(code=1, message="记录不存在", data=None)

        log_path = record.get("log_path", "")
        if not log_path or not os.path.exists(log_path):
            return ApiResponse(code=1, message="日志文件不存在", data={"commands": [], "full": ""})

        # 读取各命令文件
        commands = []
        if os.path.isdir(log_path):
            files = sorted([f for f in os.listdir(log_path) if f.endswith('.log') and f != f"{record['ip']}_full.log"])
            for fname in files:
                fpath = os.path.join(log_path, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                # 从文件名解析命令名: "01_show_version.log" → "show version"
                cmd_name = fname.split('_', 1)[-1].replace('.log', '').replace('_', ' ')
                commands.append({"name": cmd_name, "output": content})

        # 也读 full log 作为后备
        full_log = os.path.join(log_path, f"{record['ip']}_full.log")
        full_content = ""
        if os.path.exists(full_log):
            with open(full_log, "r", encoding="utf-8") as f:
                full_content = f.read()

        return ApiResponse(code=0, message="success", data={
            "ip": record["ip"],
            "success": record["success"],
            "commands": commands,
            "full": full_content
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取巡检结果失败: {str(e)}")

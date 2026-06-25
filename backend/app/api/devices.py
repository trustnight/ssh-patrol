# -*- coding: utf-8 -*-
"""
设备管理相关API路由
"""
import os
import paramiko
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.models.schemas import (
    Device,
    DeviceCreate,
    DeviceUpdate,
    TestConnectionRequest,
    ApiResponse
)
from app.database import db
from app.crypto_utils import crypto
from app.config import settings, get_exe_dir

router = APIRouter(prefix="/api/devices", tags=["设备管理"])

# 设备导入模板文件名
TEMPLATE_FILENAME = "设备导入模板.csv"


def get_template_path():
    """获取设备导入模板文件路径"""
    return os.path.join(get_exe_dir(), TEMPLATE_FILENAME)


def ensure_template_file():
    """生成/刷新设备导入模板（从数据库读取设备，密码保持加密状态）"""
    template_path = get_template_path()
    devices = db.get_devices()  # 含加密密码
    header = "manufacturer,ip,username,password,port"

    if devices:
        rows = [header]
        for d in devices:
            rows.append(f"{d['manufacturer']},{d['ip']},{d['username']},{d['password']},{d['port']}")
        content = "\n".join(rows)
    else:
        # 没有设备时生成示例模板
        pwd1 = crypto.encrypt("password123")
        pwd2 = crypto.encrypt("password456")
        content = (
            f"{header}\n"
            f"Hillstone,192.168.1.1,admin,{pwd1},22\n"
            f"Huawei,192.168.1.2,admin,{pwd2},22\n"
        )

    with open(template_path, "w", encoding="utf-8-sig") as f:
        f.write(content)


class BatchDeleteDevicesRequest(BaseModel):
    device_ids: List[int]

@router.post("/batch-delete", response_model=ApiResponse, summary="批量删除设备")
def batch_delete_devices(request: BatchDeleteDevicesRequest):
    """批量删除设备"""
    try:
        if not request.device_ids:
            return ApiResponse(code=1, message="请提供要删除的设备ID", data=None)
        deleted = db.delete_devices_batch(request.device_ids)
        return ApiResponse(code=0, message=f"已删除 {deleted} 台设备", data={"deleted": deleted})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")


@router.get("/export", response_model=ApiResponse, summary="导出设备列表（含加密密码）")
def export_devices():
    """导出所有设备，包含加密后的密码，可直接用于导入"""
    try:
        devices = db.get_devices()
        return ApiResponse(
            code=0,
            message="success",
            data={"devices": devices}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出设备失败: {str(e)}")


@router.post("/template/refresh", response_model=ApiResponse, summary="刷新设备导入模板")
def refresh_template():
    """从数据库重新生成设备导入模板CSV（密码已加密），直接写入磁盘"""
    try:
        ensure_template_file()
        return ApiResponse(
            code=0,
            message="模板已刷新",
            data={"path": get_template_path()}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新模板失败: {str(e)}")


@router.get("", response_model=ApiResponse, summary="获取设备列表")
def get_devices(keyword: str = None, manufacturer: str = None):
    """获取设备列表

    Args:
        keyword: 搜索关键词（IP或用户名）
        manufacturer: 设备厂商筛选

    Returns:
        设备列表
    """
    try:
        devices = db.get_devices(keyword=keyword, manufacturer=manufacturer)
        for device in devices:
            device.pop("password", None)
        return ApiResponse(
            code=0,
            message="success",
            data={"devices": devices}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备列表失败: {str(e)}")


@router.get("/{device_id}", response_model=ApiResponse, summary="获取设备详情")
def get_device(device_id: int):
    """获取设备详情

    Args:
        device_id: 设备ID

    Returns:
        设备详情
    """
    try:
        device = db.get_device(device_id)
        if not device:
            return ApiResponse(
                code=1,
                message="设备不存在",
                data=None
            )
        device.pop("password", None)
        return ApiResponse(
            code=0,
            message="success",
            data={"device": device}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备详情失败: {str(e)}")


@router.post("", response_model=ApiResponse, summary="新增设备")
def add_device(request: DeviceCreate):
    """新增设备

    Args:
        request: 设备信息

    Returns:
        新增结果
    """
    try:
        password = request.password
        if not crypto.is_encrypted(password):
            password = crypto.encrypt(password)

        device_id = db.add_device(
            manufacturer=request.manufacturer,
            ip=request.ip,
            username=request.username,
            password=password,
            port=request.port
        )
        if device_id:
            return ApiResponse(
                code=0,
                message="设备添加成功",
                data={"id": device_id}
            )
        elif device_id is None and db.device_exists(request.ip):
            return ApiResponse(
                code=2,
                message=f"设备已存在: {request.ip}",
                data={"duplicate": True}
            )
        else:
            return ApiResponse(
                code=1,
                message="设备添加失败",
                data=None
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加设备失败: {str(e)}")


@router.put("/{device_id}", response_model=ApiResponse, summary="更新设备")
def update_device(device_id: int, request: DeviceUpdate):
    """更新设备信息

    Args:
        device_id: 设备ID
        request: 更新的设备信息

    Returns:
        更新结果
    """
    try:
        password = request.password
        if password and not crypto.is_encrypted(password):
            password = crypto.encrypt(password)

        success = db.update_device(
            device_id=device_id,
            manufacturer=request.manufacturer,
            ip=request.ip,
            username=request.username,
            password=password,
            port=request.port
        )
        if success:
            return ApiResponse(
                code=0,
                message="设备更新成功",
                data={"success": True}
            )
        else:
            return ApiResponse(
                code=1,
                message="设备更新失败",
                data={"success": False}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新设备失败: {str(e)}")


@router.delete("/{device_id}", response_model=ApiResponse, summary="删除设备")
def delete_device(device_id: int):
    """删除设备

    Args:
        device_id: 设备ID

    Returns:
        删除结果
    """
    try:
        success = db.delete_device(device_id)
        if success:
            return ApiResponse(
                code=0,
                message="设备删除成功",
                data={"success": True}
            )
        else:
            return ApiResponse(
                code=1,
                message="设备删除失败",
                data={"success": False}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除设备失败: {str(e)}")


@router.post("/test-connection", response_model=ApiResponse, summary="测试连接")
def test_connection(request: TestConnectionRequest):
    """测试设备SSH连接

    Args:
        request: 设备连接信息，可传device_id或完整连接信息

    Returns:
        连接测试结果
    """
    try:
        password = request.password
        ip = request.ip
        port = request.port
        username = request.username

        # 如果传了device_id，从数据库取密码
        if request.device_id is not None:
            device = db.get_device(request.device_id)
            if device:
                ip = device["ip"]
                port = device["port"]
                username = device["username"]
                encrypted_pwd = device["password"]
                from app.crypto_utils import crypto
                password = crypto.decrypt(encrypted_pwd) if crypto.is_encrypted(encrypted_pwd) else encrypted_pwd

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(
            ip,
            port=port,
            username=username,
            password=password,
            timeout=10
        )
        client.close()

        return ApiResponse(
            code=0,
            message="连接成功",
            data={"success": True}
        )
    except Exception as e:
        return ApiResponse(
            code=1,
            message=f"连接失败: {str(e)}",
            data={"success": False}
        )

# -*- coding: utf-8 -*-
"""
命令模板相关API路由
"""
from typing import List
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    TemplateInfo,
    TemplateCommandsResponse,
    SaveCustomTemplateRequest,
    ApiResponse
)
from app.database import db

router = APIRouter(prefix="/api/templates", tags=["命令模板管理"])


@router.get("/list", response_model=ApiResponse, summary="获取模板列表")
def get_template_list():
    """获取所有命令模板列表"""
    try:
        templates = db.get_template_list()
        return ApiResponse(
            code=0,
            message="success",
            data={"templates": templates}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模板列表失败: {str(e)}")


@router.get("/commands", response_model=ApiResponse, summary="获取模板命令")
def get_template_commands(template_name: str, manufacturer: str, device_type: str = ''):
    """获取指定模板和厂商的命令列表

    Args:
        template_name: 模板名称
        manufacturer: 设备厂商
        device_type: 设备类型（FW/SW/RT/IPS/WAF/DDOS/WOC/other）

    Returns:
        模板命令列表
    """
    try:
        commands = db.get_template_commands(template_name, manufacturer, device_type or '')
        return ApiResponse(
            code=0,
            message="success",
            data={
                "template_name": template_name,
                "manufacturer": manufacturer,
                "device_type": device_type or '',
                "commands": commands
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模板命令失败: {str(e)}")


@router.get("/manufacturers", response_model=ApiResponse, summary="获取模板支持的厂商列表")
def get_template_manufacturers(template_name: str, device_type: str = ''):
    """获取指定模板支持的厂商列表

    Args:
        template_name: 模板名称
        device_type: 设备类型（可选）

    Returns:
        厂商列表
    """
    try:
        manufacturers = db.get_template_manufacturers(template_name, device_type or '')
        return ApiResponse(
            code=0,
            message="success",
            data={"manufacturers": manufacturers}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取厂商列表失败: {str(e)}")


@router.post("/custom/save", response_model=ApiResponse, summary="保存自定义模板")
def save_custom_template(request: SaveCustomTemplateRequest):
    """保存自定义模板命令

    Args:
        request: 保存自定义模板请求

    Returns:
        保存结果
    """
    try:
        success = db.save_custom_template(
            request.template_name,
            request.manufacturer,
            request.commands,
            request.device_type or ''
        )
        if success:
            return ApiResponse(
                code=0,
                message="自定义模板保存成功",
                data={"success": True}
            )
        else:
            return ApiResponse(
                code=1,
                message="自定义模板保存失败",
                data={"success": False}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存自定义模板失败: {str(e)}")

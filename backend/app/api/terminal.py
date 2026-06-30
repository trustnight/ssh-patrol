# -*- coding: utf-8 -*-
"""
终端连接历史 API
"""
from fastapi import APIRouter, HTTPException
from app.database import db

router = APIRouter(prefix="/api/terminal", tags=["终端历史"])


@router.get("/history", summary="获取终端连接历史")
def get_history():
    """返回最近 20 条连接记录"""
    try:
        history = db.get_terminal_history(limit=20)
        return {"code": 0, "data": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.post("/history", summary="保存终端连接")
def save_history(ip: str, port: str = "22", username: str = "", protocol: str = "ssh"):
    """保存一条连接历史"""
    try:
        db.add_terminal_history(ip, port, username, protocol)
        return {"code": 0, "message": "已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存历史失败: {str(e)}")


@router.delete("/history", summary="清空终端连接历史")
def clear_history():
    """清空所有连接历史"""
    try:
        db.clear_terminal_history()
        return {"code": 0, "message": "已清空"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空历史失败: {str(e)}")

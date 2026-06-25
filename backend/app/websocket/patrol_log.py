# -*- coding: utf-8 -*-
"""
实时巡检日志 WebSocket 实现
"""
import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.task_manager import task_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/patrol/{task_id}")
async def patrol_log_ws(websocket: WebSocket, task_id: str):
    """实时巡检日志WebSocket接口

    Args:
        websocket: WebSocket连接对象
        task_id: 巡检任务ID
    """
    await websocket.accept()

    task = task_manager.get_task(task_id)
    if not task:
        await websocket.send_json({
            "type": "error",
            "message": f"任务不存在: {task_id}"
        })
        await websocket.close()
        return

    log_queue = asyncio.Queue()
    heartbeat_task = None
    receive_task = None

    def log_callback(log_text):
        """日志回调函数，将日志放入队列"""
        try:
            log_queue.put_nowait(log_text)
        except Exception:
            pass

    try:
        task_manager.register_log_callback(task_id, log_callback)

        history_logs = task_manager.get_logs(task_id)
        if history_logs:
            full_history = "".join(history_logs)
            try:
                await websocket.send_json({"type": "history", "data": full_history})
            except Exception:
                pass

        current_task = task_manager.get_task(task_id)
        if current_task:
            try:
                await websocket.send_json({
                    "type": "status",
                    "data": {
                        "task_id": current_task["task_id"],
                        "status": current_task["status"],
                        "total_devices": current_task["total_devices"],
                        "success_count": current_task["success_count"],
                        "fail_count": current_task["fail_count"],
                        "progress": current_task["progress"]
                    }
                })
            except Exception:
                pass

        async def heartbeat_loop():
            """心跳检测循环"""
            while True:
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": 0
                    })
                    await asyncio.sleep(30)
                except Exception:
                    break

        async def receive_loop():
            """接收客户端消息循环"""
            while True:
                try:
                    message = await websocket.receive_text()
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        if msg_type == "pong":
                            continue
                        elif msg_type == "get_status":
                            current = task_manager.get_task(task_id)
                            if current:
                                await websocket.send_json({
                                    "type": "status",
                                    "data": {
                                        "task_id": current["task_id"],
                                        "status": current["status"],
                                        "total_devices": current["total_devices"],
                                        "success_count": current["success_count"],
                                        "fail_count": current["fail_count"],
                                        "progress": current["progress"]
                                    }
                                })
                    except json.JSONDecodeError:
                        continue
                except WebSocketDisconnect:
                    break
                except Exception:
                    break

        async def safe_send(msg):
            """安全发送消息，连接已关闭时静默忽略"""
            try:
                await websocket.send_json(msg)
            except Exception:
                pass

        heartbeat_task = asyncio.create_task(heartbeat_loop())
        receive_task = asyncio.create_task(receive_loop())

        while True:
            try:
                log_text = await asyncio.wait_for(log_queue.get(), timeout=1.0)
                await safe_send({"type": "log", "data": log_text})

                current = task_manager.get_task(task_id)
                if current and current["status"] in ("completed", "failed"):
                    await safe_send({
                        "type": "status",
                        "data": {
                            "task_id": current["task_id"],
                            "status": current["status"],
                            "total_devices": current["total_devices"],
                            "success_count": current["success_count"],
                            "fail_count": current["fail_count"],
                            "progress": current["progress"]
                        }
                    })
                    break

            except asyncio.TimeoutError:
                current = task_manager.get_task(task_id)
                if current and current["status"] in ("completed", "failed"):
                    await safe_send({
                        "type": "status",
                        "data": {
                            "task_id": current["task_id"],
                            "status": current["status"],
                            "total_devices": current["total_devices"],
                            "success_count": current["success_count"],
                            "fail_count": current["fail_count"],
                            "progress": current["progress"]
                        }
                    })
                    break
                continue

            except WebSocketDisconnect:
                logger.info(f"巡检日志WebSocket断开: {task_id}")
                break

    except WebSocketDisconnect:
        logger.info(f"巡检日志WebSocket断开: {task_id}")

    except Exception as e:
        logger.error(f"巡检日志WebSocket异常: {task_id} - {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass

    finally:
        task_manager.unregister_log_callback(task_id, log_callback)

        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        if receive_task and not receive_task.done():
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass

        logger.info(f"巡检日志WebSocket连接已关闭: {task_id}")

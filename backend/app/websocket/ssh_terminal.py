# -*- coding: utf-8 -*-
"""
Web SSH 终端 WebSocket 实现
支持直接传参连接 或 通过 device_id 从数据库获取设备信息连接
"""
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

import asyncssh

from app.crypto_utils import crypto
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/ssh")
async def ssh_terminal(
    websocket: WebSocket,
    device_id: int = Query(None, description="设备ID（与 ip/username/password 二选一）"),
    ip: str = Query(None, description="设备IP地址"),
    port: int = Query(22, description="SSH端口"),
    username: str = Query(None, description="用户名"),
    password: str = Query(None, description="密码"),
    encoding: str = Query("utf-8", description="编码方式")
):
    """Web SSH终端WebSocket接口

    支持两种连接方式：
    1. 通过 device_id：自动从数据库获取设备信息（密码自动解密）
    2. 直接传 ip/username/password

    Args:
        websocket: WebSocket连接对象
        device_id: 设备ID（从数据库获取连接信息）
        ip: 设备IP地址
        port: SSH端口
        username: 用户名
        password: 密码（支持加密格式）
        encoding: 编码方式
    """
    await websocket.accept()

    # 如果传了 device_id，从数据库获取设备信息
    if device_id is not None:
        device = db.get_device(device_id)
        if not device:
            await websocket.send_text("\r\n\x1b[31m设备不存在\x1b[0m\r\n")
            await websocket.close()
            return

        ip = device["ip"]
        port = device["port"]
        username = device["username"]
        password = device["password"]  # 数据库中已是加密的
        logger.info(f"SSH连接请求(device_id={device_id}): {ip}:{port}, 用户: {username}")

    if not ip or not username or not password:
        await websocket.send_text("\r\n\x1b[31m缺少连接参数（ip/username/password）\x1b[0m\r\n")
        await websocket.close()
        return

    conn = None
    process = None
    read_task = None

    try:
        logger.info(f"SSH连接: {ip}:{port}, 用户: {username}")

        decrypted_password = crypto.decrypt(password) if crypto.is_encrypted(password) else password

        conn = await asyncssh.connect(
            ip,
            port=port,
            username=username,
            password=decrypted_password,
            known_hosts=None,
            encoding=encoding
        )

        logger.info(f"SSH连接成功: {ip}:{port}")

        process = await conn.create_process(
            term_type='xterm-256color',
            term_size=(80, 24)
        )

        # 发送连接成功标记（前端收到后才显示"已连接"状态）
        await websocket.send_text("__SSH_CONNECTED__")

        async def read_output():
            """读取SSH输出并发送到前端"""
            try:
                while True:
                    data = await process.stdout.read(4096)
                    if not data:
                        break
                    await websocket.send_text(data)
            except Exception as e:
                logger.debug(f"读取SSH输出异常: {e}")

        read_task = asyncio.create_task(read_output())

        while True:
            try:
                message = await websocket.receive_text()

                if message.startswith("resize:"):
                    parts = message[len("resize:"):].split(",")
                    if len(parts) == 2:
                        try:
                            cols = int(parts[0])
                            rows = int(parts[1])
                            if process and process.channel:
                                process.channel.resize_pty(width=cols, height=rows)
                                logger.debug(f"终端窗口大小调整: {cols}x{rows}")
                        except (ValueError, Exception) as e:
                            logger.debug(f"调整窗口大小失败: {e}")
                elif message == "__PING__":
                    # 心跳，忽略
                    pass
                else:
                    if process and process.stdin:
                        process.stdin.write(message)
                        await process.stdin.drain()

            except WebSocketDisconnect:
                logger.info(f"WebSocket断开连接: {ip}:{port}")
                break

    except asyncssh.misc.PermissionDenied as e:
        error_msg = f"认证失败: {str(e)}"
        logger.warning(f"SSH认证失败: {ip}:{port} - {error_msg}")
        try:
            await websocket.send_text(f"\r\n\x1b[31m{error_msg}\x1b[0m\r\n")
        except Exception:
            pass

    except asyncssh.misc.ConnectionLost as e:
        error_msg = f"连接丢失: {str(e)}"
        logger.warning(f"SSH连接丢失: {ip}:{port} - {error_msg}")
        try:
            await websocket.send_text(f"\r\n\x1b[31m{error_msg}\x1b[0m\r\n")
        except Exception:
            pass

    except (ConnectionRefusedError, OSError) as e:
        error_msg = f"连接失败: {str(e)}"
        logger.warning(f"SSH连接失败: {ip}:{port} - {error_msg}")
        try:
            await websocket.send_text(f"\r\n\x1b[31m{error_msg}\x1b[0m\r\n")
        except Exception:
            pass

    except Exception as e:
        error_msg = f"连接错误: {str(e)}"
        logger.error(f"SSH连接异常: {ip}:{port} - {error_msg}", exc_info=True)
        try:
            await websocket.send_text(f"\r\n\x1b[31m{error_msg}\x1b[0m\r\n")
        except Exception:
            pass

    finally:
        if read_task and not read_task.done():
            read_task.cancel()
            try:
                await read_task
            except asyncio.CancelledError:
                pass

        if process:
            try:
                process.close()
            except Exception:
                pass

        if conn:
            try:
                conn.close()
                await conn.wait_closed()
            except Exception:
                pass

        logger.info(f"SSH连接已关闭: {ip}:{port}")

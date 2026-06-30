# -*- coding: utf-8 -*-
"""
简易 Telnet 客户端（兼容 Python 3.13+，不依赖已废弃的 telnetlib）
"""
import asyncio
import socket
import time
import re

# Telnet 协议常量
IAC = 255
DONT = 254
DO = 253
WONT = 252
WILL = 251
SB = 250
SE = 240

# Telnet 选项
TTYPE = 24
NAWS = 31
ECHO = 1
SGA = 3  # Suppress Go Ahead


class SimpleTelnet:
    """简易 Telnet 客户端，支持基础协议协商和命令执行"""

    def __init__(self, host, port=23, timeout=15):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self._buffer = b""

    def connect(self):
        """连接并完成初始协商"""
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.settimeout(self.timeout)
        self._negotiate()

    def close(self):
        """关闭连接"""
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def _negotiate(self):
        """处理 Telnet 协商"""
        self.sock.settimeout(0.5)
        time.sleep(0.3)
        try:
            while True:
                data = self.sock.recv(4096)
                if not data:
                    break
                response = SimpleTelnet._handle_negotiation(data)
                if response:
                    self.sock.sendall(response)
        except socket.timeout:
            pass
        except OSError:
            pass
        self.sock.settimeout(self.timeout)

    @staticmethod
    def _handle_negotiation(data):
        """处理单个协商数据包（静态方法，不依赖实例状态）
        
        返回 IAC 协商响应字节串。
        """
        if IAC not in data:
            return b""
        i = 0
        response = b""
        while i < len(data):
            if data[i] == IAC and i + 1 < len(data):
                cmd = data[i + 1]
                if cmd in (DO, DONT):
                    opt = data[i + 2] if i + 2 < len(data) else 0
                    # 拒绝：WONT for DO, WONT for DONT
                    response += bytes([IAC, WONT, opt])
                    i += 3
                elif cmd in (WILL, WONT):
                    opt = data[i + 2] if i + 2 < len(data) else 0
                    # 接受 WILL SGA，拒绝其他
                    if cmd == WILL and opt == SGA:
                        response += bytes([IAC, DO, SGA])
                    else:
                        response += bytes([IAC, DONT, opt])
                    i += 3
                elif cmd in (SB, SE):
                    # 子协商，跳过
                    i += 2
                else:
                    i += 2
            else:
                # 普通数据，跳过（由 read/read_until 统一处理）
                i += 1
        return response

    def write(self, data):
        """发送数据"""
        if isinstance(data, str):
            data = data.encode("utf-8", errors="ignore")
        self.sock.sendall(data)

    def read_until(self, expected, timeout=30):
        """读取直到遇到期望的字符串"""
        if isinstance(expected, str):
            expected = expected.encode("utf-8", errors="ignore")

        deadline = time.time() + timeout
        result = self._buffer
        self._buffer = b""

        try:
            self.sock.settimeout(1.0)
        except Exception:
            pass

        while time.time() < deadline:
            # 检查是否已经包含期望内容
            if expected in result:
                # 把多余的内容放回buffer
                idx = result.find(expected) + len(expected)
                self._buffer = result[idx:]
                return result[:idx].decode("utf-8", errors="ignore")

            try:
                data = self.sock.recv(4096)
                if data:
                    result += data
                else:
                    break
            except socket.timeout:
                continue
            except OSError:
                break

        self._buffer = b""
        return result.decode("utf-8", errors="ignore")

    def read_very_eager(self):
        """读取所有立即可用的数据"""
        self.sock.settimeout(0.3)
        result = self._buffer
        self._buffer = b""
        try:
            while True:
                data = self.sock.recv(4096)
                if not data:
                    break
                result += data
        except socket.timeout:
            pass
        except OSError:
            pass
        self.sock.settimeout(self.timeout)
        return result.decode("utf-8", errors="ignore")


class AsyncTelnetClient:
    """异步 Telnet 客户端（用于 WebSocket 终端）"""

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self._closed = False

    @classmethod
    async def connect(cls, host, port=23, timeout=15):
        """异步连接"""
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        client = cls(reader, writer)
        await client._negotiate()
        return client

    async def _negotiate(self):
        """处理 Telnet 协商（快速版：0.15s 超时，足够完成协商且不阻塞）"""
        import asyncio as aio
        try:
            # 先发一轮 IAC DO TERMINAL_TYPE 主动协商
            self.writer.write(bytes([IAC, DO, TTYPE]))
            await self.writer.drain()
            # 快速收集协商响应，最多 0.15s
            while True:
                data = await aio.wait_for(self.reader.read(4096), timeout=0.15)
                if not data:
                    break
                response = SimpleTelnet._handle_negotiation(data)
                if response:
                    self.writer.write(response)
                    await self.writer.drain()
        except (aio.TimeoutError, OSError):
            pass

    async def read(self, n=4096):
        """读取数据"""
        import asyncio as aio
        try:
            data = await aio.wait_for(self.reader.read(n), timeout=0.2)
            if data:
                # 过滤 IAC 协商数据
                clean = b""
                i = 0
                while i < len(data):
                    if data[i] == IAC and i + 1 < len(data):
                        cmd = data[i + 1]
                        if cmd in (DO, DONT, WILL, WONT):
                            i += 3
                        elif cmd in (SB, SE):
                            i += 2
                        else:
                            i += 2
                    else:
                        clean += bytes([data[i]])
                        i += 1
                return clean if clean else None
            return data  # None 表示连接关闭
        except aio.TimeoutError:
            return b""
        except OSError:
            return None

    async def write(self, data):
        """发送数据"""
        if isinstance(data, str):
            data = data.encode("utf-8", errors="ignore")
        self.writer.write(data)
        await self.writer.drain()

    async def close(self):
        """关闭连接"""
        if not self._closed:
            self._closed = True
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass

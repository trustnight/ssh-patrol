# -*- coding: utf-8 -*-
"""
SSH终端模块
使用 asyncssh 实现异步SSH连接
"""
import asyncio
from re import T
import asyncssh
import tkinter as tk
from tkinter import ttk
import threading


class SSHWindow(tk.Toplevel):
    """SSH终端窗口 - 使用 asyncssh 实现"""
    
    # 类级别的debug开关，可以通过 SSHWindow.DEBUG = True 开启
    DEBUG = True
    
    def __init__(self, ip, port, user, password, x_pos=None, y_pos=None, encoding="utf-8", debug=None):
        super().__init__()
        self.title(f"SSH终端 - {ip}:{port}")
        
        # 如果传入了debug参数则使用，否则使用类级别的设置
        self.debug = debug if debug is not None else self.DEBUG
        
        window_width = 1000
        window_height = 700
        
        if x_pos is not None and y_pos is not None:
            self.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        else:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password
        self.encoding = encoding
        
        # asyncssh 连接对象
        self.conn = None
        self.process = None
        self.stdin = None
        self.stdout = None
        self.stderr = None
        
        self.running = False
        self.loop = None
        self.thread = None
        
        self.setup_ui()
        self.connect_ssh()
    
    def _debug_log(self, title, data=None):
        """输出调试日志"""
        if not self.debug:
            return
        
        print(f"\n{'='*50}")
        print(f"[{title}]")
        if data is not None:
            if isinstance(data, str):
                print(f"  原始数据: {repr(data)}")
                # 转换为字节显示十六进制
                try:
                    byte_data = data.encode('latin-1')
                    hex_str = ' '.join([f'{b:02x}' for b in byte_data])
                    print(f"  十六进制: {hex_str}")
                except:
                    pass
            elif isinstance(data, bytes):
                print(f"  原始字节: {data}")
                hex_str = ' '.join([f'{b:02x}' for b in data])
                print(f"  十六进制: {hex_str}")
                try:
                    print(f"  字符串: {repr(data.decode('latin-1'))}")
                except:
                    pass
        print(f"{'='*50}")
    
    def setup_ui(self):
        """设置UI"""
        self.terminal = tk.Text(
            self, 
            wrap=tk.NONE,
            font=('Consolas', 11),
            bg='black',
            fg='white',
            insertbackground='white',
            selectbackground='#444444',
            selectforeground='white',
            state=tk.NORMAL,
            padx=5,
            pady=5
        )
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        scrollbar_y = ttk.Scrollbar(self.terminal, orient=tk.VERTICAL, command=self.terminal.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.terminal.config(yscrollcommand=scrollbar_y.set)
        
        scrollbar_x = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.terminal.xview)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.terminal.config(xscrollcommand=scrollbar_x.set)
        
        self.status_bar = ttk.Label(self, text="未连接", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.encoding_label = ttk.Label(self, text=f"编码: {self.encoding}", relief=tk.SUNKEN, anchor=tk.W)
        self.encoding_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.terminal.focus_set()
        self.terminal.bind('<Key>', self.on_key_press)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def connect_ssh(self):
        """启动异步SSH连接"""
        self.update_status(f"正在连接 {self.ip}:{self.port}...")
        
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()
    
    def _run_async_loop(self):
        """在线程中运行异步事件循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._ssh_session())
        except Exception as e:
            self.after(0, lambda: self.append_text(f"\n连接错误: {str(e)}\n"))
            self.after(0, lambda: self.update_status("连接失败"))
    
    async def _ssh_session(self):
        """SSH会话主协程"""
        try:
            self.conn = await asyncssh.connect(
                self.ip,
                port=self.port,
                username=self.user,
                password=self.password,
                known_hosts=None,
                encoding=self.encoding
            )
            
            self.running = True
            self.after(0, lambda: self.update_status(f"已连接到 {self.ip}:{self.port}"))
            
            self.process = await self.conn.create_process(
                term_type='xterm',
                term_size=(80, 24)
            )
            
            self.stdin = self.process.stdin
            self.stdout = self.process.stdout
            self.stderr = self.process.stderr
            
            await self._read_loop()
            
        except asyncssh.Error as e:
            self.after(0, lambda: self.append_text(f"\nSSH错误: {str(e)}\n"))
            self.after(0, lambda: self.update_status("连接失败"))
        except Exception as e:
            self.after(0, lambda: self.append_text(f"\n错误: {str(e)}\n"))
            self.after(0, lambda: self.update_status("连接失败"))
    
    async def _read_loop(self):
        """异步读取SSH输出"""
        try:
            while self.running:
                try:
                    data = await asyncio.wait_for(
                        self.stdout.read(4096),
                        timeout=0.1
                    )
                    if data:
                        self._debug_log("收到数据", data)
                        self.after(0, lambda d=data: self.append_text(d))
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    if self.running:
                        self.after(0, lambda: self.update_status(f"读取错误: {str(e)}"))
                    break
        except Exception as e:
            if self.running:
                self.after(0, lambda: self.update_status(f"读取循环错误: {str(e)}"))
    
    def append_text(self, text):
        """向终端添加文本 - 正确处理控制序列"""
        if not text or not self.running:
            return
        
        # 调试：记录原始数据
        self._debug_log("append_text 原始数据", text)
        
        # 预处理：检测退格+空格+退格序列（服务器回显的退格处理）
        # 模式1: \x1b[K + 退格/换行（tab补全）- 删除整行
        # 模式2: 多个退格 + 多个空格 + 多个退格（Ctrl+C中断，至少5个退格）- 删除整行
        # 模式3: 单个或多个退格 + 空格 + 退格（退格回显）- 删除对应数量的字符
        import re
        
        # 模式1: \x1b[K 开头的覆盖
        overwrite_pattern1 = r'\x1b\[K[\x08\r\n]*'
        match1 = re.search(overwrite_pattern1, text)
        
        if match1:
            # 找到覆盖行模式，删除当前行内容
            try:
                current_line = self.terminal.get("end-1l linestart", "end-1l lineend")
                if current_line:
                    self.terminal.delete("end-1l linestart", "end-1l lineend")
            except:
                pass
            text = text[match1.end():]
            self._debug_log("覆盖行处理后的数据(模式1)", text)
        
        # 处理退格+空格+退格序列（服务器回显的退格）
        # 格式: \x08+\s+\x08+ （退格、空格、退格数量相同）
        backspace_pattern = r'^(\x08+)(\s+)(\x08+)'
        bs_match = re.search(backspace_pattern, text)
        if bs_match:
            bs_count = len(bs_match.group(1))
            space_count = len(bs_match.group(2))
            bs2_count = len(bs_match.group(3))
            
            if bs_count >= 5 and bs_count == space_count == bs2_count:
                # 模式2: 大量退格（Ctrl+C），删除整行
                try:
                    current_line = self.terminal.get("end-1l linestart", "end-1l lineend")
                    if current_line:
                        self.terminal.delete("end-1l linestart", "end-1l lineend")
                except:
                    pass
                text = text[bs_match.end():]
                self._debug_log("覆盖行处理后的数据(模式2-Ctrl+C)", text)
            else:
                # 模式3: 普通退格回显，删除对应数量的字符
                try:
                    for _ in range(bs_count):
                        self.terminal.delete("end-2c", tk.END)
                except:
                    pass
                text = text[bs_match.end():]
                self._debug_log(f"退格处理后的数据(删除{bs_count}个字符)", text)
        
        i = 0
        while i < len(text):
            # 检查是否是ANSI转义序列 CSI序列 \x1b[...
            if i < len(text) - 1 and text[i] == '\x1b' and text[i+1] == '[':
                j = i + 2
                # 收集参数字符（数字、分号、问号等）
                while j < len(text) and text[j] in '0123456789;?':
                    j += 1
                if j < len(text):
                    cmd = text[j]
                    param_str = text[i+2:j]
                    
                    # 解析参数
                    if cmd == 'D':  # 光标左移
                        # 提取数字部分
                        import re
                        nums = re.findall(r'\d+', param_str)
                        n = int(nums[0]) if nums else 1
                        try:
                            self.terminal.delete(f"end-{n+1}c", tk.END)
                        except:
                            pass
                    elif cmd == 'C':  # 光标右移
                        pass
                    elif cmd == 'K':  # 清除行
                        # \x1b[K 或 \x1b[0K 清除到行尾
                        # \x1b[1K 清除到行首
                        # \x1b[2K 清除整行
                        # 注意：\x1b[K + 退格的模式已在预处理中处理
                        if param_str == '1':
                            # 清除到行首
                            try:
                                self.terminal.delete("end-1l linestart", "end-1l lineend")
                            except:
                                pass
                        elif param_str == '2':
                            # 清除整行
                            try:
                                self.terminal.delete("end-1l linestart", "end-1l lineend")
                            except:
                                pass
                        # \x1b[K (param_str为''或'0') 已在预处理中处理，这里忽略
                    elif cmd in ('A', 'B'):  # 光标上下移动
                        pass
                    elif cmd == 'H' or cmd == 'f':  # 光标定位
                        pass
                    elif cmd == 'J':  # 清除屏幕
                        if param_str in ('', '0', '2'):
                            try:
                                self.terminal.delete(1.0, tk.END)
                            except:
                                pass
                    elif cmd == 'm':  # 颜色/样式设置
                        pass
                    i = j + 1
                    continue
            
            char = text[i]
            if char == '\x08' or char == '\b':  # 退格
                try:
                    # 获取当前行内容
                    current_line = self.terminal.get("end-1l linestart", "end-1l lineend")
                    # 查找常见提示符位置 (# > $ % 等)
                    # 提示符通常在行尾，格式如 "hostname# " 或 "hostname> "
                    # 如果当前行只剩提示符（以 # > $ % 结尾且后面没有内容），则不删除
                    import re
                    # 匹配提示符模式：任意字符后跟 # > $ % 和可选空格
                    prompt_match = re.search(r'[#>\$%]\s*$', current_line)
                    if prompt_match:
                        # 找到提示符，检查提示符后面是否还有用户输入
                        prompt_end_pos = prompt_match.end()
                        if prompt_end_pos >= len(current_line):
                            # 提示符后面没有内容了，不删除
                            pass
                        else:
                            # 提示符后面还有内容，可以删除
                            self.terminal.delete("end-2c", tk.END)
                    else:
                        # 没找到提示符，正常删除
                        self.terminal.delete("end-2c", tk.END)
                except:
                    pass
            elif char == '\x7f':  # DEL键
                try:
                    current_line = self.terminal.get("end-1l linestart", "end-1l lineend")
                    import re
                    prompt_match = re.search(r'[#>\$%]\s*$', current_line)
                    if prompt_match:
                        prompt_end_pos = prompt_match.end()
                        if prompt_end_pos >= len(current_line):
                            pass
                        else:
                            self.terminal.delete("end-2c", tk.END)
                    else:
                        self.terminal.delete("end-2c", tk.END)
                except:
                    pass
            elif char == '\r':
                if i + 1 < len(text) and text[i+1] == '\n':
                    self.terminal.insert(tk.END, '\n')
                    i += 1
            elif char == '\n':
                self.terminal.insert(tk.END, '\n')
            elif char == '\x07':  # 响铃字符 BEL
                pass  # 忽略
            else:
                self.terminal.insert(tk.END, char)
            i += 1
        
        self.terminal.see(tk.END)
        
        try:
            line_count = int(self.terminal.index(tk.END).split('.')[0])
            if line_count > 5000:
                self.terminal.delete(1.0, f"{line_count - 4000}.0")
        except:
            pass
    
    def on_key_press(self, event):
        """处理键盘输入"""
        if not self.running or not self.stdin:
            return "break"
        
        key = event.keysym
        char = event.char
        
        if key == 'Return':
            self._send_data('\r')
        elif key == 'BackSpace':
            self._send_data('\b')
        elif key == 'Tab':
            self._send_data('\t')
        elif key == 'Escape':
            self._send_data('\x1b')
        elif key == 'Up':
            self._send_data('\x1b[A')
        elif key == 'Down':
            self._send_data('\x1b[B')
        elif key == 'Right':
            self._send_data('\x1b[C')
        elif key == 'Left':
            self._send_data('\x1b[D')
        elif key == 'Home':
            self._send_data('\x1b[H')
        elif key == 'End':
            self._send_data('\x1b[F')
        elif key == 'Delete':
            self._send_data('\x1b[3~')
        elif key == 'Insert':
            self._send_data('\x1b[2~')
        elif key == 'Prior':
            self._send_data('\x1b[5~')
        elif key == 'Next':
            self._send_data('\x1b[6~')
        elif char and ord(char) >= 32:
            self._send_data(char)
        elif char and ord(char) == 3:
            self._send_data('\x03')
        elif char and ord(char) == 4:
            self._send_data('\x04')
        elif char and ord(char) == 26:
            self._send_data('\x1a')
        elif char and ord(char) == 1:
            self._send_data('\x01')
        elif char and ord(char) == 5:
            self._send_data('\x05')
        elif char and ord(char) == 12:
            self._send_data('\x0c')
        elif char and ord(char) == 8:
            self._send_data('\b')
        elif char and ord(char) == 127:
            self._send_data('\b')
        
        return "break"
    
    def _send_data(self, data):
        """发送数据到SSH服务器"""
        self._debug_log("发送数据", data)
        if self.loop and self.stdin:
            asyncio.run_coroutine_threadsafe(
                self._async_send(data),
                self.loop
            )
    
    async def _async_send(self, data):
        """异步发送数据"""
        try:
            self.stdin.write(data)
            await self.stdin.drain()
        except Exception as e:
            print(f"发送错误: {e}")
    
    def disconnect(self):
        """断开连接"""
        self.running = False
        
        if self.process:
            try:
                self.process.close()
            except:
                pass
        
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        
        if self.loop:
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except:
                pass
        
        self.update_status("已断开连接")
    
    def update_status(self, text):
        """更新状态栏"""
        try:
            self.status_bar.config(text=text)
        except:
            pass
    
    def show_disconnected_message(self):
        """显示断开连接的提示信息"""
        self.append_text("\n\n[连接已断开] 按回车键重连...\n")
        self.update_status("连接已断开")
    
    def on_close(self):
        """窗口关闭事件"""
        self.disconnect()
        try:
            self.destroy()
        except:
            pass

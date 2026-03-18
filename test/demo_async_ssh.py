# -*- coding: utf-8 -*-
"""
异步SSH终端 Demo
使用 asyncssh 库实现更高效的异步SSH连接
"""
import asyncio
import asyncssh
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys


class AsyncSSHWindow(tk.Toplevel):
    """使用 asyncssh 的异步SSH终端窗口"""
    
    # 类级别的debug开关
    DEBUG = True  # Demo默认开启调试
    
    def __init__(self, ip, port, user, password, encoding="utf-8", debug=None):
        super().__init__()
        self.title(f"异步SSH终端 - {ip}:{port}")
        
        # 如果传入了debug参数则使用，否则使用类级别的设置
        self.debug = debug if debug is not None else self.DEBUG
        
        # 窗口居中显示
        window_width = 1000
        window_height = 700
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
        
        # SSH连接对象
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
        # 终端显示区域
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
        
        # 滚动条
        scrollbar_y = ttk.Scrollbar(self.terminal, orient=tk.VERTICAL, command=self.terminal.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.terminal.config(yscrollcommand=scrollbar_y.set)
        
        # 状态栏
        self.status_bar = ttk.Label(self, text="未连接", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 绑定键盘事件
        self.terminal.bind('<Key>', self.on_key_press)
        self.terminal.focus_set()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def connect_ssh(self):
        """启动异步SSH连接"""
        self.update_status(f"正在连接 {self.ip}:{self.port}...")
        
        # 在新线程中运行异步事件循环
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
            # 建立SSH连接
            self.conn = await asyncssh.connect(
                self.ip,
                port=self.port,
                username=self.user,
                password=self.password,
                known_hosts=None,  # 不检查known_hosts
                encoding=self.encoding
            )
            
            self.running = True
            self.after(0, lambda: self.update_status(f"已连接到 {self.ip}:{self.port}"))
            
            # 创建交互式shell会话（使用更通用的终端类型）
            self.process = await self.conn.create_process(
                term_type='vt100',  # 使用更通用的终端类型，兼容性更好
                term_size=(80, 24)
            )
            
            self.stdin = self.process.stdin
            self.stdout = self.process.stdout
            self.stderr = self.process.stderr
            
            # 启动读取任务
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
                # 异步读取输出（非阻塞）
                try:
                    # 设置超时，避免永久阻塞
                    data = await asyncio.wait_for(
                        self.stdout.read(4096),
                        timeout=0.1
                    )
                    if data:
                        self._debug_log("收到数据", data)
                        self.after(0, lambda d=data: self.append_text(d))
                except asyncio.TimeoutError:
                    # 超时后继续循环
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
        
        self._debug_log("append_text 原始数据", text)
        
        import re
        
        i = 0
        while i < len(text):
            # 检查是否是ANSI转义序列
            if i < len(text) - 1 and text[i] == '\x1b' and text[i+1] == '[':
                # 找到序列结束字符
                j = i + 2
                while j < len(text) and text[j].isdigit():
                    j += 1
                if j < len(text):
                    cmd = text[j]
                    param = text[i+2:j] if j > i+2 else "1"
                    n = int(param) if param.isdigit() else 1
                    
                    # 处理光标移动
                    if cmd == 'D':  # 左移
                        # 删除最后n个字符（模拟光标回退并覆盖）
                        try:
                            self.terminal.delete(f"end-{n+1}c", tk.END)
                        except:
                            pass
                    elif cmd == 'C':  # 右移
                        pass  # tk.Text不支持光标移动，忽略
                    elif cmd == 'K':  # 清除行
                        if param == '':  # \x1b[K 清除到行尾
                            pass
                        elif param == '1':  # \x1b[1K 清除到行首
                            pass
                        elif param == '2':  # \x1b[2K 清除整行
                            pass
                    # 其他控制序列忽略
                    i = j + 1
                    continue
            
            # 处理普通字符
            char = text[i]
            if char == '\x08' or char == '\b':  # 退格
                try:
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
                pass  # 忽略，不显示
            else:
                self.terminal.insert(tk.END, char)
            i += 1
        
        self.terminal.see(tk.END)
        
        # 限制行数
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
        
        # 使用 after 将异步操作调度到事件循环
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
        elif key == 'Delete':
            self._send_data('\x1b[3~')
        elif char and ord(char) >= 32:
            self._send_data(char)
        elif char and ord(char) == 3:  # Ctrl+C
            self._send_data('\x03')
        elif char and ord(char) == 4:  # Ctrl+D
            self._send_data('\x04')
        
        return "break"
    
    def _send_data(self, data):
        """发送数据到SSH服务器"""
        self._debug_log("发送数据", data)
        if self.loop and self.stdin:
            # 使用 call_soon_threadsafe 在线程安全的方式下调度协程
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
    
    def on_close(self):
        """关闭窗口"""
        self.running = False
        
        # 关闭SSH连接
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
        
        # 停止事件循环
        if self.loop:
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except:
                pass
        
        self.destroy()
    
    def _can_delete(self):
        """检查是否可以删除字符"""
        try:
            # 获取当前行内容
            last_line = self.terminal.get("end linestart", "end lineend")
            if not last_line:
                return True
            
            # 简单判断：如果行不为空且光标在行尾，允许删除
            current_pos = self.terminal.index(tk.END)
            if current_pos == self.terminal.index("end"):
                return True
            
            return False
        except:
            # 如果发生错误，默认允许删除
            return True

    def update_status(self, text):
        """更新状态栏"""
        self.status_bar.config(text=text)


class DemoApp(tk.Tk):
    """演示应用主窗口"""
    
    def __init__(self):
        super().__init__()
        self.title("异步SSH终端 Demo")
        self.geometry("400x300")
        
        # 设置窗口居中
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 300) // 2
        self.geometry(f"400x300+{x}+{y}")
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        frame = ttk.Frame(self, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 设备地址
        ttk.Label(frame, text="设备地址:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ip_var = tk.StringVar(value="192.168.113.127")
        ttk.Entry(frame, textvariable=self.ip_var, width=25).grid(row=0, column=1, pady=5)
        
        # 端口
        ttk.Label(frame, text="SSH端口:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.port_var = tk.StringVar(value="22")
        ttk.Entry(frame, textvariable=self.port_var, width=25).grid(row=1, column=1, pady=5)
        
        # 用户名
        ttk.Label(frame, text="用户名:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.user_var = tk.StringVar(value="admin")
        ttk.Entry(frame, textvariable=self.user_var, width=25).grid(row=2, column=1, pady=5)
        
        # 密码
        ttk.Label(frame, text="密码:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar(value="Admin@123456")
        ttk.Entry(frame, textvariable=self.password_var, show="*", width=25).grid(row=3, column=1, pady=5)
        
        # 编码
        ttk.Label(frame, text="编码:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.encoding_var = tk.StringVar(value="utf-8")
        ttk.Combobox(
            frame,
            textvariable=self.encoding_var,
            values=["utf-8", "gb2312", "gbk", "gb18030", "big5"],
            state="readonly",
            width=23
        ).grid(row=4, column=1, pady=5)
        
        # 连接按钮
        ttk.Button(
            frame,
            text="连接 (asyncssh)",
            command=self.connect_async
        ).grid(row=5, column=0, columnspan=2, pady=20)
        
        # 说明标签
        info_text = "使用 asyncssh 库实现异步SSH连接\n"
        info_text += "优势: 更好的性能、更简洁的代码、原生异步支持"
        ttk.Label(frame, text=info_text, wraplength=350, justify=tk.CENTER).grid(
            row=6, column=0, columnspan=2, pady=10
        )
    
    def connect_async(self):
        """使用 asyncssh 连接"""
        ip = self.ip_var.get()
        port = int(self.port_var.get())
        user = self.user_var.get()
        password = self.password_var.get()
        encoding = self.encoding_var.get()
        
        if not ip or not user or not password:
            messagebox.showerror("错误", "请填写所有必填项")
            return
        
        # 创建异步SSH窗口
        window = AsyncSSHWindow(ip, port, user, password, encoding)
        window.mainloop()


def main():
    """主函数"""
    # 检查是否安装了 asyncssh
    try:
        import asyncssh
        print(f"asyncssh 版本: {asyncssh.__version__}")
    except ImportError:
        print("请先安装 asyncssh: pip install asyncssh")
        print("注意: asyncssh 需要 Python 3.6+")
        sys.exit(1)
    
    app = DemoApp()
    app.mainloop()


if __name__ == "__main__":
    main()

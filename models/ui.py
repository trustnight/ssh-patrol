# -*- coding: utf-8 -*-
"""
UI界面模块
"""
from models.core import Core
from models.ssh_terminal import SSHWindow
from models.patrol import Patrol
from models.database import db
from models.crypto_utils import crypto
import os
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import webbrowser
import logging

# 配置日志 - 仅在需要时记录，不记录默认打开的日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ui')

class SSHPatrolPage(tk.Frame, Core):
    """SSH 巡检页面"""
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        Core.__init__(self)
        self.setup_ui()
        
    def setup_ui(self):
        """设置 UI"""
        # 主容器
        main_frame = ttk.Frame(self, padding="10", style="Bordered.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X)
        # 设备信息区域
        info_frame = ttk.LabelFrame(top_frame, text="设备信息", style="Bordered.TFrame")
        info_frame.pack(fill=tk.X, padx=(0, 10), side=tk.LEFT)
        
        # 设备地址
        ttk.Label(info_frame, text="设备地址：").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
        self.ip_var = tk.StringVar()
        self.ip_entry = ttk.Entry(info_frame, textvariable=self.ip_var, width=20)
        self.ip_entry.grid(row=0, column=1, padx=(0, 5), pady=5)
        
        # SSH端口
        ttk.Label(info_frame, text="SSH端口：").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.port_var = tk.StringVar(value="22")
        ttk.Entry(info_frame, textvariable=self.port_var, width=20).grid(row=1, column=1, padx=(0, 5), pady=5)
    
        # 用户名
        ttk.Label(info_frame, text="用 户  名：").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
        self.user_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.user_var, width=20).grid(row=2, column=1, padx=(0, 5), pady=5)
        
        # 密码
        ttk.Label(info_frame, text="密      码：").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.password_var, show="*", width=20).grid(row=3, column=1, padx=(0, 5), pady=5)
        
        # 设备厂商
        ttk.Label(info_frame, text="设备厂商：").grid(row=4, column=0, sticky=tk.E, padx=5, pady=5)
        self.manufacturer_var = tk.StringVar()
        self.manufacturer = ttk.Combobox(
            info_frame, 
            textvariable=self.manufacturer_var,
            values=[
                'Hillstone',
                'Huawei',
                'Topsec'
            ],
            state="readonly",
            width=18
        )
        self.manufacturer.current(0)
        self.manufacturer.grid(row=4, column=1, padx=5, pady=5)
        

        
        # 命令模板区域
        cmd_frame = ttk.LabelFrame(top_frame, text="命令模板", style="Bordered.TFrame")
        cmd_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(cmd_frame, text="选择命令模板：").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.cmd_template_var = tk.StringVar()
        self.cmd_template = ttk.Combobox(
            cmd_frame, 
            textvariable=self.cmd_template_var,
            values=[
                '普通巡检模板',
                '深度巡检模板',
                '自定义模板'
            ],
            state="readonly",
            width=20
        )
        self.cmd_template.current(0)
        self.cmd_template.grid(row=0, column=1, padx=5, pady=5)
        
        # 按钮区域（换行显示）
        button_frame = ttk.Frame(cmd_frame)
        button_frame.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky=tk.W)
        
        ttk.Button(button_frame, text="查看当前模板", command=self.show_cmdlist).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导入自定义模板", command=self.get_user_cmd).pack(side=tk.LEFT, padx=5)

        # 开始巡检按钮
        self.collet_button = ctk.CTkButton(
            cmd_frame, 
            text="开始巡检", 
            command=self.run_ssh,
            fg_color="#007bff",       # 正常背景色 (蓝色)
            hover_color="#0056b3",    # 悬停背景色 (深蓝)
            text_color="white",
            corner_radius=8,          # 圆角
            height=40,
            font=("微软雅黑", 12, "bold")
        )
        self.collet_button.grid(row=2, column=0, padx=10, pady=5, sticky=tk.E)
        
        # 进度区域
        progress_frame = ttk.LabelFrame(main_frame, text="执行进度", style="Bordered.TFrame", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(progress_frame, text="命令执行进度：").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var, 
            maximum=100
        )
        self.progress_bar.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        # 设置列权重，让进度条列拉伸
        progress_frame.columnconfigure(1, weight=1)
        
        self.progress_label = ttk.Label(progress_frame, text="0/0")
        self.progress_label.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        # 输出区域
        output_frame = ttk.LabelFrame(main_frame, text="日志", style="Bordered.TFrame", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.output_text = tk.Text(
            output_frame, 
            wrap=tk.WORD, 
            height=10,
            state=tk.DISABLED
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.output_text, command=self.output_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text['yscrollcommand'] = scrollbar.set
        
        # 添加使用说明按钮
        help_button = ttk.Button(main_frame, text="?", style="Help.TButton", command=self.show_help)
        help_button.pack(side=tk.TOP, anchor=tk.NE, pady=5, padx=5)
        
        # 初始化数据库
        db.newdb(self)
        
        # 设置默认焦点在设备地址输入框
        self.ip_entry.focus_set()
    
    def show_help(self):
        """显示使用说明"""
        help_text = "使用说明：\n"
        help_text += "1.程序默认内置了巡检常用的命令模板，未导入命令模板将会使用内置的命令模板；\n"
        help_text += "2.支持导入自定义的命令模板，命令必须为完整命令，仅支持文本文件导入，且必须一行一个命令；\n"
        help_text += "3.程序将会自动在程序所在目录中创建存放日志的文件夹（log），对应设备的日志将会存放在以IP方式命名的子文件夹中；\n"
        help_text += "4.每个命令输出的内容都会单独存放，也会输出一份完整的日志文件；\n"
        help_text += "5.建议使用只读权限账号进行巡检；\n"
        messagebox.showinfo("使用说明", help_text)
    
    def append_output(self, text):
        """向输出框添加文本"""
        # 使用after方法确保在主线程中更新GUI
        def update_gui():
            try:
                self.output_text.config(state=tk.NORMAL)
                self.output_text.insert(tk.END, text)
                self.output_text.see(tk.END)
                self.output_text.config(state=tk.DISABLED)
            except Exception as e:
                print(f"更新GUI错误: {e}")
        
        # 检查是否在主线程中
        if hasattr(self, 'output_text') and self.output_text.winfo_exists():
            self.output_text.after(0, update_gui)
        else:
            # 如果GUI组件不存在，直接打印
            print(text)
        
        # 保存日志到文件，只保存系统关键信息
        # 记录执行的命令，但不记录命令的输出内容
        important_keywords = ['开始', '完成', '错误', '失败', '成功登录', '巡检完成', '设备数量', '命令模板', '执行命令']
        # 排除命令输出（包含"命令输出"、"输出长度"、"后置命令输出"等）
        exclude_keywords = ['命令输出', '输出长度', '输出内容']
        is_important = any(keyword in text for keyword in important_keywords)
        is_excluded = any(keyword in text for keyword in exclude_keywords)
        is_help = '使用说明' in text or '日志分析功能说明' in text
        
        if is_important and not is_excluded and not is_help:
            try:
                import datetime
                import os
                # 创建runlog文件夹（如果不存在）
                runlog_dir = "runlog"
                if not os.path.exists(runlog_dir):
                    os.makedirs(runlog_dir)
                # 保存日志到runlog文件夹
                log_file = os.path.join(runlog_dir, f"log-{datetime.datetime.now().strftime('%Y-%m-%d')}.txt")
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(text)
            except Exception as e:
                pass
    
    def update_progress(self, current, total):
        """更新进度条"""
        # 使用after方法确保在主线程中更新GUI
        def update_gui():
            if total > 0:
                progress = (current / total) * 100
                self.progress_var.set(progress)
                self.progress_label.config(text=f"{current}/{total}")
        
        if hasattr(self, 'progress_var') and hasattr(self, 'progress_label'):
            if self.progress_label.winfo_exists():
                self.progress_label.after(0, update_gui)
    
    def show_cmdlist(self):
        """查看当前命令模板"""
        template_name = self.cmd_template_var.get()
        # 弹出厂商选择对话框
        manufacturer_window = tk.Toplevel()
        manufacturer_window.title("选择厂商")
        manufacturer_window.geometry("300x150")
        manufacturer_window.resizable(False, False)
        
        # 居中显示
        window_width = 300
        window_height = 150
        screen_width = manufacturer_window.winfo_screenwidth()
        screen_height = manufacturer_window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        manufacturer_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 厂商选择框架
        frame = ttk.Frame(manufacturer_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="请选择厂商：").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        
        # 厂商选择变量
        selected_manufacturer = tk.StringVar(value="Hillstone")
        
        # 厂商下拉框
        ttk.Combobox(
            frame,
            textvariable=selected_manufacturer,
            values=["Hillstone", "Huawei", "Topsec"],
            state="readonly",
            width=15
        ).grid(row=0, column=1, padx=5, pady=10, sticky=tk.W)
        # 确认按钮
        def confirm_manufacturer():
            manufacturer = selected_manufacturer.get()
            manufacturer_window.destroy()
            # 直接调用 _show_cmdlist_for_manufacturer 方法
            self._show_cmdlist_for_manufacturer(template_name, manufacturer)
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="确认", command=confirm_manufacturer).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=manufacturer_window.destroy).pack(side=tk.LEFT, padx=10)

    def _show_cmdlist_for_manufacturer(self, template_name, manufacturer):
        """为指定厂商显示命令模板"""
        # 清空日志区
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        cmd_list = db.get_cmd_template(template_name, manufacturer)
        
        with open('tool_cmdlist.txt', 'w', encoding='utf-8') as f:
            for cmd in cmd_list:
                f.write(cmd + '\n')
        
        webbrowser.open('tool_cmdlist.txt')
        self.append_output(f"已打开命令模板文件：{template_name} (厂商: {manufacturer})\n")

    def get_user_cmd(self):
        """导入自定义命令模板"""
        template_name = self.cmd_template_var.get()
        file_path = filedialog.askopenfilename(
            title="选择命令模板文件",
            initialdir=os.getcwd(),
            filetypes=[("Text Files", "*.txt"), ("All Files", "*")]
        )
        
        if file_path:
            # 弹出厂商选择对话框
            manufacturer_window = tk.Toplevel()
            manufacturer_window.title("选择厂商")
            manufacturer_window.geometry("300x150")
            manufacturer_window.resizable(False, False)
            
            # 居中显示
            window_width = 300
            window_height = 150
            screen_width = manufacturer_window.winfo_screenwidth()
            screen_height = manufacturer_window.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            manufacturer_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            # 厂商选择变量
            selected_manufacturer = tk.StringVar(value="Hillstone")
            
            # 厂商选择框架
            frame = ttk.Frame(manufacturer_window, padding=20)
            frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame, text="请选择厂商：").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
            
            # 厂商下拉框
            manufacturer_combobox = ttk.Combobox(
                frame,
                textvariable=selected_manufacturer,
                values=["Hillstone", "Huawei", "Topsec"],
                state="readonly",
                width=15
            )
            manufacturer_combobox.grid(row=0, column=1, padx=5, pady=10, sticky=tk.W)
            
            # 确认按钮
            def confirm_manufacturer():
                manufacturer = selected_manufacturer.get()
                manufacturer_window.destroy()
                # 直接调用 _process_custom_cmd_import 方法
                self._process_custom_cmd_import(file_path, manufacturer, template_name)
            
            button_frame = ttk.Frame(frame)
            button_frame.grid(row=1, column=0, columnspan=2, pady=10)
            
            ttk.Button(button_frame, text="确认", command=confirm_manufacturer).pack(side=tk.LEFT, padx=10)
            ttk.Button(button_frame, text="取消", command=manufacturer_window.destroy).pack(side=tk.LEFT, padx=10)

    def _process_custom_cmd_import(self, file_path, manufacturer, template_name):
        """处理自定义命令导入"""
        try:
            with open(file_path, 'r', encoding='UTF-8') as f:
                user_cmds = f.readlines()
            
            # 保存命令到数据库
            import sqlite3
            conn = sqlite3.connect('patrol.db')
            cursor = conn.cursor()
            
            # 先删除该厂商的所有命令（包括自定义和非自定义），确保完全清空
            cursor.execute('DELETE FROM commands WHERE template_name = ? AND LOWER(manufacturer) = LOWER(?)',
                       (template_name, manufacturer))
            
            # 插入新的自定义命令
            # 根据模板名称确定 template_id
            template_id = 0
            if template_name == '普通巡检模板':
                template_id = 0
            elif template_name == '深度巡检模板':
                template_id = 1
            elif template_name == '自定义模板':
                template_id = 2
            
            # 插入新命令（不进行去重处理）
            for cmd_order, cmd in enumerate(user_cmds, 1):
                cmd = cmd.strip()
                if cmd:
                    cursor.execute(
                        'INSERT INTO commands (template_id, template_name, manufacturer, command, cmd_order, is_custom) VALUES (?, ?, ?, ?, ?, ?)',
                        (template_id, template_name, manufacturer, cmd, cmd_order, 1)
                    )
            
            conn.commit()
            conn.close()
            
            # 同时添加到内存中的user_cmd列表
            i = 0
            for cmd in user_cmds:
                cmd = cmd.strip()
                if cmd:
                    i += 1
                    self.insert_data('importcmd', cmd)
            
            self.append_output(f"导入成功！导入了{i}个巡检命令,具体如下：\n")
            for cmd in user_cmds:
                cmd = cmd.strip()
                if cmd:
                    self.append_output(cmd + '\n')
            self.append_output("\n命令已保存到数据库\n")
        except Exception as e:
            self.append_output(f"导入失败：{str(e)}\n")
            import traceback
            self.append_output(f"错误详情：{traceback.format_exc()}\n")
    
    def run_ssh(self):
        """运行 SSH 巡检"""
        template_name = self.cmd_template_var.get()
        
        if template_name == '选择巡检命令模板':
            self.append_output("请先选择命令模板！\n")
            return
        
        # 获取参数
        ip = self.ip_var.get()
        port = int(self.port_var.get())
        user = self.user_var.get()
        password = self.password_var.get()
        
        # 验证参数
        if not ip:
            self.append_output("请输入设备地址！\n")
            return
        
        if not user:
            self.append_output("请输入用户名！\n")
            return
        
        if not password:
            self.append_output("请输入密码！\n")
            return
        
        # 清空日志区
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        # 禁用按钮并设置灰色背景
        self.collet_button.configure(state="disabled")
        # 保存原始背景色
        self.original_fg_color = "#007bff"
        # 设置禁用状态的灰色背景
        self.collet_button.configure(fg_color="#a0a0a0")
        
        # 获取厂商信息
        manufacturer = self.manufacturer_var.get()
        
        # 启动线程执行巡检
        t = threading.Thread(
            target=Patrol.login,
            args=(self, ip, port, user, password, template_name, False, manufacturer)
        )
        t.daemon = True
        t.start()
    
    def enable_collect_button(self):
        """启用收集按钮"""
        # 使用after方法确保在主线程中更新GUI
        def update_gui():
            self.collet_button.configure(state="normal")
            # 恢复原始背景色
            self.collet_button.configure(fg_color="#007bff")
        
        if hasattr(self, 'collet_button') and self.collet_button.winfo_exists():
            self.collet_button.after(0, update_gui)

class BatchSSHPatrolPage(tk.Frame, Core):
    """SSH 批量巡检页面"""
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        Core.__init__(self)
        self.devices = []  # 存储导入的设备列表
        self.setup_ui()
    
    def setup_ui(self):
        """设置 UI"""
        # 主容器
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建设备管理和批量操作的容器框架
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)
        
        # 设备信息区域 - 左侧
        device_frame = ttk.LabelFrame(top_frame, text="设备管理", style="Bordered.TFrame", padding="10")
        device_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        ttk.Button(
            device_frame, 
            text="导入设备信息", 
            command=self.idev
        ).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(
            device_frame, 
            text="下载导入设备模板", 
            command=self.get_template
        ).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 批量操作区域 - 右侧
        batch_frame = ttk.LabelFrame(top_frame, text="批量操作", style="Bordered.TFrame", padding="10")
        batch_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.batch_collect_button = ctk.CTkButton(
            batch_frame, 
            text="开始批量巡检", 
            command=self.collectlog,
            fg_color="#007bff",       # 正常背景色 (蓝色)
            hover_color="#0056b3",    # 悬停背景色 (深蓝)
            text_color="white",
            corner_radius=8,          # 圆角
            height=40,
            font=("微软雅黑", 12, "bold")
        )
        self.batch_collect_button.pack(side=tk.LEFT, padx=10, pady=5)
        

        
        # 命令模板区域
        cmd_frame = ttk.LabelFrame(main_frame, text="命令模板", style="Bordered.TFrame", padding="10")
        cmd_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(cmd_frame, text="选择命令模板：").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.cmd_template_var = tk.StringVar()
        self.cmd_template = ttk.Combobox(
            cmd_frame, 
            textvariable=self.cmd_template_var,
            values=[
                '普通巡检模板',
                '深度巡检模板',
                '自定义模板'
            ],
            state="readonly",
            width=20
        )
        self.cmd_template.current(0)
        self.cmd_template.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 按钮区域（换行显示）
        button_frame = ttk.Frame(cmd_frame)
        button_frame.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky=tk.W)
        
        ttk.Button(button_frame, text="查看当前模板", command=self.show_cmdlist).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导入自定义模板", command=self.icmd).pack(side=tk.LEFT, padx=5)
        
        # 设备统计区域
        stats_frame = ttk.LabelFrame(main_frame, text="设备统计", style="Bordered.TFrame", padding="10")
        stats_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(stats_frame, text="设备数量：").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.dev_total_var = tk.StringVar(value="0")
        ttk.Label(stats_frame, textvariable=self.dev_total_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(stats_frame, text="执行进度：").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.dev_progress_var = tk.StringVar(value="0")
        ttk.Label(stats_frame, textvariable=self.dev_progress_var).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(stats_frame, text="成功：").grid(row=0, column=4, sticky=tk.W, padx=5, pady=5)
        self.dev_success_var = tk.StringVar(value="0")
        ttk.Label(stats_frame, textvariable=self.dev_success_var).grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(stats_frame, text="失败：").grid(row=0, column=6, sticky=tk.W, padx=5, pady=5)
        self.dev_fail_var = tk.StringVar(value="0")
        ttk.Label(stats_frame, textvariable=self.dev_fail_var).grid(row=0, column=7, padx=5, pady=5, sticky=tk.W)
        
        # 输出区域
        output_frame = ttk.LabelFrame(main_frame, text="日志", style="Bordered.TFrame", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.output_text = tk.Text(
            output_frame, 
            wrap=tk.WORD, 
            height=10,
            state=tk.DISABLED
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.output_text, command=self.output_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text['yscrollcommand'] = scrollbar.set
        
        # 添加使用说明按钮
        help_button = ttk.Button(main_frame, text="?", style="Help.TButton", command=self.show_help)
        help_button.pack(side=tk.TOP, anchor=tk.NE, pady=5, padx=5)
    
    def show_help(self):
        """显示使用说明"""
        help_text = "使用说明：\n"
        help_text += "1.程序默认内置了巡检常用的命令模板，未导入命令模板将会使用内置的命令模板；\n"
        help_text += "2.支持导入自定义的命令模板，命令必须为完整命令，仅支持文本文件导入，且必须一行一个命令；\n"
        help_text += "3.程序将会自动在程序所在目录中创建存放日志的文件夹（log），对应设备的日志将会存放在以IP方式命名的子文件夹中；\n"
        help_text += "4.每个命令输出的内容都会单独存放，也会输出一份完整的日志文件；\n"
        help_text += "5.批量巡检功能已实现，支持同时巡检多个设备；\n"
        messagebox.showinfo("使用说明", help_text)
    
    def append_output(self, text):
        """向输出框添加文本"""
        # 使用after方法确保在主线程中更新GUI
        def update_gui():
            try:
                self.output_text.config(state=tk.NORMAL)
                self.output_text.insert(tk.END, text)
                self.output_text.see(tk.END)
                self.output_text.config(state=tk.DISABLED)
            except Exception as e:
                print(f"更新GUI错误: {e}")
        
        # 检查是否在主线程中
        if hasattr(self, 'output_text') and self.output_text.winfo_exists():
            self.output_text.after(0, update_gui)
        else:
            # 如果GUI组件不存在，直接打印
            print(text)
        
        # 保存日志到文件，只保存系统关键信息
        # 记录执行的命令，但不记录命令的输出内容
        important_keywords = ['开始', '完成', '错误', '失败', '成功登录', '巡检完成', '设备数量', '命令模板', '执行命令']
        # 排除命令输出（包含"命令输出"、"输出长度"、"后置命令输出"等）
        exclude_keywords = ['命令输出', '输出长度', '输出内容']
        is_important = any(keyword in text for keyword in important_keywords)
        is_excluded = any(keyword in text for keyword in exclude_keywords)
        is_help = '使用说明' in text or '日志分析功能说明' in text
        
        if is_important and not is_excluded and not is_help:
            try:
                import datetime
                import os
                # 创建runlog文件夹（如果不存在）
                runlog_dir = "runlog"
                if not os.path.exists(runlog_dir):
                    os.makedirs(runlog_dir)
                # 保存日志到runlog文件夹
                log_file = os.path.join(runlog_dir, f"log-{datetime.datetime.now().strftime('%Y-%m-%d')}.txt")
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(text)
            except Exception as e:
                pass
    
    def icmd(self):
        """导入命令模板"""
        template_name = self.cmd_template_var.get()
        file_path = filedialog.askopenfilename(
            title="选择命令模板文件",
            initialdir=os.getcwd(),
            filetypes=[("Text Files", "*.txt"), ("All Files", "*")]
        )
        
        if file_path:
            # 弹出厂商选择对话框
            manufacturer_window = tk.Toplevel()
            manufacturer_window.title("选择厂商")
            manufacturer_window.geometry("300x150")
            manufacturer_window.resizable(False, False)
            
            # 居中显示
            window_width = 300
            window_height = 150
            screen_width = manufacturer_window.winfo_screenwidth()
            screen_height = manufacturer_window.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            manufacturer_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            # 厂商选择变量
            selected_manufacturer = tk.StringVar(value="Hillstone")
            
            # 厂商选择框架
            frame = ttk.Frame(manufacturer_window, padding=20)
            frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame, text="请选择厂商：").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
            
            # 厂商下拉框
            manufacturer_combobox = ttk.Combobox(
                frame,
                textvariable=selected_manufacturer,
                values=["Hillstone", "Huawei", "Topsec"],
                state="readonly",
                width=15
            )
            manufacturer_combobox.grid(row=0, column=1, padx=5, pady=10, sticky=tk.W)
            
            # 确认按钮
            def confirm_manufacturer():
                manufacturer = selected_manufacturer.get()
                manufacturer_window.destroy()
                # 直接调用 _process_custom_cmd_import 方法
                self._process_custom_cmd_import(file_path, manufacturer, template_name)
            
            button_frame = ttk.Frame(frame)
            button_frame.grid(row=1, column=0, columnspan=2, pady=10)
            
            ttk.Button(button_frame, text="确认", command=confirm_manufacturer).pack(side=tk.LEFT, padx=10)
            ttk.Button(button_frame, text="取消", command=manufacturer_window.destroy).pack(side=tk.LEFT, padx=10)

    def show_cmdlist(self):
        """查看当前命令模板"""
        template_name = self.cmd_template_var.get()
        # 弹出厂商选择对话框
        manufacturer_window = tk.Toplevel()
        manufacturer_window.title("选择厂商")
        manufacturer_window.geometry("300x150")
        manufacturer_window.resizable(False, False)
        
        # 居中显示
        window_width = 300
        window_height = 150
        screen_width = manufacturer_window.winfo_screenwidth()
        screen_height = manufacturer_window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        manufacturer_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 厂商选择框架
        frame = ttk.Frame(manufacturer_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="请选择厂商：").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        
        # 厂商选择变量
        selected_manufacturer = tk.StringVar(value="Hillstone")
        
        # 厂商下拉框
        ttk.Combobox(
            frame,
            textvariable=selected_manufacturer,
            values=["Hillstone", "Huawei", "Topsec"],
            state="readonly",
            width=15
        ).grid(row=0, column=1, padx=5, pady=10, sticky=tk.W)
        # 确认按钮
        def confirm_manufacturer():
            manufacturer = selected_manufacturer.get()
            manufacturer_window.destroy()
            # 直接调用 _show_cmdlist_for_manufacturer 方法
            self._show_cmdlist_for_manufacturer(template_name, manufacturer)
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="确认", command=confirm_manufacturer).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=manufacturer_window.destroy).pack(side=tk.LEFT, padx=10)

    def _show_cmdlist_for_manufacturer(self, template_name, manufacturer):
        """为指定厂商显示命令模板"""
        # 清空日志区
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        cmd_list = db.get_cmd_template(template_name, manufacturer)
        
        with open('tool_cmdlist.txt', 'w', encoding='utf-8') as f:
            for cmd in cmd_list:
                f.write(cmd + '\n')
        
        webbrowser.open('tool_cmdlist.txt')
        self.append_output(f"已打开命令模板文件：{template_name} (厂商: {manufacturer})\n")

    def _process_custom_cmd_import(self, file_path, manufacturer, template_name):
        """处理自定义命令导入"""
        try:
            with open(file_path, 'r', encoding='UTF-8') as f:
                user_cmds = f.readlines()
            
            # 保存命令到数据库
            import sqlite3
            conn = sqlite3.connect('patrol.db')
            cursor = conn.cursor()
            
            # 先删除该厂商的所有命令（包括自定义和非自定义），确保完全清空
            cursor.execute('DELETE FROM commands WHERE template_name = ? AND LOWER(manufacturer) = LOWER(?)',
                       (template_name, manufacturer))
            
            # 插入新的自定义命令
            # 根据模板名称确定 template_id
            template_id = 0
            if template_name == '普通巡检模板':
                template_id = 0
            elif template_name == '深度巡检模板':
                template_id = 1
            elif template_name == '自定义模板':
                template_id = 2
            
            # 插入新命令（不进行去重处理）
            for cmd_order, cmd in enumerate(user_cmds, 1):
                cmd = cmd.strip()
                if cmd:
                    cursor.execute(
                        'INSERT INTO commands (template_id, template_name, manufacturer, command, cmd_order, is_custom) VALUES (?, ?, ?, ?, ?, ?)',
                        (template_id, template_name, manufacturer, cmd, cmd_order, 1)
                    )
            
            conn.commit()
            conn.close()
            
            # 同时添加到内存中的user_cmd列表
            i = 0
            for cmd in user_cmds:
                cmd = cmd.strip()
                if cmd:
                    i += 1
                    self.insert_data('importcmd', cmd)
            
            self.append_output(f"导入成功！导入了{i}个巡检命令,具体命令如下：\n")
            for cmd in user_cmds:
                cmd = cmd.strip()
                if cmd:
                    self.append_output(cmd + '\n')
            self.append_output("\n命令已保存到数据库\n")
        except Exception as e:
            self.append_output(f"导入失败：{str(e)}\n")
            import traceback
            self.append_output(f"错误详情：{traceback.format_exc()}\n")
    
    def idev(self):
        """导入设备信息"""
        file_path = filedialog.askopenfilename(
            title="选择设备信息文件",
            initialdir=os.getcwd(),
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*")]
        )
        
        if file_path:
            try:
                # 清空日志区
                self.output_text.config(state=tk.NORMAL)
                self.output_text.delete(1.0, tk.END)
                self.output_text.config(state=tk.DISABLED)
                
                self.append_output(f"已选择设备信息文件：{file_path}\n")
                
                # Parse CSV file
                import csv
                devices = []
                rows_to_write = []
                encrypted_count = 0
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for i, row in enumerate(reader):
                        if i == 0:
                            # 保存表头
                            rows_to_write.append(row)
                            continue
                        if len(row) >= 5:
                            # Read manufacturer, IP, username, password, port
                            manufacturer, ip, username, password, port = row[0], row[1], row[2], row[3], row[4]
                            # 检查密码是否已加密
                            if not crypto.is_encrypted(password):
                                # 加密密码
                                password = crypto.encrypt(password)
                                encrypted_count += 1
                            # 更新行数据
                            row[3] = password
                            rows_to_write.append(row)
                            devices.append((manufacturer, ip, username, password, port))
                        elif len(row) >= 4:
                            # Compatible with old format (no manufacturer column)
                            manufacturer = "unknown"
                            ip, username, password, port = row[0], row[1], row[2], row[3]
                            # 检查密码是否已加密
                            if not crypto.is_encrypted(password):
                                # 加密密码
                                password = crypto.encrypt(password)
                                encrypted_count += 1
                            # 更新行数据
                            row[2] = password
                            rows_to_write.append(row)
                            devices.append((manufacturer, ip, username, password, port))
                
                # 将加密后的数据写回CSV文件
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(rows_to_write)
                
                # 存储设备列表
                self.devices = devices
                
                # 展示导入的设备列表
                if devices:
                    self.append_output("\n导入的设备列表：\n")
                    self.append_output("-" * 100 + "\n")
                    self.append_output(f"{'厂商':<15} {'IP地址':<20} {'用户名':<15} {'密码':<15} {'端口':<10}\n")
                    self.append_output("-" * 100 + "\n")
                    
                    for manufacturer, ip, username, password, port in devices:
                        # 显示密码为掩码，保护密码安全
                        password_display = "******" if password else ""
                        self.append_output(f"{manufacturer:<15} {ip:<20} {username:<15} {password_display:<15} {port:<10}\n")
                    
                    self.append_output("-" * 80 + "\n")
                    
                    # 更新设备统计
                    device_count = len(devices)
                    self.dev_total_var.set(str(device_count))
                    if encrypted_count > 0:
                        self.append_output(f"\n设备导入成功！共导入 {device_count} 台设备，已加密 {encrypted_count} 个明文密码\n")
                        self.append_output(f"CSV文件已更新，明文密码已替换为加密密码\n")
                    else:
                        self.append_output(f"\n设备导入成功！共导入 {device_count} 台设备（所有密码已是加密状态）\n")
                else:
                    self.append_output("\n警告：未找到有效的设备信息\n")
                    self.dev_total_var.set("0")
                    
            except Exception as e:
                self.append_output(f"\n导入设备信息失败：{str(e)}\n")
                self.dev_total_var.set("0")
    
    def get_template(self):
        """下载导入设备模板"""
        try:
            import os
            
            # 直接保存到程序运行目录
            save_path = os.path.join(os.getcwd(), 'device_template_for_batchssh.csv')
            
            # 检查目标文件是否存在
            if os.path.exists(save_path):
                # 文件已存在，直接打开
                os.startfile(save_path)
                self.append_output(f"设备模板已存在，已打开: {save_path}\n")
                return
            
            # 创建新的模板文件
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write('manufacturer,ip,username,password,port\n')
                f.write('hillstone,192.168.113.128,hillstone,Aa@123456,22\n')
            
            # 打开文件供用户填写
            os.startfile(save_path)
            
            self.append_output(f"设备模板已保存到: {save_path}\n")
            self.append_output("模板文件已自动打开，请填写设备信息后保存。\n")
        except Exception as e:
            self.append_output(f"下载模板失败：{str(e)}\n")
    
    def collectlog(self):
        """开始批量巡检"""
        template_name = self.cmd_template_var.get()
        
        if template_name == '选择巡检命令模板':
            self.append_output("请先选择命令模板！\n")
            return
        
        # 检查是否有导入的设备列表
        if not self.devices:
            self.append_output("请先导入设备信息！\n")
            return
        
        # 禁用按钮并设置灰色背景
        self.batch_collect_button.configure(state="disabled")
        # 保存原始背景色
        self.original_fg_color = "#007bff"
        # 设置禁用状态的灰色背景
        self.batch_collect_button.configure(fg_color="#a0a0a0")
        
        # 构建设备列表（添加表头）
        gdev = [['厂商', 'IP', '用户名', '密码', '端口']]  # 表头
        for device in self.devices:
            gdev.append(list(device))

        # 最大并发数（默认20，可根据需要调整）
        max_concurrent = 20

        def run_batch_collect():
            try:
                Patrol.batch_collect(self, gdev, template_name, max_concurrent)
            finally:
                # 启用按钮
                self.batch_collect_button.configure(state="normal")
                # 恢复原始背景色
                self.batch_collect_button.configure(fg_color="#007bff")
        
        t = threading.Thread(target=run_batch_collect)
        t.daemon = True
        t.start()

class SSHTerminalPage(tk.Frame, Core):
    """SSH终端页面"""
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        Core.__init__(self)
        self.ssh_windows = []  # 存储打开的SSH窗口
        self.setup_ui()
        self.load_history()
    
    def setup_ui(self):
        """设置 UI"""
        # 主容器
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：登录表单
        left_frame = ttk.LabelFrame(main_frame, text="SSH登录", style="Bordered.TFrame", padding="10", width=300)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        
        # 设备地址
        ttk.Label(left_frame, text="设备地址：").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
        self.ip_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.ip_var, width=20).grid(row=0, column=1, padx=(0, 5), pady=5)
        
        # SSH端口
        ttk.Label(left_frame, text="SSH端口：").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.port_var = tk.StringVar(value="22")
        ttk.Entry(left_frame, textvariable=self.port_var, width=20).grid(row=1, column=1, padx=(0, 5), pady=5)
    
        # 用户名
        ttk.Label(left_frame, text="用 户  名：").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
        self.user_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.user_var, width=20).grid(row=2, column=1, padx=(0, 5), pady=5)
        
        # 密码
        ttk.Label(left_frame, text="密      码：").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.password_var, show="*", width=20).grid(row=3, column=1, padx=(0, 5), pady=5)
        
        # 编码选择
        ttk.Label(left_frame, text="编      码：").grid(row=4, column=0, sticky=tk.E, padx=5, pady=5)
        self.encoding_var = tk.StringVar(value="utf-8")
        self.encoding_combobox = ttk.Combobox(
            left_frame, 
            textvariable=self.encoding_var,
            values=[
                'utf-8',
                'gb2312',
                'gbk',
                'gb18030',
                'big5',
                'utf-16'
            ],
            state="readonly",
            width=18
        )
        self.encoding_combobox.grid(row=4, column=1, padx=5, pady=5)
        
        # 登录按钮
        self.login_button = ctk.CTkButton(
            left_frame, 
            text="登录", 
            command=self.login_ssh,
            fg_color="#007bff",       # 正常背景色 (蓝色)
            hover_color="#0056b3",    # 悬停背景色 (深蓝)
            text_color="white",
            corner_radius=8,          # 圆角
            height=40,
            font=("微软雅黑", 12, "bold")
        )
        self.login_button.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky=tk.EW)
        

        
        # 右侧：历史记录
        right_frame = ttk.LabelFrame(main_frame, text="历史登录", style="Bordered.TFrame", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 历史记录列表 - 添加边框
        style = ttk.Style()
        style.configure("Treeview", borderwidth=1, relief="solid")
        
        self.history_tree = ttk.Treeview(right_frame, columns=("ip", "port", "user", "encoding", "time"), show="headings", style="Treeview")
        # 设置所有列左对齐
        self.history_tree.heading("ip", text="设备地址", anchor=tk.W)
        self.history_tree.heading("port", text="端口", anchor=tk.W)
        self.history_tree.heading("user", text="用户名", anchor=tk.W)
        self.history_tree.heading("encoding", text="编码", anchor=tk.W)
        self.history_tree.heading("time", text="登录时间", anchor=tk.W)
        
        # 设置列宽度，根据文本内容自动调整
        self.history_tree.column("ip", width=120, minwidth=100, stretch=tk.YES)
        self.history_tree.column("port", width=60, minwidth=50, stretch=tk.NO)
        self.history_tree.column("user", width=100, minwidth=80, stretch=tk.YES)
        self.history_tree.column("encoding", width=80, minwidth=60, stretch=tk.NO)
        self.history_tree.column("time", width=140, minwidth=120, stretch=tk.YES)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_tree.pack(fill=tk.BOTH, expand=True)
        
        # 历史记录操作按钮
        history_button_frame = ttk.Frame(right_frame)
        history_button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(history_button_frame, text="使用选中记录", command=self.use_selected_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_button_frame, text="删除选中记录", command=self.delete_selected_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_button_frame, text="清除历史记录", command=self.clear_history).pack(side=tk.LEFT, padx=5)
        
        # 绑定双击事件 - 双击直接登录
        self.history_tree.bind('<Double-1>', self.on_history_double_click)
        
        # 绑定Delete键删除选中记录
        self.history_tree.bind('<Delete>', lambda event: self.delete_selected_history())
        
        # 创建右键菜单
        self.history_context_menu = tk.Menu(self, tearoff=0)
        self.history_context_menu.add_command(label="删除", command=self.delete_selected_history)
        self.history_context_menu.add_command(label="查看密码", command=self.show_password)
        
        # 绑定右键菜单
        self.history_tree.bind('<Button-3>', self.show_history_context_menu)
    
    def encrypt_password(self, password):
        """加密密码"""
        import base64
        # 简单的Base64加密（可替换为更强的加密方式）
        return base64.b64encode(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password):
        """解密密码"""
        import base64
        try:
            return base64.b64decode(encrypted_password.encode()).decode()
        except:
            return ""
    
    def load_history(self):
        """加载历史登录记录"""
        try:
            import sqlite3
            conn = sqlite3.connect('patrol.db')
            cursor = conn.cursor()
            
            # 检查表格是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ssh_history'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                # 检查表格结构，添加encoding字段（如果不存在）
                cursor.execute('PRAGMA table_info(ssh_history)')
                columns = [column[1] for column in cursor.fetchall()]
                if 'encoding' not in columns:
                    # 添加encoding字段
                    cursor.execute('ALTER TABLE ssh_history ADD COLUMN encoding TEXT')
                    conn.commit()
            else:
                # 创建历史记录表格（如果不存在）- 添加密码和编码字段
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ssh_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ip TEXT,
                        port INTEGER,
                        user TEXT,
                        password TEXT,
                        encoding TEXT,
                        login_time TEXT
                    )
                ''')
            
            # 查询历史记录 - 按IP、端口、用户名分组，只取每组最后一条
            try:
                cursor.execute('''
                    SELECT h1.ip, h1.port, h1.user, h1.encoding, h1.login_time 
                    FROM ssh_history h1
                    JOIN (
                        SELECT ip, port, user, MAX(login_time) as max_time
                        FROM ssh_history
                        GROUP BY ip, port, user
                    ) h2 ON h1.ip = h2.ip AND h1.port = h2.port AND h1.user = h2.user AND h1.login_time = h2.max_time
                    ORDER BY h1.login_time DESC
                    LIMIT 50
                ''')
            except sqlite3.OperationalError:
                # 如果encoding字段还不存在，使用旧的查询
                cursor.execute('''
                    SELECT ip, port, user, MAX(login_time) as last_login 
                    FROM ssh_history 
                    GROUP BY ip, port, user 
                    ORDER BY last_login DESC 
                    LIMIT 50
                ''')
            records = cursor.fetchall()
            
            # 清空树状图
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            
            # 添加历史记录
            for record in records:
                # 确保记录包含编码信息
                if len(record) == 4:
                    # 旧记录，没有编码字段
                    ip, port, user, login_time = record
                    encoding = "utf-8"
                else:
                    # 新记录，包含编码字段
                    ip, port, user, encoding, login_time = record
                # 如果编码为空，显示"utf-8"
                if not encoding:
                    encoding = "utf-8"
                self.history_tree.insert('', 'end', values=(ip, port, user, encoding, login_time))
            
            conn.close()
        except Exception as e:
            print(f"加载历史记录失败: {e}")
    
    def save_history(self, ip, port, user, password, encoding):
        """保存登录历史记录"""
        try:
            import sqlite3
            import datetime
            conn = sqlite3.connect('patrol.db')
            cursor = conn.cursor()
            
            # 加密密码
            encrypted_password = self.encrypt_password(password)
            
            # 插入历史记录
            login_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                'INSERT INTO ssh_history (ip, port, user, password, encoding, login_time) VALUES (?, ?, ?, ?, ?, ?)',
                (ip, port, user, encrypted_password, encoding, login_time)
            )
            
            # 限制历史记录数量
            cursor.execute('DELETE FROM ssh_history WHERE id NOT IN (SELECT id FROM ssh_history ORDER BY login_time DESC LIMIT 50)')
            
            conn.commit()
            conn.close()
            
            # 重新加载历史记录
            self.load_history()
        except Exception as e:
            print(f"保存历史记录失败: {e}")
    
    def use_selected_history(self):
        """使用选中的历史记录"""
        selected_item = self.history_tree.selection()
        if selected_item:
            item = selected_item[0]
            values = self.history_tree.item(item, 'values')
            if values:
                self.ip_var.set(values[0])
                self.port_var.set(str(values[1]))
                self.user_var.set(values[2])
                # 填充编码
                encoding = "utf-8"
                if len(values) >= 4:
                    encoding = values[3]
                    if encoding in self.encoding_combobox['values']:
                        self.encoding_combobox.set(encoding)
                # 从数据库获取密码
                self.fill_password_from_history(values[0], values[1], values[2])
    
    def delete_selected_history(self):
        """删除选中的历史记录"""
        selected_item = self.history_tree.selection()
        if not selected_item:
            messagebox.showwarning("提示", "请先选择要删除的记录！")
            return
        
        if messagebox.askyesno("确认", "确定要删除选中的历史记录吗？"):
            try:
                import sqlite3
                item = selected_item[0]
                values = self.history_tree.item(item, 'values')
                if values:
                    conn = sqlite3.connect('patrol.db')
                    cursor = conn.cursor()
                    # 删除该IP、端口、用户的所有记录
                    cursor.execute(
                        'DELETE FROM ssh_history WHERE ip=? AND port=? AND user=?',
                        (values[0], values[1], values[2])
                    )
                    conn.commit()
                    conn.close()
                    
                    # 重新加载历史记录
                    self.load_history()
                    messagebox.showinfo("成功", "历史记录已删除！")
            except Exception as e:
                print(f"删除历史记录失败: {e}")
                messagebox.showerror("错误", f"删除失败: {e}")
    
    def show_history_context_menu(self, event):
        """显示右键菜单"""
        # 选中鼠标指向的行
        item = self.history_tree.identify_row(event.y)
        if item:
            self.history_tree.selection_set(item)
            # 保存鼠标位置
            self.mouse_x = event.x_root
            self.mouse_y = event.y_root
            # 显示右键菜单
            self.history_context_menu.post(event.x_root, event.y_root)
    
    def show_password(self):
        """查看密码"""
        selected_item = self.history_tree.selection()
        if not selected_item:
            messagebox.showwarning("提示", "请先选择要查看密码的记录！")
            return
        
        # 检查是否设置了查看密码
        if not self.check_view_password_set():
            # 首次使用，需要设置查看密码
            self.set_view_password()
            return
        
        # 验证查看密码
        if not self.verify_view_password():
            return
        
        # 显示密码
        item = selected_item[0]
        values = self.history_tree.item(item, 'values')
        if values:
            try:
                import sqlite3
                conn = sqlite3.connect('patrol.db')
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT password FROM ssh_history WHERE ip=? AND port=? AND user=? ORDER BY login_time DESC LIMIT 1',
                    (values[0], values[1], values[2])
                )
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0]:
                    password = self.decrypt_password(result[0])
                    # 显示密码对话框
                    self.show_password_dialog(values[0], values[2], password)
                else:
                    messagebox.showinfo("提示", "该记录没有保存密码！")
            except Exception as e:
                print(f"获取密码失败: {e}")
                messagebox.showerror("错误", f"获取密码失败: {e}")
    
    def check_view_password_set(self):
        """检查是否设置了查看密码"""
        try:
            import sqlite3
            conn = sqlite3.connect('patrol.db')
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            cursor.execute('SELECT value FROM app_settings WHERE key=?', ('view_password',))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except Exception as e:
            print(f"检查查看密码设置失败: {e}")
            return False
    
    def set_view_password(self):
        """设置查看密码"""
        dialog = tk.Toplevel(self)
        dialog.title("设置查看密码")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()
        
        # 使用保存的鼠标位置来定位对话框
        if hasattr(self, 'mouse_x') and hasattr(self, 'mouse_y'):
            # 在鼠标位置下方显示对话框
            dialog_x = self.mouse_x
            dialog_y = self.mouse_y + 10
            dialog.geometry(f"300x150+{dialog_x}+{dialog_y}")
        else:
            #  fallback: 在历史记录树下方显示对话框
            tree_x = self.history_tree.winfo_rootx()
            tree_y = self.history_tree.winfo_rooty()
            tree_height = self.history_tree.winfo_height()
            dialog_x = tree_x + 50
            dialog_y = tree_y + tree_height + 10
            dialog.geometry(f"300x150+{dialog_x}+{dialog_y}")
        
        ttk.Label(dialog, text="请设置查看密码的密码：").pack(pady=10)
        
        password_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=password_var, show="*", width=25)
        entry.pack(pady=5)
        entry.focus()
        
        def save_password():
            password = password_var.get()
            if not password:
                messagebox.showwarning("提示", "密码不能为空！", parent=dialog)
                return
            
            try:
                import sqlite3
                conn = sqlite3.connect('patrol.db')
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS app_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                ''')
                # 加密存储查看密码
                encrypted = self.encrypt_password(password)
                cursor.execute(
                    'INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)',
                    ('view_password', encrypted)
                )
                conn.commit()
                conn.close()
                messagebox.showinfo("成功", "查看密码已设置！", parent=dialog)
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"设置失败: {e}", parent=dialog)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="确定", command=save_password).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # 绑定回车键
        dialog.bind('<Return>', lambda event: save_password())
    
    def verify_view_password(self):
        """验证查看密码"""
        dialog = tk.Toplevel(self)
        dialog.title("验证密码")
        dialog.geometry("300x120")
        dialog.transient(self)
        dialog.grab_set()
        
        # 使用保存的鼠标位置来定位对话框
        if hasattr(self, 'mouse_x') and hasattr(self, 'mouse_y'):
            # 在鼠标位置下方显示对话框
            dialog_x = self.mouse_x
            dialog_y = self.mouse_y + 10
            dialog.geometry(f"300x120+{dialog_x}+{dialog_y}")
        else:
            #  fallback: 在历史记录树下方显示对话框
            tree_x = self.history_tree.winfo_rootx()
            tree_y = self.history_tree.winfo_rooty()
            tree_height = self.history_tree.winfo_height()
            dialog_x = tree_x + 50
            dialog_y = tree_y + tree_height + 10
            dialog.geometry(f"300x120+{dialog_x}+{dialog_y}")
        
        ttk.Label(dialog, text="请输入查看密码：").pack(pady=10)
        
        password_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=password_var, show="*", width=25)
        entry.pack(pady=5)
        entry.focus()
        
        result = [False]  # 使用列表来在闭包中修改
        
        def check_password():
            input_password = password_var.get()
            try:
                import sqlite3
                conn = sqlite3.connect('patrol.db')
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM app_settings WHERE key=?', ('view_password',))
                stored_password = cursor.fetchone()
                conn.close()
                
                if stored_password and stored_password[0]:
                    decrypted = self.decrypt_password(stored_password[0])
                    if input_password == decrypted:
                        result[0] = True
                        dialog.destroy()
                    else:
                        messagebox.showerror("错误", "密码错误！", parent=dialog)
                else:
                    messagebox.showerror("错误", "未设置查看密码！", parent=dialog)
            except Exception as e:
                messagebox.showerror("错误", f"验证失败: {e}", parent=dialog)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="确定", command=check_password).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # 绑定回车键
        dialog.bind('<Return>', lambda event: check_password())
        
        # 等待对话框关闭
        self.wait_window(dialog)
        return result[0]
    
    def show_password_dialog(self, ip, user, password):
        """显示密码对话框"""
        dialog = tk.Toplevel(self)
        dialog.title("查看密码")
        dialog.geometry("350x150")
        dialog.transient(self)
        dialog.grab_set()
        
        # 使用保存的鼠标位置来定位对话框
        if hasattr(self, 'mouse_x') and hasattr(self, 'mouse_y'):
            # 在鼠标位置下方显示对话框
            dialog_x = self.mouse_x
            dialog_y = self.mouse_y + 10
            dialog.geometry(f"350x150+{dialog_x}+{dialog_y}")
        else:
            #  fallback: 在历史记录树下方显示对话框
            tree_x = self.history_tree.winfo_rootx()
            tree_y = self.history_tree.winfo_rooty()
            tree_height = self.history_tree.winfo_height()
            dialog_x = tree_x + 50
            dialog_y = tree_y + tree_height + 10
            dialog.geometry(f"350x150+{dialog_x}+{dialog_y}")
        
        ttk.Label(dialog, text=f"设备: {ip}").pack(pady=5)
        ttk.Label(dialog, text=f"用户: {user}").pack(pady=5)
        
        password_frame = ttk.Frame(dialog)
        password_frame.pack(pady=10)
        ttk.Label(password_frame, text="密码: ").pack(side=tk.LEFT)
        password_entry = ttk.Entry(password_frame, width=25)
        password_entry.pack(side=tk.LEFT, padx=5)
        password_entry.insert(0, password)
        password_entry.config(state='readonly')
        
        def copy_password():
            self.clipboard_clear()
            self.clipboard_append(password)
            messagebox.showinfo("成功", "密码已复制到剪贴板！", parent=dialog)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="复制密码", command=copy_password).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关闭", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def fill_password_from_history(self, ip, port, user):
        """从历史记录中获取密码"""
        try:
            import sqlite3
            conn = sqlite3.connect('patrol.db')
            cursor = conn.cursor()
            cursor.execute(
                'SELECT password FROM ssh_history WHERE ip=? AND port=? AND user=? ORDER BY login_time DESC LIMIT 1',
                (ip, port, user)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                # 解密密码
                password = self.decrypt_password(result[0])
                self.password_var.set(password)
        except Exception as e:
            print(f"获取密码失败: {e}")
    
    def on_history_double_click(self, event):
        """双击历史记录 - 自动填入信息"""
        selected_item = self.history_tree.selection()
        if selected_item:
            item = selected_item[0]
            values = self.history_tree.item(item, 'values')
            if values:
                # 填入表单
                self.ip_var.set(values[0])
                self.port_var.set(str(values[1]))
                self.user_var.set(values[2])
                # 填充编码
                encoding = "utf-8"
                if len(values) >= 4:
                    encoding = values[3]
                    if encoding in self.encoding_combobox['values']:
                        self.encoding_combobox.set(encoding)
                # 获取密码
                self.fill_password_from_history(values[0], values[1], values[2])
    
    def clear_history(self):
        """清除历史记录"""
        if messagebox.askyesno("确认", "确定要清除所有历史登录记录吗？"):
            try:
                import sqlite3
                conn = sqlite3.connect('patrol.db')
                cursor = conn.cursor()
                cursor.execute('DELETE FROM ssh_history')
                conn.commit()
                conn.close()
                
                # 清空树状图
                for item in self.history_tree.get_children():
                    self.history_tree.delete(item)
            except Exception as e:
                print(f"清除历史记录失败: {e}")
    
    def login_ssh(self):
        """登录SSH并打开终端窗口"""
        # 获取参数
        ip = self.ip_var.get()
        port = int(self.port_var.get())
        user = self.user_var.get()
        password = self.password_var.get()
        
        # 验证参数
        if not ip:
            messagebox.showerror("错误", "请输入设备地址！")
            return
        
        if not user:
            messagebox.showerror("错误", "请输入用户名！")
            return
        
        if not password:
            messagebox.showerror("错误", "请输入密码！")
            return
        
        # 获取选择的编码
        encoding = self.encoding_var.get()
        # 保存历史记录（包含加密后的密码和编码）
        self.save_history(ip, port, user, password, encoding)
        
        # 打开SSH终端窗口
        self.open_ssh_window(ip, port, user, password, encoding)
    
    def open_ssh_window(self, ip, port, user, password, encoding=None):
        """打开SSH终端窗口"""
        # 如果没有传递编码，获取选择的编码
        if encoding is None:
            encoding = self.encoding_var.get()
        
        # 创建窗口（不传位置参数，让窗口默认居中显示）
        window = SSHWindow(ip, port, user, password, None, None, encoding)
        self.ssh_windows.append(window)
        window.protocol("WM_DELETE_WINDOW", lambda: self.on_ssh_window_close(window))
        window.mainloop()
    
    def on_ssh_window_close(self, window):
        """SSH窗口关闭事件"""
        if window in self.ssh_windows:
            self.ssh_windows.remove(window)
        window.destroy()

class PaginationConfigPage(ttk.Frame):
    """禁用分页配置页面"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        # 创建主框架
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 厂商选择框架
        manufacturer_frame = ttk.LabelFrame(main_frame, text="选择厂商", style="Bordered.TFrame", padding=10)
        manufacturer_frame.pack(fill=tk.X, pady=10)
        
        # 厂商选择下拉框
        self.manufacturer_var = tk.StringVar(value="Hillstone")
        manufacturer_combobox = ttk.Combobox(
            manufacturer_frame,
            textvariable=self.manufacturer_var,
            values=["Hillstone", "Huawei", "Topsec"],
            state="readonly",
            width=20
        )
        manufacturer_combobox.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 加载按钮
        ttk.Button(manufacturer_frame, text="加载配置", command=self.load_config).pack(side=tk.LEFT, padx=10, pady=5)
        
        # 命令配置框架
        command_frame = ttk.LabelFrame(main_frame, text="命令配置", style="Bordered.TFrame", padding=10)
        command_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 前置命令
        ttk.Label(command_frame, text="前置命令（巡检前执行）:").pack(anchor=tk.W, pady=5)
        self.pre_command_text = tk.Text(command_frame, height=5, width=80, font=('Consolas', 9))
        self.pre_command_text.pack(fill=tk.X, pady=5)
        
        # 后置命令
        ttk.Label(command_frame, text="后置命令（巡检后执行）:").pack(anchor=tk.W, pady=5)
        self.post_command_text = tk.Text(command_frame, height=5, width=80, font=('Consolas', 9))
        self.post_command_text.pack(fill=tk.X, pady=5)
        
        # 提示标签
        ttk.Label(command_frame, text="提示：每行一个命令，按执行顺序排列", font=('微软雅黑', 8, 'italic')).pack(anchor=tk.W, pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 保存按钮
        self.save_config_button = ctk.CTkButton(
            button_frame, 
            text="保存配置", 
            command=self.save_config,
            fg_color="#007bff",       # 正常背景色 (蓝色)
            hover_color="#0056b3",    # 悬停背景色 (深蓝)
            text_color="white",
            corner_radius=8,          # 圆角
            height=40,
            font=("微软雅黑", 12, "bold")
        )
        self.save_config_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 重置按钮
        ttk.Button(button_frame, text="重置", command=self.reset_config).pack(side=tk.LEFT, padx=10, pady=5)
    
    def load_config(self):
        """加载配置"""
        manufacturer = self.manufacturer_var.get()
        
        # 从数据库中获取厂商的前后命令
        pre_commands = db.get_manufacturer_commands(manufacturer, "pre")
        post_commands = db.get_manufacturer_commands(manufacturer, "post")
        
        # 清空文本框
        self.pre_command_text.delete(1.0, tk.END)
        self.post_command_text.delete(1.0, tk.END)
        
        # 填充文本框
        for cmd in pre_commands:
            self.pre_command_text.insert(tk.END, cmd + '\n')
        
        for cmd in post_commands:
            self.post_command_text.insert(tk.END, cmd + '\n')
    
    def save_config(self):
        """保存配置"""
        manufacturer = self.manufacturer_var.get()
        
        # 获取文本框中的命令
        pre_commands = self.pre_command_text.get(1.0, tk.END).strip().split('\n')
        post_commands = self.post_command_text.get(1.0, tk.END).strip().split('\n')
        
        # 过滤空命令
        pre_commands = [cmd for cmd in pre_commands if cmd.strip()]
        post_commands = [cmd for cmd in post_commands if cmd.strip()]
        
        # 检查是否有内容
        if not pre_commands and not post_commands:
            messagebox.showwarning("提示", "请输入要保存的命令内容！")
            return
        
        # 保存到数据库
        db.save_manufacturer_commands(manufacturer, "pre", pre_commands)
        db.save_manufacturer_commands(manufacturer, "post", post_commands)
        
        # 显示成功消息
        messagebox.showinfo("成功", f"{manufacturer}的命令配置已保存！")
    
    def reset_config(self):
        """重置配置"""
        # 清空文本框
        self.pre_command_text.delete(1.0, tk.END)
        self.post_command_text.delete(1.0, tk.END)
        
        # 为山石厂商设置默认命令
        if self.manufacturer_var.get() == "Hillstone":
            self.pre_command_text.insert(tk.END, "terminal length 0\n")
            self.post_command_text.insert(tk.END, "terminal length 25\n")

class MainWindow(tk.Tk):
    """主窗口"""
    def __init__(self, app_version='0.3.0'):
        super().__init__()
        self.title(f'巡检助手 v{app_version}')
        # 窗口大小
        window_width = 850
        window_height = 650
        
        # 计算屏幕位置：垂直居中，水平左侧1/4处
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width // 6  # 水平左侧1/4处
        y = (screen_height - window_height) // 2  # 垂直居中
        
        # 设置窗口大小和位置
        self.geometry(f'{window_width}x{window_height}+{x}+{y}')

        self.minsize(800, 600)
        
        # 设置样式
        self.setup_styles()
        
        # 创建标签页
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 添加页面
        self.ssh_page = SSHPatrolPage(self.notebook)
        self.batch_ssh_page = BatchSSHPatrolPage(self.notebook)
        self.ssh_terminal_page = SSHTerminalPage(self.notebook)
        self.pagination_config_page = PaginationConfigPage(self.notebook)

        # 添加到标签页
        self.notebook.add(self.ssh_page, text='单设备巡检')
        self.notebook.add(self.batch_ssh_page, text='批量设备巡检')
        self.notebook.add(self.ssh_terminal_page, text='SSH终端')
        self.notebook.add(self.pagination_config_page, text='禁用分页配置')
        
        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 绑定全局回车键 - 根据当前页面调用对应的蓝色按钮
        self.bind('<Return>', self.on_global_return)
    
    def on_global_return(self, event):
        """全局回车键处理 - 根据当前页面调用对应按钮"""
        # 获取当前选中的标签页索引
        current_tab = self.notebook.index(self.notebook.select())
        
        # 根据当前页面调用对应的按钮
        if current_tab == 0:  # SSH版页面
            self.ssh_page.run_ssh()
        elif current_tab == 1:  # SSH(批量版)页面
            self.batch_ssh_page.collectlog()
        elif current_tab == 2:  # SSH终端页面
            self.ssh_terminal_page.login_ssh()
        elif current_tab == 3:  # 禁用分页配置页面
            self.pagination_config_page.save_config()
    
    def setup_styles(self):
        """设置样式"""
        style = ttk.Style()
        # 关键：必须配置 borderwidth 和 relief 才能看到边框
        style.configure(
            "Bordered.TFrame", 
            borderwidth=2, 
            relief="solid"
        )
    
    def on_close(self):
        """关闭窗口事件"""
        self.destroy()

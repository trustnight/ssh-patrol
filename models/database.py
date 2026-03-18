# -*- coding: utf-8 -*-
"""
数据库操作模块
"""
import sqlite3


class Database:
    def __init__(self):
        self.conn = None
        self.db_path = 'patrol.db'
    
    def newdb(self, ui):
        """初始化数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
    
            # 创建命令表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id INTEGER,
                    template_name TEXT,
                    manufacturer TEXT,
                    command TEXT,
                    cmd_order INTEGER,
                    is_custom INTEGER DEFAULT 0
                )
            ''')
            
            # 创建厂商命令表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS manufacturer_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    manufacturer TEXT,
                    command_type TEXT,  -- pre 或 post
                    command TEXT,
                    cmd_order INTEGER
                )
            ''')
            
            # 检查命令表是否为空
            cursor.execute('SELECT COUNT(*) FROM commands')
            if cursor.fetchone()[0] == 0:
                # 初始化命令模板
                self._init_command_templates(ui)
            
            # 检查厂商命令表是否为空
            cursor.execute('SELECT COUNT(*) FROM manufacturer_commands')
            if cursor.fetchone()[0] == 0:
                # 初始化厂商命令
                self._init_manufacturer_commands(ui)
            
            self.conn.commit()
            
            if hasattr(ui, 'out'):
                ui.out.AppendText("数据库初始化成功！\n")
            if hasattr(ui, 'append_output'):
                ui.append_output("数据库初始化成功！\n")
                
        except Exception as e:
            if hasattr(ui, 'out'):
                ui.out.AppendText(f"数据库初始化错误: {str(e)}\n")
            if hasattr(ui, 'append_output'):
                ui.append_output(f"数据库初始化错误: {str(e)}\n")
    
    def _init_command_templates(self, ui):
        """初始化命令模板到数据库"""
        try:
            cursor = self.conn.cursor()
            
            # 定义模板映射
            templates = {
                '普通巡检模板': {
                    'Hillstone': [
                        'show version',
                        'show license',
                        'show ha group 0',
                        'show session generic detail',
                        'show session generic',
                        'show cpu',
                        'show cpu detail',
                        'show memory',
                        'show memory detail',
                        'show statistics-set predef_if_bw current',
                        'show module',
                        'show environment',
                        'show logging event',
                        'show logging threat',
                        'show logging alarm',
                        'show configuration'
                    ],
                    'Huawei': [
                        'display esn',
                        'display firewall session table',
                        'display diagnostic-information'
                    ]
                },
                '深度巡检模板': {
                    'Hillstone': [
                        'show version detail',
                        'show version',
                        'show license',
                        'show image',
                        'show clock',
                        'show configuration',
                        'show configuration non',
                        'show session generic',
                        'show session generic detail',
                        'show cpu',
                        'show cpu detail',
                        'show memory',
                        'show memory detail',
                        'show environment',
                        'show arp',
                        'show interface',
                        'show interface detail',
                        'show routing-table',
                        'show vpn',
                        'show zone',
                        'show policy',
                        'show policy all',
                        'show object address',
                        'show object service',
                        'show object application',
                        'show user local',
                        'show logging event',
                        'show logging threat',
                        'show logging alarm',
                        'show ha group 0',
                        'show ha statistics',
                        'show statistics-set predef_if_bw current',
                        'show module',
                        'show module detail',
                        'show tech-support'
                    ],
                    'Huawei': [
                        'display version',
                        'display esn',
                        'display cpu-usage',
                        'display memory-usage',
                        'display interface',
                        'display ip routing-table',
                        'display firewall session table',
                        'display security-policy',
                        'display zone',
                        'display object-group',
                        'display local-user',
                        'display diagnostic-information'
                    ]
                },
                '自定义模板': {
                    'Hillstone': [],
                    'Huawei': [],
                    'Topsec': []
                }
            }
            
            # 插入命令模板
            for template_name, manufacturers in templates.items():
                # 根据模板名称确定 template_id
                template_id = 0
                if template_name == '普通巡检模板':
                    template_id = 0
                elif template_name == '深度巡检模板':
                    template_id = 1
                elif template_name == '自定义模板':
                    template_id = 2
                
                for manufacturer, commands in manufacturers.items():
                    for cmd_order, cmd in enumerate(commands, 1):
                        cursor.execute(
                            'INSERT INTO commands (template_id, template_name, manufacturer, command, cmd_order, is_custom) VALUES (?, ?, ?, ?, ?, ?)',
                            (template_id, template_name, manufacturer, cmd, cmd_order, 0)
                        )
            
            self.conn.commit()
            
            if hasattr(ui, 'append_output'):
                ui.append_output("命令模板初始化成功！\n")
                
        except Exception as e:
            if hasattr(ui, 'append_output'):
                ui.append_output(f"初始化命令模板错误: {str(e)}\n")
    
    def _init_manufacturer_commands(self, ui):
        """初始化厂商命令到数据库"""
        try:
            cursor = self.conn.cursor()
            
            # 定义厂商命令
            manufacturer_commands = {
                'Hillstone': {
                    'pre': ['terminal length 0'],
                    'post': ['terminal length 25']
                },
                'Huawei': {
                    'pre': ['screen-length 0 temporary'],
                    'post': []
                },
                'Topsec': {
                    'pre': [],
                    'post': []
                }
            }
            
            # 插入厂商命令
            for manufacturer, command_types in manufacturer_commands.items():
                for command_type, commands in command_types.items():
                    for cmd_order, cmd in enumerate(commands, 1):
                        cursor.execute(
                            'INSERT INTO manufacturer_commands (manufacturer, command_type, command, cmd_order) VALUES (?, ?, ?, ?)',
                            (manufacturer, command_type, cmd, cmd_order)
                        )
            
            self.conn.commit()
            
            if hasattr(ui, 'append_output'):
                ui.append_output("厂商命令初始化成功！\n")
                
        except Exception as e:
            if hasattr(ui, 'append_output'):
                ui.append_output(f"初始化厂商命令错误: {str(e)}\n")
    
    def get_cmd_template(self, template_name, manufacturer):
        """获取命令模板"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT command FROM commands WHERE template_name = ? AND LOWER(manufacturer) = LOWER(?) ORDER BY cmd_order',
                (template_name, manufacturer)
            )
            result = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in result]
        except Exception as e:
            print(f"获取命令模板错误: {str(e)}")
            return []
    
    def get_manufacturer_commands(self, manufacturer, command_type):
        """获取厂商命令"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT command FROM manufacturer_commands WHERE LOWER(manufacturer) = LOWER(?) AND command_type = ? ORDER BY cmd_order',
                (manufacturer, command_type)
            )
            result = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in result]
        except Exception as e:
            print(f"获取厂商命令错误: {str(e)}")
            return []
    
    def save_manufacturer_commands(self, manufacturer, command_type, commands):
        """保存厂商命令"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 删除该厂商的指定类型命令
            cursor.execute(
                'DELETE FROM manufacturer_commands WHERE LOWER(manufacturer) = LOWER(?) AND command_type = ?',
                (manufacturer, command_type)
            )
            
            # 插入新命令
            for cmd_order, cmd in enumerate(commands, 1):
                cursor.execute(
                    'INSERT INTO manufacturer_commands (manufacturer, command_type, command, cmd_order) VALUES (?, ?, ?, ?)',
                    (manufacturer, command_type, cmd, cmd_order)
                )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存厂商命令错误: {str(e)}")
            return False


# 创建全局数据库实例
db = Database()

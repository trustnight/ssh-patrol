# -*- coding: utf-8 -*-
"""
数据库操作模块
"""
import sqlite3
from datetime import datetime
from app.config import settings
from app.crypto_utils import crypto


class Database:
    def __init__(self):
        self.conn = None
        self.db_path = settings.DB_PATH

    def init_db(self):
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
                    command_type TEXT,
                    command TEXT,
                    cmd_order INTEGER
                )
            ''')

            # 创建设备表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    manufacturer TEXT,
                    ip TEXT,
                    username TEXT,
                    password TEXT,
                    port INTEGER DEFAULT 22,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')

            # 创建巡检历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patrol_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    ip TEXT,
                    manufacturer TEXT,
                    template_name TEXT,
                    success INTEGER DEFAULT 0,
                    log_path TEXT,
                    created_at TEXT
                )
            ''')

            # 检查命令表是否为空
            cursor.execute('SELECT COUNT(*) FROM commands')
            if cursor.fetchone()[0] == 0:
                self._init_command_templates()

            # 检查厂商命令表是否为空
            cursor.execute('SELECT COUNT(*) FROM manufacturer_commands')
            if cursor.fetchone()[0] == 0:
                self._init_manufacturer_commands()

            self.conn.commit()
            print("数据库初始化成功！")

        except Exception as e:
            print(f"数据库初始化错误: {str(e)}")

    def _init_command_templates(self):
        """初始化命令模板到数据库"""
        try:
            cursor = self.conn.cursor()

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
                    ],
                    'Topsec': [
                        'system time show',
                        'system uptime',
                        'system utilization',
                        'system ntp show',
                        'network arp show',
                        'network ospf show',
                        'network route show',
                        'network interface show all',
                        'firewall policy total',
                        'firewall policy total status enable',
                        'firewall policy total status disable'
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
                    ],
                    'Topsec': [
                        'system product model',
                        'system product sn',
                        'system terminal show',
                        'system time show',
                        'system uptime',
                        'system version',
                        'system utilization',
                        'system cpuinfo show',
                        'system mem show',
                        'system osinfo show',
                        'system ntp show',
                        'network arp show',
                        'network ospf show',
                        'network route show',
                        'network interface show all',
                        'firewall policy total',
                        'firewall policy total status enable',
                        'firewall policy total status disable',
                        'nat policy show',
                        'show',
                        'show-running'
                    ]
                },
                '自定义模板': {
                    'Hillstone': [],
                    'Huawei': [],
                    'Topsec': []
                }
            }

            for template_name, manufacturers in templates.items():
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
            print("命令模板初始化成功！")

        except Exception as e:
            print(f"初始化命令模板错误: {str(e)}")

    def _init_manufacturer_commands(self):
        """初始化厂商命令到数据库"""
        try:
            cursor = self.conn.cursor()

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

            for manufacturer, command_types in manufacturer_commands.items():
                for command_type, commands in command_types.items():
                    for cmd_order, cmd in enumerate(commands, 1):
                        cursor.execute(
                            'INSERT INTO manufacturer_commands (manufacturer, command_type, command, cmd_order) VALUES (?, ?, ?, ?)',
                            (manufacturer, command_type, cmd, cmd_order)
                        )

            self.conn.commit()
            print("厂商命令初始化成功！")

        except Exception as e:
            print(f"初始化厂商命令错误: {str(e)}")

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

    def get_template_list(self):
        """获取模板列表（去重）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT DISTINCT template_id, template_name FROM commands ORDER BY template_id'
            )
            result = cursor.fetchall()
            conn.close()

            return [{"template_id": row[0], "template_name": row[1]} for row in result]
        except Exception as e:
            print(f"获取模板列表错误: {str(e)}")
            return []

    def get_template_manufacturers(self, template_name):
        """获取指定模板支持的厂商列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT DISTINCT manufacturer FROM commands WHERE template_name = ? ORDER BY manufacturer',
                (template_name,)
            )
            result = cursor.fetchall()
            conn.close()

            return [row[0] for row in result]
        except Exception as e:
            print(f"获取模板厂商列表错误: {str(e)}")
            return []

    def get_template_commands(self, template_name, manufacturer):
        """获取模板命令列表（带详细信息）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT id, command, cmd_order, is_custom FROM commands WHERE template_name = ? AND LOWER(manufacturer) = LOWER(?) ORDER BY cmd_order',
                (template_name, manufacturer)
            )
            result = cursor.fetchall()
            conn.close()

            return [
                {
                    "id": row[0],
                    "command": row[1],
                    "cmd_order": row[2],
                    "is_custom": bool(row[3])
                }
                for row in result
            ]
        except Exception as e:
            print(f"获取模板命令错误: {str(e)}")
            return []

    def save_custom_template(self, template_name, manufacturer, commands):
        """保存自定义模板命令"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'DELETE FROM commands WHERE template_name = ? AND LOWER(manufacturer) = LOWER(?) AND is_custom = 1',
                (template_name, manufacturer)
            )

            template_id = 2
            cursor.execute(
                'SELECT template_id FROM commands WHERE template_name = ? LIMIT 1',
                (template_name,)
            )
            row = cursor.fetchone()
            if row:
                template_id = row[0]

            for cmd_order, cmd in enumerate(commands, 1):
                cursor.execute(
                    'INSERT INTO commands (template_id, template_name, manufacturer, command, cmd_order, is_custom) VALUES (?, ?, ?, ?, ?, ?)',
                    (template_id, template_name, manufacturer, cmd, cmd_order, 1)
                )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存自定义模板错误: {str(e)}")
            return False

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

            cursor.execute(
                'DELETE FROM manufacturer_commands WHERE LOWER(manufacturer) = LOWER(?) AND command_type = ?',
                (manufacturer, command_type)
            )

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

    def device_exists(self, ip):
        """检查IP是否已存在"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM devices WHERE ip = ?', (ip,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except Exception:
            return False

    def add_device(self, manufacturer, ip, username, password, port=22):
        """新增设备（IP重复时返回 None 表示已存在）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查IP是否已存在
            cursor.execute('SELECT id FROM devices WHERE ip = ?', (ip,))
            if cursor.fetchone():
                conn.close()
                return None  # IP已存在，拒绝重复添加

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            encrypted_password = crypto.encrypt(password) if not crypto.is_encrypted(password) else password

            cursor.execute(
                'INSERT INTO devices (manufacturer, ip, username, password, port, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (manufacturer, ip, username, encrypted_password, port, now, now)
            )
            conn.commit()
            device_id = cursor.lastrowid
            conn.close()
            return device_id
        except Exception as e:
            print(f"新增设备错误: {str(e)}")
            return None

    def get_devices(self, keyword=None, manufacturer=None):
        """获取设备列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = 'SELECT id, manufacturer, ip, username, password, port, created_at, updated_at FROM devices WHERE 1=1'
            params = []

            if keyword:
                query += ' AND (ip LIKE ? OR username LIKE ?)'
                keyword_pattern = f'%{keyword}%'
                params.append(keyword_pattern)
                params.append(keyword_pattern)

            if manufacturer:
                query += ' AND manufacturer = ?'
                params.append(manufacturer)

            query += ' ORDER BY id DESC'

            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.close()

            devices = []
            for row in result:
                devices.append({
                    "id": row[0],
                    "manufacturer": row[1],
                    "ip": row[2],
                    "username": row[3],
                    "password": row[4],
                    "port": row[5],
                    "created_at": row[6],
                    "updated_at": row[7]
                })
            return devices
        except Exception as e:
            print(f"获取设备列表错误: {str(e)}")
            return []

    def get_device(self, device_id):
        """获取设备详情"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT id, manufacturer, ip, username, password, port, created_at, updated_at FROM devices WHERE id = ?',
                (device_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "id": row[0],
                    "manufacturer": row[1],
                    "ip": row[2],
                    "username": row[3],
                    "password": row[4],
                    "port": row[5],
                    "created_at": row[6],
                    "updated_at": row[7]
                }
            return None
        except Exception as e:
            print(f"获取设备详情错误: {str(e)}")
            return None

    def update_device(self, device_id, manufacturer=None, ip=None, username=None, password=None, port=None):
        """更新设备信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            update_fields = []
            params = []

            if manufacturer is not None:
                update_fields.append('manufacturer = ?')
                params.append(manufacturer)
            if ip is not None:
                update_fields.append('ip = ?')
                params.append(ip)
            if username is not None:
                update_fields.append('username = ?')
                params.append(username)
            if password is not None:
                update_fields.append('password = ?')
                params.append(crypto.encrypt(password))
            if port is not None:
                update_fields.append('port = ?')
                params.append(port)

            if not update_fields:
                conn.close()
                return False

            update_fields.append('updated_at = ?')
            params.append(now)
            params.append(device_id)

            query = 'UPDATE devices SET {} WHERE id = ?'.format(', '.join(update_fields))
            cursor.execute(query, params)
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return affected > 0
        except Exception as e:
            print(f"更新设备错误: {str(e)}")
            return False

    def delete_device(self, device_id):
        """删除设备"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM devices WHERE id = ?', (device_id,))
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return affected > 0
        except Exception as e:
            print(f"删除设备错误: {str(e)}")
            return False

    def add_patrol_record(self, task_id, ip, manufacturer, template_name, success, log_path):
        """新增巡检记录（如已存在相同task_id+ip则更新）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 先查是否已有记录
            cursor.execute(
                'SELECT id FROM patrol_history WHERE task_id = ? AND ip = ?',
                (task_id, ip)
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    'UPDATE patrol_history SET success = ?, log_path = ?, manufacturer = ?, template_name = ?, created_at = ? WHERE id = ?',
                    (1 if success else 0, log_path, manufacturer, template_name, now, existing[0])
                )
                record_id = existing[0]
            else:
                cursor.execute(
                    'INSERT INTO patrol_history (task_id, ip, manufacturer, template_name, success, log_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (task_id, ip, manufacturer, template_name, 1 if success else 0, log_path, now)
                )
                record_id = cursor.lastrowid

            conn.commit()
            conn.close()
            return record_id
        except Exception as e:
            print(f"新增巡检记录错误: {str(e)}")
            return None

    def get_patrol_list(self, task_id=None, ip=None, page=1, page_size=20):
        """获取巡检历史列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = 'SELECT id, task_id, ip, manufacturer, template_name, success, log_path, created_at FROM patrol_history WHERE 1=1'
            count_query = 'SELECT COUNT(*) FROM patrol_history WHERE 1=1'
            params = []

            if task_id:
                query += ' AND task_id = ?'
                count_query += ' AND task_id = ?'
                params.append(task_id)

            if ip:
                query += ' AND ip LIKE ?'
                count_query += ' AND ip LIKE ?'
                params.append(f'%{ip}%')

            # 查询总数
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # 分页查询
            query += ' ORDER BY id DESC LIMIT ? OFFSET ?'
            params.append(page_size)
            params.append((page - 1) * page_size)

            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.close()

            records = []
            for row in result:
                records.append({
                    "id": row[0],
                    "task_id": row[1],
                    "ip": row[2],
                    "manufacturer": row[3],
                    "template_name": row[4],
                    "success": bool(row[5]),
                    "log_path": row[6],
                    "created_at": row[7]
                })

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "records": records
            }
        except Exception as e:
            print(f"获取巡检历史列表错误: {str(e)}")
            return {"total": 0, "page": page, "page_size": page_size, "records": []}

    def delete_devices_batch(self, device_ids):
        """批量删除设备"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in device_ids])
            cursor.execute(
                f'DELETE FROM devices WHERE id IN ({placeholders})',
                device_ids
            )
            conn.commit()
            deleted = cursor.rowcount
            conn.close()
            return deleted
        except Exception as e:
            print(f"批量删除设备错误: {str(e)}")
            return 0

    def delete_patrol_tasks(self, task_ids):
        """批量删除巡检任务（含所有设备记录）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in task_ids])
            cursor.execute(
                f'DELETE FROM patrol_history WHERE task_id IN ({placeholders})',
                task_ids
            )
            conn.commit()
            deleted = cursor.rowcount
            conn.close()
            return deleted
        except Exception as e:
            print(f"删除巡检任务错误: {str(e)}")
            return 0

    def get_patrol_detail(self, record_id):
        """获取巡检历史详情"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT id, task_id, ip, manufacturer, template_name, success, log_path, created_at FROM patrol_history WHERE id = ?',
                (record_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "id": row[0],
                    "task_id": row[1],
                    "ip": row[2],
                    "manufacturer": row[3],
                    "template_name": row[4],
                    "success": bool(row[5]),
                    "log_path": row[6],
                    "created_at": row[7]
                }
            return None
        except Exception as e:
            print(f"获取巡检历史详情错误: {str(e)}")
            return None


db = Database()

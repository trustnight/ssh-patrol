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
                    device_type TEXT DEFAULT '',
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
                    sort_order INTEGER DEFAULT 0,
                    manufacturer TEXT,
                    device_type TEXT DEFAULT '',
                    ip TEXT,
                    username TEXT,
                    password TEXT,
                    port INTEGER DEFAULT 22,
                    url TEXT DEFAULT '',
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')

            # 兼容旧数据库：为devices表添加缺失列（如果不存在）
            for col, col_type, col_default in [
                ('url', "TEXT", "''"),
                ('sort_order', "INTEGER", '0'),
                ('device_type', "TEXT", "''"),
            ]:
                try:
                    cursor.execute(f'ALTER TABLE devices ADD COLUMN {col} {col_type} DEFAULT {col_default}')
                except sqlite3.OperationalError:
                    pass  # 列已存在

            # 兼容旧数据库：为commands表添加device_type列
            try:
                cursor.execute("ALTER TABLE commands ADD COLUMN device_type TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass  # 列已存在

            # 迁移旧数据：将内置模板中 device_type='' 的记录统一归类为 FW（防火墙）
            cursor.execute(
                "UPDATE commands SET device_type = 'FW' WHERE is_custom = 0 AND (device_type = '' OR device_type IS NULL)"
            )
            print("旧内置指令已归类到 FW 设备类型")

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

            # 创建截图URL表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS screenshot_urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    ip TEXT,
                    is_active INTEGER DEFAULT 0,
                    created_at TEXT
                )
            ''')

            # 创建截图历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS screenshot_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    ip TEXT,
                    file_path TEXT,
                    created_at TEXT
                )
            ''')

            # 创建截图任务表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS screenshot_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    created_at TEXT
                )
            ''')

            # 创建截图任务设备关联表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS screenshot_task_devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    url_id INTEGER,
                    url TEXT,
                    ip TEXT,
                    status TEXT DEFAULT 'pending',
                    screenshot_count INTEGER DEFAULT 0,
                    sort_order INTEGER DEFAULT 0,
                    FOREIGN KEY (task_id) REFERENCES screenshot_tasks(id)
                )
            ''')

            # ══════════════════════════════════════════════════
            #  终端连接历史表
            # ══════════════════════════════════════════════════
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS terminal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL,
                    port TEXT DEFAULT '22',
                    username TEXT,
                    protocol TEXT DEFAULT 'ssh',
                    connected_at TEXT NOT NULL
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
                            'INSERT INTO commands (template_id, template_name, manufacturer, device_type, command, cmd_order, is_custom) VALUES (?, ?, ?, ?, ?, ?, ?)',
                            (template_id, template_name, manufacturer, 'FW', cmd, cmd_order, 0)
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

    def get_cmd_template(self, template_name, manufacturer, device_type=''):
        """获取命令模板（必须指定设备类型才能匹配指令）

        匹配策略：
          1. device_type 为空 → 返回空列表（未绑定设备类型则不允许巡检）
          2. device_type 非空 → 精确匹配 template_name + manufacturer + device_type
        """
        if not device_type:
            print(f"巡检警告: 设备厂商={manufacturer}, 模板={template_name}，未指定设备类型，跳过命令匹配")
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT command FROM commands WHERE template_name = ? AND LOWER(manufacturer) = LOWER(?) AND LOWER(device_type) = LOWER(?) ORDER BY cmd_order',
                (template_name, manufacturer, device_type)
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

    def get_template_manufacturers(self, template_name, device_type=''):
        """获取指定模板支持的厂商列表

        Args:
            template_name: 模板名称
            device_type: 设备类型筛选（可选）
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if device_type:
                cursor.execute(
                    'SELECT DISTINCT manufacturer FROM commands WHERE template_name = ? AND device_type = ? ORDER BY manufacturer',
                    (template_name, device_type)
                )
            else:
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

    def get_template_commands(self, template_name, manufacturer, device_type=''):
        """获取模板命令列表（带详细信息）

        Args:
            template_name: 模板名称
            manufacturer: 设备厂商
            device_type: 设备类型（可选）
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if device_type:
                cursor.execute(
                    'SELECT id, command, cmd_order, is_custom, device_type FROM commands WHERE template_name = ? AND LOWER(manufacturer) = LOWER(?) AND LOWER(device_type) = LOWER(?) ORDER BY cmd_order',
                    (template_name, manufacturer, device_type)
                )
            else:
                # 模板管理页面未选设备类型时，不显示任何命令（巡检流程走 get_cmd_template，不受影响）
                conn.close()
                return []
            result = cursor.fetchall()
            conn.close()

            return [
                {
                    "id": row[0],
                    "command": row[1],
                    "cmd_order": row[2],
                    "is_custom": bool(row[3]),
                    "device_type": row[4] if len(row) > 4 else ''
                }
                for row in result
            ]
        except Exception as e:
            print(f"获取模板命令错误: {str(e)}")
            return []

    def save_custom_template(self, template_name, manufacturer, commands, device_type=''):
        """保存自定义模板命令

        Args:
            template_name: 模板名称
            manufacturer: 设备厂商
            commands: 命令列表
            device_type: 设备类型（可选）
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'DELETE FROM commands WHERE template_name = ? AND LOWER(manufacturer) = LOWER(?) AND is_custom = 1 AND device_type = ?',
                (template_name, manufacturer, device_type or '')
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
                    'INSERT INTO commands (template_id, template_name, manufacturer, device_type, command, cmd_order, is_custom) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (template_id, template_name, manufacturer, device_type or '', cmd, cmd_order, 1)
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

    def add_device(self, manufacturer, ip, username, password, port=22, url='', sort_order=0, device_type=''):
        """新增/更新设备（IP重复时自动更新已有记录）

        Returns:
            (device_id, 'insert') 或 (device_id, 'update') 或 (None, None)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            encrypted_password = crypto.encrypt(password) if not crypto.is_encrypted(password) else password

            # 检查IP是否已存在
            cursor.execute('SELECT id FROM devices WHERE ip = ?', (ip,))
            existing = cursor.fetchone()

            if existing:
                # IP已存在 → 更新所有字段
                device_id = existing[0]
                cursor.execute(
                    'UPDATE devices SET sort_order=?, manufacturer=?, device_type=?, username=?, password=?, port=?, url=?, updated_at=? WHERE id=?',
                    (sort_order, manufacturer, device_type or '', username, encrypted_password, port, url or '', now, device_id)
                )
                conn.commit()
                conn.close()
                return (device_id, 'update')
            else:
                # 新设备 → 插入
                cursor.execute(
                    'INSERT INTO devices (sort_order, manufacturer, device_type, ip, username, password, port, url, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (sort_order, manufacturer, device_type or '', ip, username, encrypted_password, port, url or '', now, now)
                )
                conn.commit()
                device_id = cursor.lastrowid
                conn.close()
                return (device_id, 'insert')
        except Exception as e:
            print(f"新增设备错误: {str(e)}")
            return (None, None)

    def get_devices(self, keyword=None, manufacturer=None):
        """获取设备列表（按序号排序）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = 'SELECT id, sort_order, manufacturer, device_type, ip, username, password, port, url, created_at, updated_at FROM devices WHERE 1=1'
            params = []

            if keyword:
                query += ' AND (ip LIKE ? OR username LIKE ?)'
                keyword_pattern = f'%{keyword}%'
                params.append(keyword_pattern)
                params.append(keyword_pattern)

            if manufacturer:
                query += ' AND manufacturer = ?'
                params.append(manufacturer)

            query += ' ORDER BY sort_order ASC, id ASC'

            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.close()

            devices = []
            for row in result:
                devices.append({
                    "id": row[0],
                    "sort_order": row[1] or 0,
                    "manufacturer": row[2],
                    "device_type": row[3] or '',
                    "ip": row[4],
                    "username": row[5],
                    "password": row[6],
                    "port": row[7],
                    "url": row[8] or '',
                    "created_at": row[9],
                    "updated_at": row[10]
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
                'SELECT id, sort_order, manufacturer, device_type, ip, username, password, port, url, created_at, updated_at FROM devices WHERE id = ?',
                (device_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "id": row[0],
                    "sort_order": row[1] or 0,
                    "manufacturer": row[2],
                    "device_type": row[3] or '',
                    "ip": row[4],
                    "username": row[5],
                    "password": row[6],
                    "port": row[7],
                    "url": row[8] or '',
                    "created_at": row[9],
                    "updated_at": row[10]
                }
            return None
        except Exception as e:
            print(f"获取设备详情错误: {str(e)}")
            return None

    def update_device(self, device_id, manufacturer=None, ip=None, username=None, password=None, port=None, url=None, sort_order=None, device_type=None):
        """更新设备信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            update_fields = []
            params = []

            if sort_order is not None:
                update_fields.append('sort_order = ?')
                params.append(sort_order)
            if manufacturer is not None:
                update_fields.append('manufacturer = ?')
                params.append(manufacturer)
            if device_type is not None:
                update_fields.append('device_type = ?')
                params.append(device_type)
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
            if url is not None:
                update_fields.append('url = ?')
                params.append(url)

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

    # ==================== 截图相关方法 ====================

    def get_devices_with_url(self):
        """获取有URL的设备列表（供截图功能使用）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, manufacturer, ip, username, port, url FROM devices WHERE url IS NOT NULL AND url != '' ORDER BY id"
            )
            result = cursor.fetchall()
            conn.close()

            devices = []
            for row in result:
                devices.append({
                    "id": row[0],
                    "manufacturer": row[1],
                    "ip": row[2],
                    "username": row[3],
                    "port": row[4],
                    "url": row[5]
                })
            return devices
        except Exception as e:
            print(f"获取带URL设备列表错误: {str(e)}")
            return []

    def add_screenshot_urls(self, urls):
        """批量添加截图URL"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            for url in urls:
                # 从URL提取IP
                ip = self._extract_ip_from_url(url)
                cursor.execute(
                    'INSERT INTO screenshot_urls (url, ip, is_active, created_at) VALUES (?, ?, 0, ?)',
                    (url, ip, now)
                )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"添加截图URL错误: {str(e)}")
            return False

    def get_screenshot_urls(self):
        """获取所有截图URL"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT id, url, ip, is_active, created_at FROM screenshot_urls ORDER BY id')
            result = cursor.fetchall()
            conn.close()

            urls = []
            for row in result:
                urls.append({
                    "id": row[0],
                    "url": row[1],
                    "ip": row[2],
                    "is_active": bool(row[3]),
                    "created_at": row[4]
                })
            return urls
        except Exception as e:
            print(f"获取截图URL列表错误: {str(e)}")
            return []

    def clear_screenshot_urls(self):
        """清空截图URL列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM screenshot_urls')
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"清空截图URL列表错误: {str(e)}")
            return False

    def set_active_screenshot_url(self, url_id):
        """设置活跃的截图URL"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 先将所有URL设为非活跃
            cursor.execute('UPDATE screenshot_urls SET is_active = 0')

            # 设置指定URL为活跃
            cursor.execute('UPDATE screenshot_urls SET is_active = 1 WHERE id = ?', (url_id,))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"设置活跃截图URL错误: {str(e)}")
            return False

    def get_active_screenshot_url(self):
        """获取当前活跃的截图URL"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT id, url, ip FROM screenshot_urls WHERE is_active = 1 LIMIT 1')
            row = cursor.fetchone()
            conn.close()

            if row:
                return {"id": row[0], "url": row[1], "ip": row[2]}
            return None
        except Exception as e:
            print(f"获取活跃截图URL错误: {str(e)}")
            return None

    def add_screenshot_record(self, url, ip, file_path):
        """添加截图记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute(
                'INSERT INTO screenshot_history (url, ip, file_path, created_at) VALUES (?, ?, ?, ?)',
                (url, ip, file_path, now)
            )

            conn.commit()
            record_id = cursor.lastrowid
            conn.close()
            return record_id
        except Exception as e:
            print(f"添加截图记录错误: {str(e)}")
            return None

    def get_screenshot_history(self, ip=None):
        """获取截图历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = 'SELECT id, url, ip, file_path, created_at FROM screenshot_history WHERE 1=1'
            params = []

            if ip:
                query += ' AND ip LIKE ?'
                params.append(f'%{ip}%')

            query += ' ORDER BY id DESC'

            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.close()

            records = []
            for row in result:
                records.append({
                    "id": row[0],
                    "url": row[1],
                    "ip": row[2],
                    "file_path": row[3],
                    "created_at": row[4]
                })
            return records
        except Exception as e:
            print(f"获取截图历史错误: {str(e)}")
            return []

    def get_screenshot_count_by_ip(self, ip):
        """获取指定IP的截图数量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM screenshot_history WHERE ip = ?', (ip,))
            count = cursor.fetchone()[0]
            conn.close()

            return count
        except Exception as e:
            print(f"获取截图数量错误: {str(e)}")
            return 0

    def clear_screenshot_history(self):
        """清空截图历史（返回所有文件路径供删除本地文件）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 先获取所有文件路径
            cursor.execute('SELECT file_path FROM screenshot_history')
            file_paths = [row[0] for row in cursor.fetchall()]

            # 清空表
            cursor.execute('DELETE FROM screenshot_history')
            conn.commit()
            conn.close()

            return file_paths
        except Exception as e:
            print(f"清空截图历史错误: {str(e)}")
            return []

    def delete_screenshot_record(self, record_id):
        """删除单条截图历史（返回文件路径供清理本地文件）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT file_path FROM screenshot_history WHERE id = ?', (record_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None

            file_path = row[0]
            cursor.execute('DELETE FROM screenshot_history WHERE id = ?', (record_id,))
            conn.commit()
            conn.close()
            return file_path
        except Exception as e:
            print(f"删除截图记录错误: {str(e)}")
            return None

    # ==================== 截图任务方法 ====================

    def create_screenshot_task(self, name, device_ids):
        """创建截图任务（从devices表获取设备URL和IP）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute(
                'INSERT INTO screenshot_tasks (name, created_at) VALUES (?, ?)',
                (name, now)
            )
            task_id = cursor.lastrowid

            # 从devices表获取选中设备的URL和IP信息
            for order, device_id in enumerate(device_ids):
                cursor.execute(
                    'SELECT ip, url FROM devices WHERE id = ?', (device_id,)
                )
                row = cursor.fetchone()
                if row and row[1]:  # url不为空才添加
                    cursor.execute(
                        'INSERT INTO screenshot_task_devices (task_id, url_id, url, ip, status, screenshot_count, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (task_id, device_id, row[1], row[0], 'pending', 0, order)
                    )

            conn.commit()
            conn.close()
            return task_id
        except Exception as e:
            print(f"创建截图任务错误: {str(e)}")
            return None

    def append_devices_to_task(self, task_id, device_ids):
        """向截图任务追加设备，过滤掉已存在的设备"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 查询任务中已有的设备 url_id（url_id 对应 devices.id）
            cursor.execute(
                'SELECT url_id FROM screenshot_task_devices WHERE task_id = ?',
                (task_id,)
            )
            existing_ids = {row[0] for row in cursor.fetchall()}

            # 过滤掉已存在的设备
            new_device_ids = [did for did in device_ids if did not in existing_ids]
            if not new_device_ids:
                conn.close()
                return {'added': 0, 'skipped': len(device_ids)}

            # 获取当前最大 sort_order
            cursor.execute(
                'SELECT COALESCE(MAX(sort_order), 0) FROM screenshot_task_devices WHERE task_id = ?',
                (task_id,)
            )
            max_order = cursor.fetchone()[0]

            added_count = 0
            for order, device_id in enumerate(new_device_ids, start=max_order + 1):
                cursor.execute(
                    'SELECT ip, url FROM devices WHERE id = ?', (device_id,)
                )
                row = cursor.fetchone()
                if row and row[1]:  # url 不为空才添加
                    cursor.execute(
                        'INSERT INTO screenshot_task_devices (task_id, url_id, url, ip, status, screenshot_count, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (task_id, device_id, row[1], row[0], 'pending', 0, order)
                    )
                    added_count += 1

            conn.commit()
            conn.close()
            return {'added': added_count, 'skipped': len(device_ids) - added_count}
        except Exception as e:
            print(f"追加截图任务设备错误: {str(e)}")
            return None

    def get_screenshot_tasks(self):
        """获取截图任务列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT id, name, created_at FROM screenshot_tasks ORDER BY id DESC')
            result = cursor.fetchall()
            conn.close()

            tasks = []
            for row in result:
                tasks.append({
                    "id": row[0],
                    "name": row[1],
                    "created_at": row[2]
                })
            return tasks
        except Exception as e:
            print(f"获取截图任务列表错误: {str(e)}")
            return []

    def get_screenshot_task_devices(self, task_id):
        """获取截图任务的设备列表（按状态排序：active→pending→done）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, url_id, url, ip, status, screenshot_count, sort_order
                FROM screenshot_task_devices
                WHERE task_id = ?
                ORDER BY
                    CASE status
                        WHEN 'active' THEN 0
                        WHEN 'pending' THEN 1
                        WHEN 'done' THEN 2
                    END,
                    sort_order
            ''', (task_id,))
            result = cursor.fetchall()
            conn.close()

            devices = []
            for row in result:
                devices.append({
                    "id": row[0],
                    "url_id": row[1],
                    "url": row[2],
                    "ip": row[3],
                    "status": row[4],
                    "screenshot_count": row[5],
                    "sort_order": row[6]
                })
            return devices
        except Exception as e:
            print(f"获取截图任务设备列表错误: {str(e)}")
            return []

    def set_active_task_device(self, task_id, device_id):
        """设置当前活跃设备：将当前active改为done，新设备设为active"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 将当前active设备改为done
            cursor.execute(
                "UPDATE screenshot_task_devices SET status = 'done' WHERE task_id = ? AND status = 'active'",
                (task_id,)
            )

            # 获取当前最大sort_order（done的排最后）
            cursor.execute(
                'SELECT COALESCE(MAX(sort_order), 0) FROM screenshot_task_devices WHERE task_id = ?',
                (task_id,)
            )
            max_order = cursor.fetchone()[0]

            # 将新设备设为active，sort_order放到最前
            cursor.execute(
                "UPDATE screenshot_task_devices SET status = 'active', sort_order = -1 WHERE id = ? AND task_id = ?",
                (device_id, task_id)
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"设置活跃设备错误: {str(e)}")
            return False

    def complete_task_device(self, task_id, device_id):
        """将设备标记为完成并移到最后"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT COALESCE(MAX(sort_order), 0) FROM screenshot_task_devices WHERE task_id = ?',
                (task_id,)
            )
            max_order = cursor.fetchone()[0]

            cursor.execute(
                "UPDATE screenshot_task_devices SET status = 'done', sort_order = ? WHERE id = ? AND task_id = ?",
                (max_order + 1, device_id, task_id)
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"完成设备错误: {str(e)}")
            return False

    def increment_task_device_count(self, task_id, device_id):
        """设备截图计数+1"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'UPDATE screenshot_task_devices SET screenshot_count = screenshot_count + 1 WHERE id = ? AND task_id = ?',
                (device_id, task_id)
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"更新截图计数错误: {str(e)}")
            return False

    def get_task_device_by_id(self, device_id):
        """获取任务设备详情"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT id, task_id, url_id, url, ip, status, screenshot_count FROM screenshot_task_devices WHERE id = ?',
                (device_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "id": row[0],
                    "task_id": row[1],
                    "url_id": row[2],
                    "url": row[3],
                    "ip": row[4],
                    "status": row[5],
                    "screenshot_count": row[6]
                }
            return None
        except Exception as e:
            print(f"获取任务设备详情错误: {str(e)}")
            return None

    def delete_screenshot_task(self, task_id):
        """删除截图任务及关联设备"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM screenshot_task_devices WHERE task_id = ?', (task_id,))
            cursor.execute('DELETE FROM screenshot_tasks WHERE id = ?', (task_id,))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"删除截图任务错误: {str(e)}")
            return False

    def _extract_ip_from_url(self, url):
        """从URL中提取IP地址"""
        try:
            # 移除协议前缀
            url = url.replace('https://', '').replace('http://', '')
            # 移除端口号和路径
            ip = url.split(':')[0].split('/')[0]
            return ip
        except Exception:
            return ''
    
    # ==================== 终端连接历史 ====================
    
    def add_terminal_history(self, ip, port="22", username="", protocol="ssh"):
        """添加终端连接历史（去重：同ip+port只保留最新一条）"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # 先删除旧记录（同ip+port）
        cursor.execute(
            "DELETE FROM terminal_history WHERE ip = ? AND port = ?",
            (ip, port)
        )
        # 插入新记录
        cursor.execute(
            "INSERT INTO terminal_history (ip, port, username, protocol, connected_at) VALUES (?, ?, ?, ?, ?)",
            (ip, port, username, protocol, now)
        )
        conn.commit()
        conn.close()
    
    def get_terminal_history(self, limit=20):
        """获取终端连接历史（最近优先）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, ip, port, username, protocol, connected_at FROM terminal_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": r[0], "ip": r[1], "port": r[2],
                "username": r[3], "protocol": r[4], "connected_at": r[5]
            }
            for r in rows
        ]
    
    def clear_terminal_history(self):
        """清空终端连接历史"""
        conn = sqlite3.connect(self.db_path)
        conn.cursor().execute("DELETE FROM terminal_history")
        conn.commit()
        conn.close()


db = Database()

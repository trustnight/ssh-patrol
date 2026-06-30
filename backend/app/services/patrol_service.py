# -*- coding: utf-8 -*-
"""
设备巡检服务模块
"""
import os
import time
import re
import asyncio
import paramiko
import asyncssh
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.database import db
from app.crypto_utils import crypto
from app.config import settings
from app.telnet_utils import SimpleTelnet


class PatrolService:
    """设备巡检服务类"""

    @staticmethod
    def _patrol_via_telnet(ip, port, username, password, manufacturer, device_type, template_name,
                           append_output_func=None, update_progress_func=None, output_lock=None):
        """通过 Telnet 巡检单个设备

        Args:
            ip: 设备IP
            port: Telnet端口（23）
            username: 用户名
            password: 密码
            manufacturer: 设备厂商
            template_name: 命令模板名称
            append_output_func: 输出函数
            update_progress_func: 进度更新函数
            output_lock: 线程锁

        Returns:
            tuple: (success, cmd_results, error_msg)
        """
        def safe_output(text):
            if append_output_func:
                if output_lock:
                    with output_lock:
                        append_output_func(text)
                else:
                    append_output_func(text)

        cmd_results = []
        tn = None

        try:
            safe_output(f"开始 Telnet 登录设备: {ip}:{port}\n")
            safe_output(f"用户名: {username}\n")
            safe_output(f"命令模板: {template_name}\n")
            safe_output(f"设备厂商: {manufacturer}\n")
            safe_output(f"设备类型: {device_type or '通用'}\n")

            decrypted_password = crypto.decrypt(password) if crypto.is_encrypted(password) else password

            tn = SimpleTelnet(ip, port, timeout=15)
            tn.connect()
            safe_output("Telnet 连接成功，等待登录提示...\n")

            # 等待登录提示（缩短timeout加速）
            login_output = tn.read_until(":", timeout=5)
            safe_output(f"收到提示: {login_output[-80:]}\n")

            # 发送用户名
            tn.write(username + "\r\n")
            safe_output(f"已发送用户名: {username}\n")

            # 等待密码提示
            pass_prompt = tn.read_until(":", timeout=3)
            safe_output(f"收到密码提示\n")

            # 发送密码
            tn.write(decrypted_password + "\r\n")
            safe_output("已发送密码\n")

            # 等待登录完成，读取欢迎信息（缩短等待）
            time.sleep(0.3)
            welcome = tn.read_very_eager()
            if welcome:
                safe_output("登录成功！\n")

            # 获取命令提示符
            tn.write("\r\n")
            time.sleep(0.2)
            prompt_data = tn.read_very_eager()
            lines = prompt_data.strip().split('\n')
            # 尝试从输出中提取提示符（通常是最后一行非空内容）
            command_prompt = None
            for line in reversed(lines):
                line = line.strip()
                if line and len(line) < 80 and (line.endswith('>') or line.endswith('#') or line.endswith(']')):
                    command_prompt = line
                    break
            if command_prompt:
                safe_output(f"获取到命令提示符: {command_prompt}\n")

            cmd_list = db.get_cmd_template(template_name, manufacturer, device_type)

            if not cmd_list:
                safe_output(f"错误: 未找到厂商 [{manufacturer}] 设备类型 [{device_type}] 在模板 [{template_name}] 中的巡检命令\n")
                return False, [], f"模板 [{template_name}] 中没有厂商 [{manufacturer}] 设备类型 [{device_type}] 的巡检命令，请检查命令模板配置"

            # 执行前置命令
            pre_commands = db.get_manufacturer_commands(manufacturer, "pre")
            for cmd in pre_commands:
                safe_output(f"执行前置命令: {cmd}\n")
                tn.write(cmd + "\r\n")
                time.sleep(0.3)
                output = tn.read_very_eager()

            # 执行巡检命令
            for i, cmd in enumerate(cmd_list):
                safe_output(f"执行命令 {i+1}/{len(cmd_list)}: {cmd}\n")
                tn.write(cmd + "\r\n")
                time.sleep(0.8)
                output = tn.read_very_eager()
                error = ""

                if output:
                    # 清理输出：去除命令回显
                    if cmd in output:
                        cmd_idx = output.find(cmd)
                        end_idx = cmd_idx + len(cmd)
                        while end_idx < len(output) and output[end_idx] in '\r\n':
                            end_idx += 1
                        output = output[end_idx:]
                    # 清理空行
                    lines_out = output.split('\n')
                    cleaned = [l.strip() for l in lines_out if l.strip()]
                    output = '\n'.join(cleaned)

                cmd_results.append((cmd, output, error))

                if update_progress_func:
                    update_progress_func(i + 1, len(cmd_list))

            # 执行后置命令
            post_commands = db.get_manufacturer_commands(manufacturer, "post")
            for cmd in post_commands:
                safe_output(f"执行后置命令: {cmd}\n")
                tn.write(cmd + "\r\n")
                time.sleep(0.3)
                tn.read_very_eager()

            safe_output("Telnet 巡检完成！\n")
            return True, cmd_results, ""

        except Exception as e:
            error_msg = str(e)
            safe_output(f"Telnet 巡检错误: {error_msg}\n")
            return False, cmd_results, error_msg
        finally:
            if tn:
                try:
                    tn.close()
                except Exception:
                    pass

    @staticmethod
    def patrol_single_device(ip, port, username, password, manufacturer, device_type, template_name,
                             append_output_func=None, update_progress_func=None, output_lock=None):
        """巡检单个设备的核心逻辑（自动识别SSH/Telnet）

        Args:
            ip: 设备IP
            port: 端口（23=Telnet，其他=SSH）
            ...同原有参数

        Returns:
            tuple: (success: bool, results: list, error_msg: str)
        """
        # 端口23 → 使用 Telnet
        if int(port) == 23:
            return PatrolService._patrol_via_telnet(
                ip, port, username, password, manufacturer, device_type, template_name,
                append_output_func, update_progress_func, output_lock
            )

        def safe_output(text):
            if append_output_func:
                if output_lock:
                    with output_lock:
                        append_output_func(text)
                else:
                    append_output_func(text)

        cmd_results = []

        try:
            safe_output(f"开始登录设备: {ip}:{port}\n")
            safe_output(f"用户名: {username}\n")
            safe_output(f"命令模板: {template_name}\n")
            safe_output(f"设备厂商: {manufacturer}\n")
            safe_output(f"设备类型: {device_type or '通用'}\n")

            decrypted_password = crypto.decrypt(password) if crypto.is_encrypted(password) else password

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(ip, port=port, username=username, password=decrypted_password, timeout=15)

            safe_output("登录成功！\n")
            safe_output("开始执行巡检命令...\n")

            cmd_list = db.get_cmd_template(template_name, manufacturer, device_type)

            if not cmd_list:
                safe_output(f"错误: 未找到厂商 [{manufacturer}] 设备类型 [{device_type}] 在模板 [{template_name}] 中的巡检命令\n")
                return False, [], f"模板 [{template_name}] 中没有厂商 [{manufacturer}] 设备类型 [{device_type}] 的巡检命令，请检查命令模板配置"

            try:
                shell = client.invoke_shell()
                shell.settimeout(30.0)

                time.sleep(0.2)

                while shell.recv_ready():
                    shell.recv(1024)

                def get_command_prompt(shell, timeout=5):
                    """获取设备的命令提示符"""
                    prompts = []

                    shell.send('\n')
                    time.sleep(0.2)

                    output = ""
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        if shell.recv_ready():
                            data = shell.recv(1024).decode('utf-8', errors='ignore')
                            output += data
                        else:
                            break

                    lines = output.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.endswith('\r'):
                            prompts.append(line)

                    if prompts:
                        return prompts[-1]
                    return None

                def read_until_prompt(shell, prompt, timeout=30):
                    """读取输出直到遇到命令提示符"""
                    output = ""
                    start_time = time.time()
                    last_activity_time = time.time()
                    prompt_found = False

                    while time.time() - start_time < timeout:
                        if shell.recv_ready():
                            data = shell.recv(4096).decode('utf-8', errors='ignore')
                            output += data
                            last_activity_time = time.time()

                            if prompt and prompt in output:
                                prompt_found = True
                                check_start = time.time()
                                while time.time() - check_start < 0.3:
                                    if shell.recv_ready():
                                        data = shell.recv(4096).decode('utf-8', errors='ignore')
                                        output += data
                                        last_activity_time = time.time()
                                prompt_index = output.rfind(prompt)
                                return output[:prompt_index]

                        if time.time() - last_activity_time > 2:
                            break

                        time.sleep(0.05)

                    return output

                command_prompt = get_command_prompt(shell)
                if command_prompt:
                    safe_output(f"获取到命令提示符: {command_prompt}\n")

                pre_commands = db.get_manufacturer_commands(manufacturer, "pre")
                for cmd in pre_commands:
                    safe_output(f"执行前置命令: {cmd}\n")
                    shell.send(cmd + '\n')
                    output = read_until_prompt(shell, command_prompt)
                    while shell.recv_ready():
                        shell.recv(1024)

                for i, cmd in enumerate(cmd_list):
                    safe_output(f"执行命令 {i+1}/{len(cmd_list)}: {cmd}\n")

                    shell.send(cmd + '\n')

                    output = read_until_prompt(shell, command_prompt)
                    error = ""

                    if output:
                        cmd_index = output.find(cmd)
                        if cmd_index != -1:
                            end_index = cmd_index + len(cmd)
                            while end_index < len(output) and output[end_index] in '\r\n':
                                end_index += 1
                            output = output[end_index:]
                        lines = output.split('\n')
                        cleaned_lines = []
                        for line in lines:
                            stripped_line = line.strip()
                            if stripped_line:
                                cleaned_lines.append(stripped_line)
                        output = '\n'.join(cleaned_lines)
                        while '\n\n' in output:
                            output = output.replace('\n\n', '\n')

                    cmd_results.append((cmd, output, error))

                    if update_progress_func:
                        update_progress_func(i+1, len(cmd_list))

                    while shell.recv_ready():
                        shell.recv(4096)

                post_commands = db.get_manufacturer_commands(manufacturer, "post")
                for cmd in post_commands:
                    safe_output(f"执行后置命令: {cmd}\n")
                    shell.send(cmd + '\n')
                    output = read_until_prompt(shell, command_prompt)
                    if output:
                        cmd_index = output.find(cmd)
                        if cmd_index != -1:
                            end_index = cmd_index + len(cmd)
                            while end_index < len(output) and output[end_index] in '\r\n':
                                end_index += 1
                            output = output[end_index:]
                        lines = output.split('\n')
                        cleaned_lines = []
                        for line in lines:
                            stripped_line = line.strip()
                            if stripped_line:
                                cleaned_lines.append(stripped_line)
                        output = '\n'.join(cleaned_lines)
                        while '\n\n' in output:
                            output = output.replace('\n\n', '\n')
                        if output:
                            safe_output(f"后置命令输出:\n{output}\n")
                    while shell.recv_ready():
                        shell.recv(1024)

                shell.close()
            except Exception as e:
                safe_output(f"执行命令错误: {str(e)}\n")
                output = ""
                error = str(e)
                cmd_results.append(("执行命令失败", output, error))

            client.close()

            safe_output("巡检完成！\n")

            return True, cmd_results, ""

        except Exception as e:
            error_msg = str(e)
            safe_output(f"登录或执行命令错误: {error_msg}\n")
            return False, cmd_results, error_msg

    @staticmethod
    async def patrol_single_device_asyncssh(ip, port, username, password, manufacturer, device_type, template_name, append_output_func=None):
        """巡检单个设备（asyncssh异步版本）

        Args:
            ip: 设备IP
            port: SSH端口
            username: 用户名
            password: 密码
            manufacturer: 设备厂商
            template_name: 命令模板名称
            append_output_func: 输出函数

        Returns:
            tuple: (success: bool, results: list, error_msg: str)
        """
        def safe_output(text):
            if append_output_func:
                append_output_func(text)

        cmd_results = []

        try:
            safe_output(f"开始登录设备: {ip}:{port}\n")
            safe_output(f"用户名: {username}\n")
            safe_output(f"命令模板: {template_name}\n")
            safe_output(f"设备厂商: {manufacturer}\n")
            safe_output(f"设备类型: {device_type or '通用'}\n")

            decrypted_password = crypto.decrypt(password) if crypto.is_encrypted(password) else password

            conn = await asyncssh.connect(
                ip,
                port=port,
                username=username,
                password=decrypted_password,
                known_hosts=None,
                encoding='utf-8'
            )

            try:
                safe_output("登录成功！\n")
                safe_output("开始执行巡检命令...\n")

                cmd_list = db.get_cmd_template(template_name, manufacturer, device_type)

                if not cmd_list:
                    safe_output(f"错误: 未找到厂商 [{manufacturer}] 在模板 [{template_name}] 中的巡检命令\n")
                    return False, [], f"模板 [{template_name}] 中没有厂商 [{manufacturer}] 的巡检命令，请检查命令模板配置"

                process = await conn.create_process(term_type='xterm', term_size=(80, 24))
                stdin = process.stdin
                stdout = process.stdout

                async def read_until_prompt(prompt, timeout=30):
                    output = ""
                    start_time = time.time()
                    last_activity_time = time.time()

                    while time.time() - start_time < timeout:
                        try:
                            data = await asyncio.wait_for(stdout.read(4096), timeout=0.2)
                        except asyncio.TimeoutError:
                            data = ""

                        if data:
                            output += data
                            last_activity_time = time.time()

                            lower_output = output.lower()
                            if '--more--' in lower_output or '---- more ----' in lower_output or '\nmore' in lower_output or '\rmore' in lower_output:
                                stdin.write(' ')
                                await stdin.drain()
                                output = output.replace('--More--', '').replace('---- More ----', '')

                            if prompt and prompt in output:
                                check_start = time.time()
                                while time.time() - check_start < 0.3:
                                    try:
                                        extra = await asyncio.wait_for(stdout.read(4096), timeout=0.1)
                                    except asyncio.TimeoutError:
                                        extra = ""
                                    if extra:
                                        output += extra
                                        last_activity_time = time.time()
                                    else:
                                        break
                                prompt_index = output.rfind(prompt)
                                return output[:prompt_index]

                        if time.time() - last_activity_time > 2:
                            break

                    return output

                async def get_command_prompt(timeout=5):
                    stdin.write('\n')
                    await stdin.drain()
                    output = ""
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        try:
                            data = await asyncio.wait_for(stdout.read(4096), timeout=0.2)
                        except asyncio.TimeoutError:
                            data = ""
                        if data:
                            output += data
                        else:
                            break

                    lines = output.strip().replace('\r', '\n').split('\n')
                    prompts = [line.strip() for line in lines if line.strip()]
                    return prompts[-1] if prompts else None

                command_prompt = await get_command_prompt()
                if command_prompt:
                    safe_output(f"获取到命令提示符: {command_prompt}\n")

                pre_commands = db.get_manufacturer_commands(manufacturer, "pre")
                for cmd in pre_commands:
                    safe_output(f"执行前置命令: {cmd}\n")
                    stdin.write(cmd + '\n')
                    await stdin.drain()
                    await read_until_prompt(command_prompt)

                for i, cmd in enumerate(cmd_list):
                    safe_output(f"执行命令 {i+1}/{len(cmd_list)}: {cmd}\n")
                    stdin.write(cmd + '\n')
                    await stdin.drain()

                    output = await read_until_prompt(command_prompt)
                    error = ""

                    if output:
                        cmd_index = output.find(cmd)
                        if cmd_index != -1:
                            end_index = cmd_index + len(cmd)
                            while end_index < len(output) and output[end_index] in '\r\n':
                                end_index += 1
                            output = output[end_index:]
                        lines = output.split('\n')
                        cleaned_lines = []
                        for line in lines:
                            stripped_line = line.strip()
                            if stripped_line:
                                cleaned_lines.append(stripped_line)
                        output = '\n'.join(cleaned_lines)
                        while '\n\n' in output:
                            output = output.replace('\n\n', '\n')

                    cmd_results.append((cmd, output, error))

                post_commands = db.get_manufacturer_commands(manufacturer, "post")
                for cmd in post_commands:
                    safe_output(f"执行后置命令: {cmd}\n")
                    stdin.write(cmd + '\n')
                    await stdin.drain()
                    await read_until_prompt(command_prompt)

                try:
                    process.close()
                except Exception:
                    pass

            finally:
                conn.close()
                try:
                    await conn.wait_closed()
                except Exception:
                    pass

            safe_output("巡检完成！\n")
            return True, cmd_results, ""

        except Exception as e:
            error_msg = str(e)
            safe_output(f"登录或执行命令错误: {error_msg}\n")
            return False, cmd_results, error_msg

    @staticmethod
    def save_patrol_results(ip, cmd_results, template_name="普通巡检模板", manufacturer="Hillstone"):
        """保存巡检结果到文件

        Args:
            ip: 设备IP
            cmd_results: 命令执行结果列表
            template_name: 模板名称
            manufacturer: 厂商名称
        """
        try:
            log_dir = settings.LOG_DIR
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            if "普通" in template_name:
                patrol_type = "normal_patrol"
            elif "深度" in template_name:
                patrol_type = "deep_patrol"
            else:
                patrol_type = "normal_patrol"

            patrol_dir = os.path.join(log_dir, patrol_type)
            if not os.path.exists(patrol_dir):
                os.makedirs(patrol_dir)

            manufacturer_dir = os.path.join(patrol_dir, manufacturer)
            if not os.path.exists(manufacturer_dir):
                os.makedirs(manufacturer_dir)

            device_dir = os.path.join(manufacturer_dir, ip)
            if not os.path.exists(device_dir):
                os.makedirs(device_dir)

            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            timestamp_dir = os.path.join(device_dir, timestamp)
            if not os.path.exists(timestamp_dir):
                os.makedirs(timestamp_dir)

            full_log_path = os.path.join(timestamp_dir, f"{ip}_full.log")

            with open(full_log_path, 'w', encoding='utf-8') as f:
                f.write(f"===== 巡检结果 - 设备: {ip} =====\n")
                f.write(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

                for i, (cmd, output, error) in enumerate(cmd_results):
                    f.write(f"\n===== 命令 {i+1}: {cmd} =====\n")
                    f.write(f"输出:\n{output}\n")
                    if error:
                        f.write(f"错误:\n{error}\n")

            for i, (cmd, output, error) in enumerate(cmd_results):
                cmd_filename = cmd.replace(' ', '_').replace('/', '_').replace('\\', '_')
                cmd_filename = f"{i+1:02d}_{cmd_filename}.log"
                cmd_file_path = os.path.join(timestamp_dir, cmd_filename)

                with open(cmd_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"命令: {cmd}\n")
                    f.write(f"输出:\n{output}\n")
                    if error:
                        f.write(f"错误:\n{error}\n")

            print(f"巡检结果已保存到: {timestamp_dir}")
            return timestamp_dir

        except Exception as e:
            print(f"保存巡检结果错误: {str(e)}")
            return None

    @classmethod
    def batch_collect(cls, devices, template_name, max_workers=10, append_output_func=None):
        """批量巡检（多线程版本）

        Args:
            devices: 设备列表，每个元素为字典包含manufacturer, ip, username, password, port
            template_name: 命令模板名称
            max_workers: 最大线程数
            append_output_func: 输出函数

        Returns:
            dict: 包含统计信息和结果的字典
        """
        results = []
        success_count = 0
        fail_count = 0
        failed_devices = []

        try:
            total_devices = len(devices)
            if append_output_func:
                append_output_func(f"开始批量巡检\n")
                append_output_func(f"设备数量: {total_devices}\n")
                append_output_func(f"命令模板: {template_name}\n")

            if total_devices == 0:
                return {
                    "total": 0,
                    "success": 0,
                    "fail": 0,
                    "results": [],
                    "failed_devices": []
                }

            import threading
            output_lock = threading.Lock()

            max_workers = max(1, min(total_devices, max_workers))
            if append_output_func:
                with output_lock:
                    append_output_func(f"使用线程池大小: {max_workers}\n")

            def patrol_device(device_info):
                nonlocal success_count, fail_count
                device, index = device_info

                try:
                    manufacturer = device.get("manufacturer", "Hillstone")
                    ip = device.get("ip", "")
                    username = device.get("username", "")
                    password = device.get("password", "")
                    port = int(device.get("port", 22))

                    if append_output_func:
                        with output_lock:
                            append_output_func(f"正在处理设备 {index+1}/{total_devices}: {ip} (厂商: {manufacturer})\n")

                    def output_func(text):
                        if append_output_func:
                            with output_lock:
                                append_output_func(text)

                    success, cmd_results, error_msg = cls.patrol_single_device(
                        ip=ip,
                        port=port,
                        username=username,
                        password=password,
                        manufacturer=manufacturer,
                        template_name=template_name,
                        append_output_func=output_func,
                        output_lock=output_lock
                    )

                    if cmd_results:
                        cls.save_patrol_results(ip, cmd_results, template_name, manufacturer)

                    if append_output_func:
                        with output_lock:
                            append_output_func(f"{ip}: 巡检完成！\n")

                    result = {
                        "ip": ip,
                        "success": success,
                        "results": cmd_results,
                        "error_msg": error_msg
                    }
                    results.append(result)

                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                        failed_devices.append(ip)

                except Exception as e:
                    if append_output_func:
                        with output_lock:
                            append_output_func(f"{device.get('ip', 'unknown')}: 巡检错误: {str(e)}\n")
                    fail_count += 1
                    failed_devices.append(device.get("ip", "unknown"))
                    results.append({
                        "ip": device.get("ip", "unknown"),
                        "success": False,
                        "results": [],
                        "error_msg": str(e)
                    })

            device_info_list = [(device, i) for i, device in enumerate(devices)]

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(patrol_device, device_info) for device_info in device_info_list]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        if append_output_func:
                            append_output_func(f"任务执行错误: {str(e)}\n")

            if append_output_func:
                append_output_func("批量巡检完成！\n")
                append_output_func(f"\n=== 巡检统计 ===\n")
                append_output_func(f"总设备数: {total_devices}\n")
                append_output_func(f"成功设备数: {success_count}\n")
                append_output_func(f"失败设备数: {fail_count}\n")
                if total_devices > 0:
                    append_output_func(f"成功率: {success_count/total_devices*100:.1f}%\n")
                append_output_func("================\n")

        except Exception as e:
            if append_output_func:
                append_output_func(f"批量巡检错误: {str(e)}\n")

        return {
            "total": len(devices),
            "success": success_count,
            "fail": fail_count,
            "results": results,
            "failed_devices": failed_devices
        }


patrol_service = PatrolService()

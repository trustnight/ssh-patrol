# -*- coding: utf-8 -*-
"""
设备巡检模块
使用 asyncssh 实现异步SSH连接
"""
import os
import time
import threading
import asyncio
import asyncssh
from concurrent.futures import ThreadPoolExecutor, as_completed
from models.database import db
from models.crypto_utils import crypto


class Patrol:
    """设备巡检类"""
    
    @staticmethod
    async def patrol_single_device(ip, port, username, password, manufacturer, template_name,
                                   append_output_func=None, update_progress_func=None, output_lock=None):
        """巡检单个设备的核心逻辑（异步版本，使用 asyncssh）

        Args:
            ip: 设备IP
            port: SSH端口
            username: 用户名
            password: 密码
            manufacturer: 设备厂商
            template_name: 命令模板名称
            append_output_func: 输出函数，接收text参数
            update_progress_func: 进度更新函数，接收current和total参数
            output_lock: 线程锁（批量模式下使用）

        Returns:
            tuple: (success: bool, results: list, error_msg: str)
        """
        async def safe_output(text):
            if append_output_func:
                if output_lock:
                    async with output_lock:
                        append_output_func(text)
                else:
                    append_output_func(text)

        cmd_results = []  # 初始化结果列表
        conn = None

        try:
            await safe_output(f"开始登录设备: {ip}:{port}\n")
            await safe_output(f"用户名: {username}\n")
            await safe_output(f"命令模板: {template_name}\n")
            await safe_output(f"设备厂商: {manufacturer}\n")

            # 解密密码（如果密码是加密的）
            decrypted_password = crypto.decrypt(password) if crypto.is_encrypted(password) else password

            # 使用 asyncssh 建立连接
            conn = await asyncssh.connect(
                ip,
                port=port,
                username=username,
                password=decrypted_password,
                known_hosts=None,
                connect_timeout=15
            )

            await safe_output("登录成功！\n")
            await safe_output("开始执行巡检命令...\n")

            # 获取命令列表
            cmd_list = db.get_cmd_template(template_name, manufacturer)

            # 创建交互式 shell 会话
            process = await conn.create_process(
                term_type='vt100',
                term_size=(80, 24)
            )

            stdin = process.stdin
            stdout = process.stdout

            # 等待 shell 准备好
            await asyncio.sleep(0.2)

            # 清除初始输出
            try:
                await asyncio.wait_for(stdout.read(4096), timeout=0.5)
            except asyncio.TimeoutError:
                pass

            # 获取命令提示符
            async def get_command_prompt(timeout=5):
                """获取设备的命令提示符"""
                stdin.write('\n')
                await stdin.drain()
                await asyncio.sleep(0.2)

                output = ""
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        data = await asyncio.wait_for(stdout.read(1024), timeout=0.1)
                        if data:
                            output += data
                        else:
                            break
                    except asyncio.TimeoutError:
                        continue

                # 提取可能的提示符（最后一行非空内容）
                lines = output.strip().split('\n')
                for line in reversed(lines):
                    line = line.strip()
                    if line and not line.endswith('\r'):
                        return line
                return None

            # 读取直到遇到命令提示符
            async def read_until_prompt(prompt, timeout=30):
                """读取输出直到遇到命令提示符"""
                output = ""
                start_time = time.time()
                last_activity_time = time.time()

                while time.time() - start_time < timeout:
                    try:
                        data = await asyncio.wait_for(stdout.read(4096), timeout=0.1)
                        if data:
                            output += data
                            last_activity_time = time.time()

                            # 检查是否包含提示符
                            if prompt and prompt in output:
                                # 继续读取一小段时间，确保所有输出都已接收
                                check_start = time.time()
                                while time.time() - check_start < 0.3:
                                    try:
                                        extra_data = await asyncio.wait_for(stdout.read(4096), timeout=0.1)
                                        if extra_data:
                                            output += extra_data
                                            last_activity_time = time.time()
                                    except asyncio.TimeoutError:
                                        pass
                                # 截取提示符前的内容
                                prompt_index = output.rfind(prompt)
                                return output[:prompt_index]
                        else:
                            break
                    except asyncio.TimeoutError:
                        pass

                    # 如果超过2秒没有活动，可能命令已经执行完成
                    if time.time() - last_activity_time > 2:
                        break

                    await asyncio.sleep(0.05)

                return output  # 超时返回已读取的内容

            # 获取命令提示符
            command_prompt = await get_command_prompt()
            if command_prompt:
                await safe_output(f"获取到命令提示符: {command_prompt}\n")

            # 执行厂商特定的前置命令
            pre_commands = db.get_manufacturer_commands(manufacturer, "pre")
            for cmd in pre_commands:
                await safe_output(f"执行前置命令: {cmd}\n")
                stdin.write(cmd + '\n')
                await stdin.drain()
                await read_until_prompt(command_prompt)
                # 清除缓冲区
                try:
                    await asyncio.wait_for(stdout.read(1024), timeout=0.2)
                except asyncio.TimeoutError:
                    pass

            # 执行命令列表
            for i, cmd in enumerate(cmd_list):
                await safe_output(f"执行命令 {i+1}/{len(cmd_list)}: {cmd}\n")

                # 发送命令
                stdin.write(cmd + '\n')
                await stdin.drain()

                # 读取输出直到遇到命令提示符
                output = await read_until_prompt(command_prompt)
                error = ""

                # 处理输出，去除命令回显和多余的空行
                if output:
                    # 去除命令回显
                    cmd_index = output.find(cmd)
                    if cmd_index != -1:
                        end_index = cmd_index + len(cmd)
                        while end_index < len(output) and output[end_index] in '\r\n':
                            end_index += 1
                        output = output[end_index:]
                    # 去除多余的空行
                    lines = output.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        stripped_line = line.strip()
                        if stripped_line:
                            cleaned_lines.append(stripped_line)
                    output = '\n'.join(cleaned_lines)
                    # 再次检查，确保没有连续的空行
                    while '\n\n' in output:
                        output = output.replace('\n\n', '\n')

                # 存储命令结果
                cmd_results.append((cmd, output, error))

                # 更新进度
                if update_progress_func:
                    update_progress_func(i+1, len(cmd_list))

                # 确保缓冲区为空
                try:
                    while True:
                        await asyncio.wait_for(stdout.read(4096), timeout=0.1)
                except asyncio.TimeoutError:
                    pass

            # 执行厂商特定的后置命令
            post_commands = db.get_manufacturer_commands(manufacturer, "post")
            for cmd in post_commands:
                await safe_output(f"执行后置命令: {cmd}\n")
                stdin.write(cmd + '\n')
                await stdin.drain()
                output = await read_until_prompt(command_prompt)
                # 处理输出
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
                        await safe_output(f"后置命令输出:\n{output}\n")
                # 清除缓冲区
                try:
                    await asyncio.wait_for(stdout.read(1024), timeout=0.2)
                except asyncio.TimeoutError:
                    pass

            # 关闭进程
            process.close()

            await safe_output("巡检完成！\n")

            return True, cmd_results, ""

        except asyncssh.Error as e:
            error_msg = f"SSH错误: {str(e)}"
            await safe_output(f"登录或执行命令错误: {error_msg}\n")
            return False, cmd_results, error_msg
        except Exception as e:
            error_msg = str(e)
            await safe_output(f"登录或执行命令错误: {error_msg}\n")
            return False, cmd_results, error_msg
        finally:
            if conn:
                conn.close()


    
    @classmethod
    async def login_async(cls, ui, ip, port, user, password, template_name, is_batch=False, manufacturer="Hillstone"):
        """SSH登录设备并执行巡检（异步版本，供UI调用）"""
        # 定义输出函数
        def append_output(text):
            if hasattr(ui, 'append_output'):
                ui.append_output(text)

        def update_progress(current, total):
            if hasattr(ui, 'update_progress'):
                ui.update_progress(current, total)

        # 调用核心巡检逻辑（异步版本）
        success, cmd_results, error_msg = await cls.patrol_single_device(
            ip=ip,
            port=port,
            username=user,
            password=password,
            manufacturer=manufacturer,
            template_name=template_name,
            append_output_func=append_output,
            update_progress_func=update_progress
        )

        # 保存结果
        if cmd_results:
            cls.save_patrol_results(ui, ip, cmd_results, template_name, manufacturer)

        # 启用按钮
        if hasattr(ui, 'enable_collect_button'):
            ui.enable_collect_button()

        return success, cmd_results, error_msg

    @classmethod
    def login(cls, ui, ip, port, user, password, template_name, is_batch=False, manufacturer="Hillstone"):
        """SSH登录设备并执行巡检（同步包装，供UI调用）"""
        return asyncio.run(cls.login_async(
            ui, ip, port, user, password, template_name, is_batch, manufacturer
        ))
    
    @classmethod
    def save_patrol_results(cls, ui, ip, cmd_results, template_name="普通巡检模板", manufacturer="Hillstone"):
        """保存巡检结果到文件"""
        try:
            # 创建log目录
            log_dir = os.path.join(os.getcwd(), 'log')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 根据模板类型确定巡检类型目录
            if "普通" in template_name:
                patrol_type = "normal_patrol"
            elif "深度" in template_name:
                patrol_type = "deep_patrol"
            else:
                patrol_type = "normal_patrol"  # 默认使用普通巡检
            
            # 创建巡检类型目录
            patrol_dir = os.path.join(log_dir, patrol_type)
            if not os.path.exists(patrol_dir):
                os.makedirs(patrol_dir)
            
            # 创建厂商目录
            manufacturer_dir = os.path.join(patrol_dir, manufacturer)
            if not os.path.exists(manufacturer_dir):
                os.makedirs(manufacturer_dir)
            
            # 创建设备IP目录
            device_dir = os.path.join(manufacturer_dir, ip)
            if not os.path.exists(device_dir):
                os.makedirs(device_dir)
            
            # 创建时间戳目录
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            timestamp_dir = os.path.join(device_dir, timestamp)
            if not os.path.exists(timestamp_dir):
                os.makedirs(timestamp_dir)
            
            # 创建完整日志文件
            full_log_path = os.path.join(timestamp_dir, f"{ip}_full.log")
            
            # 写入完整日志
            with open(full_log_path, 'w', encoding='utf-8') as f:
                f.write(f"===== 巡检结果 - 设备: {ip} =====\n")
                f.write(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                for i, (cmd, output, error) in enumerate(cmd_results):
                    f.write(f"\n===== 命令 {i+1}: {cmd} =====\n")
                    f.write(f"输出:\n{output}\n")
                    if error:
                        f.write(f"错误:\n{error}\n")
            
            # 为每个命令创建单独的文件
            for i, (cmd, output, error) in enumerate(cmd_results):
                # 生成命令文件名（移除特殊字符）
                cmd_filename = cmd.replace(' ', '_').replace('/', '_').replace('\\', '_')
                cmd_filename = f"{i+1:02d}_{cmd_filename}.log"
                cmd_file_path = os.path.join(timestamp_dir, cmd_filename)
                
                # 写入命令输出
                with open(cmd_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"命令: {cmd}\n")
                    f.write(f"输出:\n{output}\n")
                    if error:
                        f.write(f"错误:\n{error}\n")
            
            # 显示保存成功信息
            if hasattr(ui, 'append_output'):
                ui.append_output(f"巡检结果已保存到: {timestamp_dir}\n")
                ui.append_output(f"完整日志文件: {full_log_path}\n")
                ui.append_output(f"每个命令的输出已单独保存\n")
                
        except Exception as e:
            if hasattr(ui, 'append_output'):
                ui.append_output(f"保存巡检结果错误: {str(e)}\n")
    
    @classmethod
    async def batch_collect_async(cls, ui, devices, template_name, max_concurrent=20):
        """批量巡检（纯异步并发版本，支持几十台设备同时巡检）

        Args:
            ui: UI对象
            devices: 设备列表
            template_name: 命令模板名称
            max_concurrent: 最大并发数（默认20，可根据需要调整）
        """
        import datetime

        # 统计变量
        stats = {
            'completed_count': 0,
            'success_count': 0,
            'fail_count': 0,
            'failed_devices': [],
            'total_devices': 0
        }

        # 线程锁用于保护UI输出
        output_lock = asyncio.Lock()

        def safe_output(text):
            """线程安全的输出函数"""
            if hasattr(ui, 'append_output'):
                ui.append_output(text)

        async def update_ui_stats():
            """更新UI统计信息"""
            if hasattr(ui, 'dev_success_var'):
                ui.dev_success_var.set(str(stats['success_count']))
            if hasattr(ui, 'dev_fail_var'):
                ui.dev_fail_var.set(str(stats['fail_count']))
            if hasattr(ui, 'dev_progress_var'):
                ui.dev_progress_var.set(f"{stats['completed_count']}/{stats['total_devices']}")

        async def patrol_single_device_async_wrapper(device, index):
            """包装单个设备巡检，处理设备信息解析和结果统计"""
            nonlocal stats

            # 解析设备信息
            if len(device) >= 5:
                manufacturer, ip, username, password, port = device[0], device[1], device[2], device[3], int(device[4])
                async with output_lock:
                    safe_output(f"开始巡检设备 {index+1}/{stats['total_devices']}: {ip} (厂商: {manufacturer})\n")
            elif len(device) >= 4:
                manufacturer = "unknown"
                ip, username, password, port = device[0], device[1], device[2], int(device[3])
                async with output_lock:
                    safe_output(f"开始巡检设备 {index+1}/{stats['total_devices']}: {ip}\n")
            else:
                async with output_lock:
                    safe_output(f"设备信息不完整，跳过\n")
                return

            try:
                # 定义输出回调（需要加锁保护）
                async def append_output_async(text):
                    async with output_lock:
                        safe_output(text)

                def append_output(text):
                    # 由于 patrol_single_device 是同步调用回调，我们需要在这里处理
                    if hasattr(ui, 'append_output'):
                        ui.append_output(text)

                # 调用核心巡检逻辑（异步版本）
                success, cmd_results, error_msg = await cls.patrol_single_device(
                    ip=ip,
                    port=port,
                    username=username,
                    password=password,
                    manufacturer=manufacturer,
                    template_name=template_name,
                    append_output_func=append_output,
                    output_lock=output_lock
                )

                # 保存巡检结果
                if cmd_results:
                    cls.save_patrol_results(ui, ip, cmd_results, template_name, manufacturer)

                async with output_lock:
                    if success:
                        safe_output(f"{ip}: 巡检完成！\n")
                        stats['success_count'] += 1
                    else:
                        safe_output(f"{ip}: 巡检失败 - {error_msg}\n")
                        stats['fail_count'] += 1
                        stats['failed_devices'].append(ip)

            except Exception as e:
                import traceback
                async with output_lock:
                    safe_output(f"{ip}: 巡检错误: {str(e)}\n")
                    safe_output(f"{ip}: 错误详情: {traceback.format_exc()}\n")
                stats['fail_count'] += 1
                stats['failed_devices'].append(ip)

            finally:
                # 更新进度
                stats['completed_count'] += 1
                await update_ui_stats()

        try:
            async with output_lock:
                safe_output(f"开始批量巡检（异步并发模式，最大并发: {max_concurrent}）\n")
                device_count = len(devices) - 1 if (devices and len(devices) > 1) else 0
                safe_output(f"设备数量: {device_count}\n")
                safe_output(f"命令模板: {template_name}\n")

            # 实际批量巡检过程
            if devices and len(devices) > 1:
                stats['total_devices'] = len(devices) - 1  # 减去表头
                device_list = devices[1:]  # 跳过表头

                # 使用信号量控制并发数
                semaphore = asyncio.Semaphore(max_concurrent)

                async def patrol_with_semaphore(device, index):
                    """使用信号量限制并发"""
                    async with semaphore:
                        await patrol_single_device_async_wrapper(device, index)

                # 创建所有巡检任务
                tasks = [
                    patrol_with_semaphore(device, i)
                    for i, device in enumerate(device_list)
                ]

                # 并发执行所有任务
                await asyncio.gather(*tasks, return_exceptions=True)

                # 输出统计信息
                async with output_lock:
                    safe_output("\n批量巡检完成！\n")
                    safe_output(f"\n=== 巡检统计 ===\n")
                    safe_output(f"总设备数: {stats['total_devices']}\n")
                    safe_output(f"成功设备数: {stats['success_count']}\n")
                    safe_output(f"失败设备数: {stats['fail_count']}\n")
                    if stats['total_devices'] > 0:
                        safe_output(f"成功率: {stats['success_count']/stats['total_devices']*100:.1f}%\n")
                    safe_output("================\n")

                # 保存失败设备列表
                if stats['failed_devices']:
                    try:
                        log_dir = os.path.join(os.getcwd(), 'log')
                        if not os.path.exists(log_dir):
                            os.makedirs(log_dir)

                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        fail_file_path = os.path.join(log_dir, f'failed_devices_{timestamp}.txt')

                        with open(fail_file_path, 'w', encoding='utf-8') as f:
                            f.write(f"===== 批量巡检失败设备列表 =====\n")
                            f.write(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write(f"失败设备数量: {len(stats['failed_devices'])}\n")
                            f.write("\n失败设备IP列表:\n")
                            for i, ip in enumerate(stats['failed_devices'], 1):
                                f.write(f"{i}. {ip}\n")

                        async with output_lock:
                            safe_output(f"\n失败设备IP列表已保存到: {fail_file_path}\n")
                    except Exception as e:
                        async with output_lock:
                            safe_output(f"保存失败设备列表错误: {str(e)}\n")

        except Exception as e:
            import traceback
            async with output_lock:
                safe_output(f"批量巡检错误: {str(e)}\n")
                safe_output(f"错误详情: {traceback.format_exc()}\n")

    @classmethod
    def batch_collect(cls, ui, devices, template_name, max_concurrent=20):
        """批量巡检（同步入口，内部使用异步并发）

        Args:
            ui: UI对象
            devices: 设备列表
            template_name: 命令模板名称
            max_concurrent: 最大并发数（默认20）
        """
        asyncio.run(cls.batch_collect_async(ui, devices, template_name, max_concurrent))

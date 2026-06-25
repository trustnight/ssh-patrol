# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

巡检助手WEBUI是一个用于网络设备批量巡检的Web应用，支持SSH连接设备执行巡检命令并生成报告。同时集成了截图自动命名功能，可通过全局快捷键对设备Web界面进行截图并按IP自动命名。

## 技术栈

- **后端**: FastAPI + SQLite + Paramiko/AsyncSSH
- **前端**: Vue3 + Element Plus + Vite
- **打包**: PyInstaller (单文件exe)
- **截图**: PIL全屏截图 + pynput全局快捷键监听

## 开发环境要求

- Python 3.7.10，conda环境名: `py3710`
- Node.js/npm
- **必须先激活conda环境**: `conda activate py3710`

## 常用命令

### 开发模式启动（同时启动前后端）
```bash
python run_dev.py
```
后端运行在 `http://127.0.0.1:8000`，前端运行在 `http://localhost:5173`，API文档在 `http://127.0.0.1:8000/docs`。

### 仅启动后端
```bash
cd backend && python run.py
```

### 前端开发
```bash
cd frontend
npm install    # 安装依赖（幂等）
npm run dev    # 启动Vite开发服务器
npm run build  # 构建生产版本到 dist/
```

### 打包为exe
```bash
python build.py
```
输出到 `dist/巡检助手WEBUI_v{版本号}.exe`。打包脚本会自动检查conda环境、构建前端、清理旧构建、执行PyInstaller。

## 架构要点

### 后端结构

后端入口是 `backend/run.py`，它导入 `app.main` 中的 FastAPI app 实例并用 uvicorn 启动。`app/main.py` 中的 `create_app()` 负责：
- 注册 CORS 中间件
- 注册 API 路由（devices, patrol, templates, screenshot）
- 注册 WebSocket 路由（ssh_terminal, patrol_log）
- 挂载前端静态文件（打包模式下从 `web/dist` 目录加载，SPA路由fallback）
- startup事件中初始化数据库和任务管理器

### 关键设计模式

- **Database单例**: `app/database.py` 导出全局 `db` 实例，所有数据库操作通过它完成。每次操作独立 `connect`/`close`（非持久连接）。
- **Service单例**: `app/services/` 下的服务类（`patrol_service`, `task_manager`, `screenshot_service`）均为模块级单例实例。
- **路径兼容**: `config.py` 中的 `get_exe_dir()` 和 `get_resource_dir()` 同时兼容开发模式和PyInstaller打包后的 `sys._MEIPASS` 路径。
- **密码加密**: 设备密码通过 `crypto_utils.py` 的 AES 加密存储，入库前自动判断是否已加密。

### 巡检流程

`task_manager` 维护任务状态，`patrol_service` 通过 Paramiko SSH 连接设备执行命令。批量巡检使用线程池并发，通过 WebSocket (`/ws/patrol/{task_id}`) 实时推送日志到前端。

### 截图功能

`screenshot_service` 使用 `PIL.ImageGrab.grab()` 全屏截图，通过 pynput 监听全局快捷键（默认 Alt+Q）。支持创建截图任务、从URL列表选择设备、按IP自动命名截图保存到 `screen/` 目录。

### 前端结构

Vue3 SPA，路由使用 `createWebHistory`。主要视图：设备管理、巡检任务列表/详情、单设备巡检、批量巡检、SSH终端、模板管理、截图管理。API调用封装在 `frontend/src/api/`，SSH终端使用 xterm.js。

## 数据库

SQLite文件: `patrol.db`（开发时在项目根目录，打包后在exe同目录）

主要表：`devices`（设备信息）、`commands`（巡检命令模板）、`manufacturer_commands`（厂商默认命令）、`patrol_history`（巡检历史）、`screenshot_urls`（截图URL列表）、`screenshot_history`（截图记录）

## 配置

配置文件: `backend/app/config.py`，关键项：`HOST/PORT`（默认127.0.0.1:8000）、`DB_PATH`、`STATIC_DIR`、`AUTO_OPEN_BROWSER`。版本号 `APP_VERSION` 在打包时用于exe文件名。

## 注意事项

- 开发模式下前端(5173)和后端(8000)分开运行，打包后前端静态文件嵌入exe由后端直接serve
- PyInstaller打包配置在 `patrol_web.spec`，hiddenimports列表包含了FastAPI/Paramiko等PyInstaller检测不到的模块
- `run_dev.py` 启动时会自动清理 `__pycache__` 和 Vite 缓存，防止旧缓存导致问题
- 设备导入支持CSV文件（模板：`设备导入模板.csv`）

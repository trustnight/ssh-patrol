# 巡检助手 WEBUI

> 网络设备批量巡检 Web 管理工具 | 支持 SSH 命令执行、Web 界面截图、CSV 导入设备

![Version](https://img.shields.io/badge/version-1.0.2-blue)
![Python](https://img.shields.io/badge/Python-3.7.10-green)
![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## 功能概览

- **设备管理** — 添加/编辑/导入网络设备，支持 CSV 批量导入
- **批量巡检** — 通过 SSH 批量执行巡检命令，实时 WebSocket 日志推送
- **单设备巡检** — 单台设备巡检 + 内嵌 SSH 终端（xterm.js）
- **模板管理** — 内置/自定义巡检命令模板，按厂商、设备类型、深度/普通分类
- **截图任务** — Web 界面截图任务编排，全局快捷键（Alt+Q）按 IP 自动命名保存
- **系统托盘** — 打包为 Windows 托盘程序，支持开机自启、后台静默运行

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLite + Paramiko/AsyncSSH + uvicorn |
| 前端 | Vue 3 + Element Plus + Vite + xterm.js |
| 打包 | PyInstaller（单文件 exe） |
| 截图 | PIL.ImageGrab + pynput 全局快捷键监听 |

---

## 快速开始

### 环境要求

- Python 3.7.10（推荐 conda 环境 `py3710`）
- Node.js ≥ 16

### 开发模式

```bash
# 1. 激活 conda 环境
conda activate py3710

# 2. 安装后端依赖
pip install -r requirements.txt

# 3. 安装前端依赖
cd frontend && npm install && cd ..

# 4. 启动开发模式（前后端同时启动）
python run_dev.py
```

- 后端 API：http://127.0.0.1:8000
- 前端页面：http://localhost:5173
- API 文档：http://127.0.0.1:8000/docs

### 打包为 EXE

```bash
python build.py
```

输出文件：`dist/巡检助手WEBUI_v1.0.2.exe`

打包脚本会自动检查 conda 环境、构建前端、执行 PyInstaller 打包。

---

## 项目结构

```
巡检助手/
├── backend/                  # 后端
│   ├── run.py                # 启动入口
│   └── app/
│       ├── main.py           # FastAPI 应用工厂
│       ├── config.py         # 配置（路径兼容开发/打包模式）
│       ├── database.py       # 数据库单例（SQLite）
│       ├── crypto_utils.py   # AES 密码加密
│       ├── api/              # API 路由
│       │   ├── devices.py    #   设备管理
│       │   ├── patrol.py     #   巡检任务
│       │   ├── templates.py  #   命令模板
│       │   └── screenshot.py #   截图管理
│       ├── models/           # 数据模型
│       └── services/         # 业务服务单例
│           ├── patrol_service.py
│           ├── task_manager.py
│           └── screenshot_service.py
├── frontend/                 # 前端 Vue 3 SPA
│   └── src/
│       ├── views/            # 页面视图
│       │   ├── DeviceManage.vue
│       │   ├── TemplateManage.vue
│       │   ├── BatchPatrol.vue
│       │   ├── SinglePatrol.vue
│       │   ├── PatrolTaskList.vue
│       │   ├── PatrolTaskDetail.vue
│       │   ├── Screenshot.vue
│       │   ├── Settings.vue
│       │   └── SSHTerminal.vue
│       └── api/              # API 调用封装
├── run_dev.py                # 开发模式启动脚本
├── build.py                  # 打包脚本
├── patrol_web.spec           # PyInstaller 配置
└── requirements.txt          # Python 依赖
```

---

## 架构要点

- **数据库单例** — `database.py` 全局 `db` 实例，每次操作独立 connect/close
- **服务单例** — patrol_service / task_manager / screenshot_service 模块级实例
- **密码加密** — 设备密码 AES 加密存储，入库自动检测
- **实时日志** — WebSocket `/ws/patrol/{task_id}` 推送巡检进度
- **路径兼容** — 开发模式和 PyInstaller `_MEIPASS` 路径自动适配
- **SSH 终端** — 基于 xterm.js + AsyncSSH 的 Web 终端

### 截图快捷键

| 快捷键 | 功能 |
|---|---|
| Alt+Q | 全屏截图，按当前设备 IP 自动命名 |
| 可自定义 | 在截图管理页面设置 |

---

## 设备类型

支持以下设备类型：

| 缩写 | 含义 | 缩写 | 含义 |
|---|---|---|---|
| FW | 防火墙 | WAF | Web 应用防火墙 |
| SW | 交换机 | DDOS | 抗 DDoS |
| RT | 路由器 | WOC | 广域网优化 |
| IPS | 入侵防御 | other | 其他 |

### 预设厂商

内置以下厂商的默认巡检命令，可在模板管理中自定义扩展：

- Hillstone
- Huawei
- Topsec

> 支持手动添加任意厂商，不限于上述预设。

---

## 数据库

SQLite 数据库 `patrol.db`，主要表：

| 表名 | 说明 |
|---|---|
| `devices` | 设备信息（IP、厂商、类型、URL、SSH 凭证） |
| `commands` | 巡检命令模板（内置 + 自定义） |
| `manufacturer_commands` | 厂商默认命令 |
| `patrol_history` | 巡检历史记录 |
| `screenshot_tasks` | 截图任务 |
| `screenshot_task_devices` | 任务-设备关联 |
| `screenshot_history` | 截图历史记录 |

---

## 配置

配置文件：`backend/app/config.py`

| 配置项 | 默认值 | 说明 |
|---|---|---|
| HOST | 127.0.0.1 | 监听地址 |
| PORT | 8000 | 监听端口 |
| DB_PATH | patrol.db | 数据库路径 |
| AUTO_OPEN_BROWSER | True | 启动后自动打开浏览器 |

---

## License

MIT

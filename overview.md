# 巡检助手 WEBUI — 新增"设备类型"支持

## 改动概要

为巡检模板和CSV设备新增"设备类型"列，实现同一厂商不同设备类型（路由器/交换机/防火墙）使用不同巡检命令。

---

## 核心设计：三级匹配 + 回退

```
巡检时匹配命令模板：
  1. 模板名 + 厂商 + 设备类型  →  精确匹配
  2. 模板名 + 厂商（device_type=""） →  回退（向后兼容）
```

已有模板如果没有设置 device_type，巡检仍然正常工作。

---

## 修改文件清单（4层 / 12个文件）

### 数据库层 — `backend/app/database.py`
- `commands` 表新增 `device_type TEXT DEFAULT ''`
- `devices` 表新增 `device_type TEXT DEFAULT ''`
- 兼容迁移：ALTER TABLE 自动加列
- `get_cmd_template()`：三级匹配 + 回退
- 所有设备/模板 CRUD 方法加 `device_type` 参数

### Schema 层 — `backend/app/models/schemas.py`
- `DeviceCreate`, `DeviceUpdate`, `Device`, `DeviceInfo`, `SaveCustomTemplateRequest` 均加 `device_type`

### API 层 — 3个文件
- `templates.py`：查询/保存模板时传 `device_type`
- `devices.py`：增/改设备时传 `device_type`；CSV header 增加 device_type 列
- `patrol.py`：从设备信息取 `device_type` 传给巡检服务

### 前端 — 5个文件
- **DeviceManage.vue**：表格新增设备类型列 + 表单下拉选择器 + CSV 导入/导出适配
- **TemplateManage.vue**：顶部选择区 + 保存表单均新增设备类型下拉
- **BatchPatrol.vue**：设备列表显示 device_type tag
- **templates.js** / **devices.js**：API 调用加 `device_type` 参数

---

## 向后兼容

- 所有旧数据 `device_type=''`（空），匹配时自动走回退逻辑
- 现有巡检命令模板不受影响
- CSV 导出/导入自动适配新列格式

## 注意事项

- 重启后端后数据库会自动迁移（ALTER TABLE 添加新列）
- 如需为某个厂商+设备类型创建专属命令，在模板管理页选择"设备类型"后保存即可
- CSV 模板格式已更新为：`order,manufacturer,device_type,ip,username,password,port,url`

import request from '@/utils/request'

// ==================== 设备URL获取 ====================

// 获取有URL的设备列表（从设备管理）
export function getDevicesWithUrl() {
  return request({ url: '/screenshot/devices-with-url', method: 'get' })
}

// ==================== 截图任务 ====================

// 创建截图任务
export function createScreenshotTask(data) {
  return request({ url: '/screenshot/tasks', method: 'post', data })
}

// 获取任务列表
export function getScreenshotTasks() {
  return request({ url: '/screenshot/tasks', method: 'get' })
}

// 获取任务设备列表
export function getTaskDevices(taskId) {
  return request({ url: `/screenshot/tasks/${taskId}/devices`, method: 'get' })
}

// 设置活跃设备
export function setTaskActiveDevice(taskId, deviceId) {
  return request({ url: `/screenshot/tasks/${taskId}/set-active`, method: 'post', data: { device_id: deviceId } })
}

// 完成当前设备
export function completeTaskDevice(taskId) {
  return request({ url: `/screenshot/tasks/${taskId}/complete`, method: 'post' })
}

// 删除截图任务
export function deleteScreenshotTask(taskId) {
  return request({ url: `/screenshot/tasks/${taskId}`, method: 'delete' })
}

// ==================== 截图操作 ====================

// 设置活跃URL（兼容旧接口）
export function setActiveUrl(url) {
  return request({ url: '/screenshot/set-active', method: 'post', data: { url } })
}

// 执行全屏截图
export function captureScreen() {
  return request({ url: '/screenshot/capture', method: 'post' })
}

// 获取截图状态
export function getScreenshotStatus() {
  return request({ url: '/screenshot/status', method: 'get' })
}

// 设置快捷键
export function setHotkey(hotkey) {
  return request({ url: '/screenshot/set-hotkey', method: 'post', data: { hotkey } })
}

// 获取截图历史
export function getScreenshotHistory(ip) {
  return request({ url: '/screenshot/history', method: 'get', params: ip ? { ip } : {} })
}

// 清空截图历史（同时删除本地文件）
export function clearScreenshotHistory() {
  return request({ url: '/screenshot/clear-history', method: 'post' })
}

// 删除单条截图历史（同时删除本地文件）
export function deleteScreenshotRecord(recordId) {
  return request({ url: `/screenshot/history/${recordId}`, method: 'delete' })
}

// 启动监听
export function startListening() {
  return request({ url: '/screenshot/start-listening', method: 'post' })
}

// 停止监听
export function stopListening() {
  return request({ url: '/screenshot/stop-listening', method: 'post' })
}

// 打开截图文件夹
export function openScreenshotFolder() {
  return request({ url: '/screenshot/open-folder', method: 'post' })
}

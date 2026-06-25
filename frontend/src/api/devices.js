import request from '@/utils/request'

// 获取设备列表（支持keyword, manufacturer筛选）
export function getDeviceList(params) {
  return request({
    url: '/devices',
    method: 'get',
    params: params
  })
}

// 获取设备详情
export function getDevice(id) {
  return request({
    url: `/devices/${id}`,
    method: 'get'
  })
}

// 新增设备
export function addDevice(data) {
  return request({
    url: '/devices',
    method: 'post',
    data: data
  })
}

// 更新设备
export function updateDevice(id, data) {
  return request({
    url: `/devices/${id}`,
    method: 'put',
    data: data
  })
}

// 删除设备
export function deleteDevice(id) {
  return request({
    url: `/devices/${id}`,
    method: 'delete'
  })
}

// 测试连接
export function testConnection(data) {
  return request({
    url: '/devices/test-connection',
    method: 'post',
    data: data
  })
}

// 导出设备（含加密密码）
export function exportDevices() {
  return request({
    url: '/devices/export',
    method: 'get'
  })
}

// 刷新设备导入模板（直接写磁盘，不弹下载）
export function refreshTemplate() {
  return request({
    url: '/devices/template/refresh',
    method: 'post'
  })
}

// 批量删除设备
export function batchDeleteDevices(deviceIds) {
  return request({
    url: '/devices/batch-delete',
    method: 'post',
    data: { device_ids: deviceIds }
  })
}

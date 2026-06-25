import request from '@/utils/request'

// 获取运行中的任务列表
export function getRunningTasks() {
  return request({
    url: '/patrol/tasks',
    method: 'get'
  })
}

// 单设备巡检
export function singlePatrol(data) {
  return request({
    url: '/patrol/single',
    method: 'post',
    data: data
  })
}

// 开始批量巡检
export function startBatchPatrol(data) {
  return request({
    url: '/patrol/batch/start',
    method: 'post',
    data: data
  })
}

// 获取批量巡检状态（silent：任务不存在时不弹错误提示）
export function getBatchStatus(taskId, silent = false) {
  return request({
    url: `/patrol/batch/status/${taskId}`,
    method: 'get',
    silent
  })
}

// 巡检历史列表
export function getPatrolHistory(params) {
  return request({
    url: '/patrol/history',
    method: 'get',
    params: params
  })
}

// 巡检历史详情
export function getPatrolDetail(id) {
  return request({
    url: `/patrol/history/${id}`,
    method: 'get'
  })
}

// 查看巡检结果（命令输出内容）
export function getPatrolResult(recordId) {
  return request({
    url: `/patrol/result/${recordId}`,
    method: 'get'
  })
}

// 打开巡检结果文件夹
export function openPatrolFolder(recordId) {
  return request({
    url: `/patrol/open-folder/${recordId}`,
    method: 'post'
  })
}

// 批量删除巡检任务
export function batchDeleteTasks(taskIds) {
  return request({
    url: '/patrol/history/batch-delete',
    method: 'post',
    data: { task_ids: taskIds }
  })
}

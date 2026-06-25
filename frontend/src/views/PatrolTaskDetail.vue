<template>
  <div class="page-container">
    <!-- 任务概览 -->
    <el-card class="overview-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-button link @click="goBack">
              <el-icon><ArrowLeft /></el-icon>
              返回
            </el-button>
            <span class="task-title">任务详情</span>
            <el-tag size="small" :type="statusType(taskStatus)">{{ statusText(taskStatus) }}</el-tag>
          </div>
          <div class="header-right">
            <el-tag size="small" type="info">{{ templateName }}</el-tag>
            <span class="task-id">ID: {{ taskId }}</span>
          </div>
        </div>
      </template>

      <el-row :gutter="24">
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-label">总设备数</div>
            <div class="stat-value">{{ totalDevices }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-label success">成功</div>
            <div class="stat-value success-value">{{ successCount }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-label fail">失败</div>
            <div class="stat-value fail-value">{{ failCount }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-label">进度</div>
            <div class="stat-value">{{ progressPercent }}%</div>
          </div>
        </el-col>
      </el-row>
      <el-progress
        :percentage="progressPercent"
        :stroke-width="10"
        :status="progressStatus"
        style="margin-top: 16px"
      />
    </el-card>

    <!-- 设备列表 + 日志/结果（可拖拽调整宽度） -->
    <div class="detail-row">
      <!-- 左侧设备列表 -->
      <div class="device-panel" :style="{ width: leftWidth + 'px' }">
        <el-card class="device-card">
          <template #header>
            <span>设备</span>
          </template>
          <div class="device-list">
            <div
              v-for="device in deviceResults"
              :key="device.ip"
              class="device-item"
              :class="{ active: activeDevice === device.ip }"
              @click="activeDevice = device.ip"
            >
              <el-tag size="small" :type="device.success ? 'success' : (device.success === false ? 'danger' : 'info')">
                {{ device.success ? '✓' : (device.success === false ? '✗' : '…') }}
              </el-tag>
              <span class="device-ip">{{ device.ip }}</span>
            </div>
            <el-empty v-if="deviceResults.length === 0" description="暂无设备" :image-size="60" />
          </div>
        </el-card>
      </div>

      <!-- 拖拽条 -->
      <div class="splitter" @mousedown="startDrag">
        <div class="splitter-line"></div>
      </div>

      <!-- 右侧内容 -->
      <div class="right-panel">
        <el-card class="log-card">
          <template #header>
            <div class="card-header">
              <el-radio-group v-model="rightTab" size="small">
                <el-radio-button value="log">巡检日志</el-radio-button>
                <el-radio-button value="result">巡检结果</el-radio-button>
              </el-radio-group>
              <el-button v-if="rightTab === 'log'" size="small" link @click="clearLog">清空</el-button>
            </div>
          </template>
          <!-- 日志视图 -->
          <div v-if="rightTab === 'log'" ref="logContainer" class="log-container">
            <pre class="log-content">{{ logText || '等待巡检开始...' }}</pre>
          </div>
          <!-- 结果视图：按命令展示 -->
          <div v-else class="result-container">
            <div v-if="!activeDevice" class="result-placeholder">点击左侧设备查看命令结果</div>
            <div v-else-if="loadingResult" class="result-placeholder">加载中...</div>
            <div v-else-if="resultCommands.length > 0" class="result-cmds">
              <div class="result-device-header">
                <el-tag :type="resultSuccess ? 'success' : 'danger'" size="small" style="flex-shrink: 0">
                  {{ resultSuccess ? '成功' : '失败' }}
                </el-tag>
                <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ activeDevice }}</span>
                <el-button size="small" link type="primary" @click="handleOpenFolder" style="flex-shrink: 0">
                  <el-icon><FolderOpened /></el-icon>
                  打开文件夹
                </el-button>
              </div>
              <el-collapse v-model="activeCmdNames" accordion>
                <el-collapse-item
                  v-for="cmd in resultCommands"
                  :key="cmd.name"
                  :title="cmd.name"
                  :name="cmd.name"
                >
                  <pre class="log-content cmd-output">{{ cmd.output }}</pre>
                </el-collapse-item>
              </el-collapse>
            </div>
            <div v-else class="result-placeholder">暂无命令输出</div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getBatchStatus, getPatrolResult, getPatrolHistory, openPatrolFolder } from '@/api/patrol'

const route = useRoute()
const router = useRouter()

// ===== 拖拽调整宽度 =====
const leftWidth = ref(200)
const MIN_LEFT = 140
const MAX_LEFT = 500
let dragging = false

function startDrag(e) {
  dragging = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

function onDrag(e) {
  if (!dragging) return
  const container = document.querySelector('.detail-row')
  if (!container) return
  const rect = container.getBoundingClientRect()
  const x = e.clientX - rect.left
  leftWidth.value = Math.min(MAX_LEFT, Math.max(MIN_LEFT, x))
}

function stopDrag() {
  dragging = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
}

onBeforeUnmount(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
})

const taskId = computed(() => route.params.taskId)

// 任务状态
const taskStatus = ref('pending')
const templateName = ref('')
const totalDevices = ref(0)
const successCount = ref(0)
const failCount = ref(0)
const logText = ref('')
const logContainer = ref(null)
const activeDevice = ref('')
const rightTab = ref('log')
const loadingResult = ref(false)
const resultCommands = ref([])
const activeCmdNames = ref('')
const resultSuccess = ref(false)
const currentRecordId = ref(null)

// 点击设备时加载巡检结果
watch(activeDevice, async (ip) => {
  if (!ip || rightTab.value !== 'result') return
  await loadDeviceResult(ip)
})

watch(rightTab, async (tab) => {
  if (tab === 'result' && activeDevice.value) {
    await loadDeviceResult(activeDevice.value)
  }
})

async function handleOpenFolder() {
  if (!currentRecordId.value) return
  try {
    await openPatrolFolder(currentRecordId.value)
  } catch (e) {
    console.error('打开文件夹失败:', e)
  }
}

async function loadDeviceResult(ip) {
  loadingResult.value = true
  resultCommands.value = []
  try {
    const res = await getPatrolHistory({ task_id: taskId.value, ip: ip, page_size: 100 })
    if (res.code === 0 && res.data.records.length > 0) {
      const record = res.data.records[0]
      currentRecordId.value = record.id
      const resultRes = await getPatrolResult(record.id)
      if (resultRes.code === 0 && resultRes.data) {
        resultCommands.value = resultRes.data.commands || []
        resultSuccess.value = resultRes.data.success
      }
    }
  } catch (e) {
    console.error('加载巡检结果失败:', e)
  } finally {
    loadingResult.value = false
  }
}

// WebSocket
let ws = null

// 设备结果列表
const deviceResults = ref([])

const progressPercent = computed(() => {
  if (totalDevices.value === 0) return 0
  return Math.round(((successCount.value + failCount.value) / totalDevices.value) * 100)
})

const progressStatus = computed(() => {
  if (successCount.value + failCount.value < totalDevices.value) {
    return ''
  }
  return failCount.value > 0 ? 'warning' : 'success'
})

const statusText = (status) => {
  const map = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

const statusType = (status) => {
  const map = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return map[status] || ''
}

// 解析日志，提取设备状态
const parseLogForDevices = (log) => {
  const lines = log.split('\n')
  const deviceMap = {}

  for (const line of lines) {
    const match = line.match(/^\[([^\]]+)\]\s+执行命令\s+(\d+)\/(\d+):\s+(.+)/)
    if (match) {
      const ip = match[1]
      const cmdIndex = parseInt(match[2])
      const cmdTotal = parseInt(match[3])
      const cmdName = match[4].trim()

      if (!deviceMap[ip]) {
        deviceMap[ip] = {
          ip: ip,
          success: null,
          cmd_index: cmdIndex,
          cmd_total: cmdTotal,
          current_cmd: cmdName
        }
      } else {
        deviceMap[ip].cmd_index = cmdIndex
        deviceMap[ip].cmd_total = cmdTotal
        deviceMap[ip].current_cmd = cmdName
      }
    }

    const successMatch = line.match(/^\[([^\]]+)\]\s+巡检完成！/)
    if (successMatch) {
      const ip = successMatch[1]
      if (deviceMap[ip]) {
        deviceMap[ip].success = true
      }
    }

    const failMatch = line.match(/^\[([^\]]+)\]\s+登录或执行命令错误:/)
    if (failMatch) {
      const ip = failMatch[1]
      if (deviceMap[ip]) {
        deviceMap[ip].success = false
      }
    }
  }

  return Object.values(deviceMap)
}

// 追加日志
const appendLog = (text) => {
  logText.value += text
  deviceResults.value = parseLogForDevices(logText.value)
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

const clearLog = () => {
  logText.value = ''
  deviceResults.value = []
}

// 更新任务状态
const updateTaskStatus = (status) => {
  totalDevices.value = status.total_devices || 0
  successCount.value = status.success_count || 0
  failCount.value = status.fail_count || 0
  taskStatus.value = status.status || 'pending'
  templateName.value = status.template_name || ''

  if (status.results) {
    for (const result of status.results) {
      const existing = deviceResults.value.find(d => d.ip === result.ip)
      if (existing) {
        existing.success = result.success
      } else {
        deviceResults.value.push({
          ip: result.ip,
          success: result.success,
          cmd_index: result.results ? result.results.length : 0,
          cmd_total: 0,
          current_cmd: ''
        })
      }
    }
  }

}

// WebSocket 实时更新任务状态
const updateTaskStatusFromWS = (data) => {
  updateTaskStatus(data)
}

// 连接WebSocket
const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/patrol/${taskId.value}`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('WebSocket连接成功')
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'log') {
        appendLog(data.data)
      } else if (data.type === 'history') {
        appendLog(data.data)
      } else if (data.type === 'status') {
        updateTaskStatus(data.data)
      }
    } catch (e) {
      appendLog(event.data)
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket错误:', error)
  }

  ws.onclose = () => {
    console.log('WebSocket连接关闭')
  }
}

const goBack = () => {
  router.push('/patrol')
}

// 加载初始状态
const loadInitialStatus = async () => {
  let foundInMemory = false

  try {
    const res = await getBatchStatus(taskId.value, true)  // silent：任务已完成/不存在时不弹报错
    if (res.code === 0 && res.data) {
      foundInMemory = true
      updateTaskStatus(res.data)
      if (res.data.results) {
        deviceResults.value = res.data.results.map(r => ({
          ip: r.ip,
          success: r.success,
          cmd_index: r.results ? r.results.length : 0,
          cmd_total: 0,
          current_cmd: ''
        }))
      }
    }
  } catch (e) {
    console.error('加载任务状态失败:', e)
  }

  // task_manager 里找不到，从数据库历史记录加载
  if (!foundInMemory) {
    try {
      const historyRes = await getPatrolHistory({ task_id: taskId.value, page_size: 200 })
      if (historyRes.code === 0 && historyRes.data.records.length > 0) {
        const records = historyRes.data.records
        templateName.value = records[0].template_name || ''
        totalDevices.value = records.length
        successCount.value = records.filter(r => r.success).length
        failCount.value = records.filter(r => !r.success).length
        taskStatus.value = 'completed'
        deviceResults.value = records.map(r => ({
          ip: r.ip,
          success: r.success,
          cmd_index: 0,
          cmd_total: 0,
          current_cmd: ''
        }))
        logText.value = '[历史任务] 巡检已完成，切换到"巡检结果"标签页查看命令输出\n'
      }
    } catch (e) {
      console.error('加载历史任务失败:', e)
    }
  }
}

onMounted(async () => {
  await loadInitialStatus()
  // 只有活跃任务连 WebSocket（实时推送，不需要轮询）
  const isActive = taskStatus.value === 'pending' || taskStatus.value === 'running'
  if (isActive) {
    connectWebSocket()
  }
})

onBeforeUnmount(() => {
  if (ws) {
    ws.close()
    ws = null
  }
})
</script>

<style scoped>
.page-container {
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.overview-card {
  flex-shrink: 0;
}

.detail-row {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 0;
  overflow: hidden;
}

.device-panel {
  flex-shrink: 0;
  min-width: 0;
  height: 100%;
}

.splitter {
  width: 8px;
  flex-shrink: 0;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  transition: background 0.15s;
  z-index: 1;
}
.splitter:hover,
.splitter:active {
  background: #409EFF33;
}
.splitter-line {
  width: 2px;
  height: 40px;
  border-radius: 1px;
  background: #dcdfe6;
}
.splitter:hover .splitter-line,
.splitter:active .splitter-line {
  background: #409EFF;
}

.right-panel {
  flex: 1;
  min-width: 300px;
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.task-id {
  font-family: 'Consolas', monospace;
  color: #909399;
  font-size: 12px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-label.success {
  color: #67C23A;
}

.stat-label.fail {
  color: #F56C6C;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.stat-value.success-value {
  color: #67C23A;
}

.stat-value.fail-value {
  color: #F56C6C;
}

.device-card,
.log-card {
  height: calc(100vh - 280px);
  display: flex;
  flex-direction: column;
}

.device-card :deep(.el-card__body),
.log-card :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 12px;
}

.device-list {
  flex: 1;
  overflow-y: auto;
}

.device-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: all 0.15s;
  font-size: 13px;
}

.device-item:hover {
  background-color: #f5f7fa;
}

.device-item.active {
  background-color: #ecf5ff;
}

.device-ip {
  font-family: 'Consolas', monospace;
  font-size: 12px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.device-info {
  padding-left: 4px;
}

.cmd-info {
  font-size: 12px;
  color: #909399;
  margin-right: 8px;
}

.cmd-name {
  font-size: 12px;
  color: #606266;
  display: inline-block;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}

/* 结果视图 */
.result-cmds {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.result-device-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0 12px;
  flex-shrink: 0;
}

.result-cmds :deep(.el-collapse) {
  flex: 1;
  overflow-y: auto;
}

.cmd-output {
  max-height: 400px;
  overflow-y: auto;
  padding: 8px 0;
  font-size: 12px;
  line-height: 1.4;
}

.log-container,
.result-container {
  flex: 1;
  overflow-y: auto;
  border-radius: 4px;
}
.log-container {
  background-color: #1e1e1e;
  padding: 12px;
}
.result-container {
  display: flex;
  flex-direction: column;
  padding: 4px 0;
}

.result-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 14px;
}

.log-content {
  margin: 0;
  color: #d4d4d4;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}
.result-container .log-content {
  color: #303133;
  background: #f5f7fa;
  border-radius: 4px;
  padding: 8px 12px;
}
</style>

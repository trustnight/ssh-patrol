<template>
  <div class="page-container">
    <el-row :gutter="20">
      <!-- 左侧：设备选择和配置 -->
      <el-col :span="10">
        <el-card class="config-card">
          <template #header>
            <span>巡检配置</span>
          </template>

          <!-- 模板选择 -->
          <el-form label-width="80px">
            <el-form-item label="巡检模板">
              <el-select
                v-model="templateName"
                placeholder="请选择巡检模板"
                style="width: 100%"
              >
                <el-option
                  v-for="template in templateList"
                  :key="template.template_name"
                  :label="template.template_name"
                  :value="template.template_name"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="并发数">
              <el-input-number
                v-model="maxWorkers"
                :min="1"
                :max="50"
                style="width: 100%"
              />
            </el-form-item>
          </el-form>

          <!-- 设备选择 -->
          <div class="device-section">
            <div class="device-list-header">
              <el-input
                v-model="searchKeyword"
                placeholder="搜索设备IP/用户名"
                size="small"
                clearable
                style="width: 200px"
                @input="filterDevices"
              />
              <el-checkbox
                v-model="selectAll"
                :indeterminate="isIndeterminate"
                @change="handleSelectAll"
              >
                全选
              </el-checkbox>
            </div>
            <div class="device-list">
              <el-checkbox-group v-model="selectedDeviceIds">
                <div
                  v-for="device in filteredDevices"
                  :key="device.id"
                  class="device-item"
                >
                  <el-checkbox :value="device.id" :label="device.id">
                    <span class="device-ip">{{ device.ip }}</span>
                    <el-tag size="small" type="info">{{ device.manufacturer }}</el-tag>
                    <span class="device-username">{{ device.username }}</span>
                  </el-checkbox>
                </div>
                <el-empty v-if="filteredDevices.length === 0" description="暂无设备" :image-size="60" />
              </el-checkbox-group>
            </div>
            <div class="selected-count">
              已选择 <b>{{ selectedDeviceIds.length }}</b> 台设备
            </div>
          </div>

          <el-button
            type="primary"
            style="width: 100%; margin-top: 16px"
            :loading="patrolling"
            :disabled="!canStartPatrol"
            @click="handleStartPatrol"
          >
            <el-icon><VideoPlay /></el-icon>
            开始批量巡检
          </el-button>
        </el-card>
      </el-col>

      <!-- 右侧：日志和进度 -->
      <el-col :span="14">
        <el-card class="log-card">
          <template #header>
            <div class="card-header">
              <span>巡检进度</span>
              <el-tag v-if="taskId" type="primary" size="small">
                任务ID: {{ taskId.slice(0, 8) }}...
              </el-tag>
            </div>
          </template>

          <!-- 进度统计 -->
          <div class="progress-stats" v-if="showProgress">
            <el-row :gutter="20">
              <el-col :span="6">
                <el-statistic title="总设备数" :value="totalDevices" />
              </el-col>
              <el-col :span="6">
                <el-statistic title="成功" :value="successCount">
                  <template #suffix>
                    <el-icon color="#67C23A"><CircleCheck /></el-icon>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="6">
                <el-statistic title="失败" :value="failCount">
                  <template #suffix>
                    <el-icon color="#F56C6C"><CircleClose /></el-icon>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="6">
                <el-statistic title="进度" :value="progressPercent" suffix="%" />
              </el-col>
            </el-row>
            <el-progress
              :percentage="progressPercent"
              :stroke-width="10"
              :status="progressStatus"
              style="margin-top: 12px"
            />
          </div>

          <!-- 实时日志区域 -->
          <div class="log-area">
            <div class="log-header">
              <span>实时日志</span>
              <el-button
                size="small"
                link
                :disabled="!logText"
                @click="clearLog"
              >
                清空
              </el-button>
            </div>
            <div ref="logContainer" class="log-container">
              <pre class="log-content">{{ logText || '等待开始巡检...' }}</pre>
            </div>
          </div>
        </el-card>

        <!-- 巡检结果列表 -->
        <el-card v-if="showResults" class="result-card" style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <span>巡检结果</span>
              <span>共 {{ patrolResults.length }} 台设备</span>
            </div>
          </template>
          <el-table :data="patrolResults" style="width: 100%" size="small">
            <el-table-column prop="ip" label="设备IP" width="140" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.success ? 'success' : 'danger'" size="small">
                  {{ row.success ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="命令数" width="80">
              <template #default="{ row }">
                {{ row.results ? row.results.length : 0 }}
              </template>
            </el-table-column>
            <el-table-column prop="error_msg" label="错误信息" show-overflow-tooltip />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  link
                  size="small"
                  @click="viewResultDetail(row)"
                >
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 结果详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="巡检详情" width="70%">
      <div v-if="currentDetail">
        <el-descriptions :column="3" size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="设备IP">{{ currentDetail.ip }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentDetail.success ? 'success' : 'danger'" size="small">
              {{ currentDetail.success ? '成功' : '失败' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="命令数">
            {{ currentDetail.results ? currentDetail.results.length : 0 }}
          </el-descriptions-item>
        </el-descriptions>
        <el-collapse v-if="currentDetail.results">
          <el-collapse-item
            v-for="(item, index) in currentDetail.results"
            :key="index"
            :title="`${index + 1}. ${item.command}`"
            :name="index"
          >
            <div class="detail-output">
              <pre>{{ item.output || '无输出' }}</pre>
              <div v-if="item.error" class="detail-error">
                <el-tag type="danger">错误: {{ item.error }}</el-tag>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDeviceList } from '@/api/devices'
import { getTemplateList } from '@/api/templates'
import { startBatchPatrol, getBatchStatus } from '@/api/patrol'

const route = useRoute()

// 模板列表
const templateList = ref([])
const templateName = ref('')

// 设备列表
const deviceList = ref([])
const searchKeyword = ref('')
const selectedDeviceIds = ref([])
const selectAll = ref(false)
const isIndeterminate = ref(false)

// 并发数
const maxWorkers = ref(5)

// 巡检状态
const patrolling = ref(false)
const taskId = ref('')
const showProgress = ref(false)
const showResults = ref(false)
const totalDevices = ref(0)
const successCount = ref(0)
const failCount = ref(0)
const logText = ref('')
const logContainer = ref(null)
const patrolResults = ref([])

// 详情对话框
const detailDialogVisible = ref(false)
const currentDetail = ref(null)

// WebSocket连接
let ws = null

// 定时轮询
let pollTimer = null

// 过滤后的设备列表
const filteredDevices = computed(() => {
  if (!searchKeyword.value) {
    return deviceList.value
  }
  const keyword = searchKeyword.value.toLowerCase()
  return deviceList.value.filter(d =>
    d.ip.toLowerCase().includes(keyword) ||
    d.username.toLowerCase().includes(keyword)
  )
})

// 是否可以开始巡检
const canStartPatrol = computed(() => {
  if (!templateName.value) return false
  return selectedDeviceIds.value.length > 0
})

// 进度百分比
const progressPercent = computed(() => {
  if (totalDevices.value === 0) return 0
  return Math.round(((successCount.value + failCount.value) / totalDevices.value) * 100)
})

// 进度状态
const progressStatus = computed(() => {
  if (successCount.value + failCount.value < totalDevices.value) {
    return ''
  }
  return failCount.value > 0 ? 'warning' : 'success'
})

// 加载模板列表
const loadTemplateList = async () => {
  try {
    const res = await getTemplateList()
    if (res.code === 0) {
      templateList.value = res.data.templates || []
      if (templateList.value.length > 0) {
        templateName.value = templateList.value[0].template_name
      }
    }
  } catch (error) {
    console.error('加载模板列表失败:', error)
  }
}

// 加载设备列表
const loadDeviceList = async () => {
  try {
    const res = await getDeviceList()
    if (res.code === 0) {
      deviceList.value = res.data.devices || []
    }
  } catch (error) {
    console.error('加载设备列表失败:', error)
  }
}

// 过滤设备
const filterDevices = () => {
  // 搜索时自动更新选择状态
  updateSelectAllStatus()
}

// 全选/取消全选
const handleSelectAll = (val) => {
  if (val) {
    selectedDeviceIds.value = filteredDevices.value.map(d => d.id)
    isIndeterminate.value = false
  } else {
    selectedDeviceIds.value = []
    isIndeterminate.value = false
  }
}

// 更新全选状态
const updateSelectAllStatus = () => {
  const filteredIds = filteredDevices.value.map(d => d.id)
  const selectedInFiltered = selectedDeviceIds.value.filter(id => filteredIds.includes(id))
  
  if (selectedInFiltered.length === 0) {
    selectAll.value = false
    isIndeterminate.value = false
  } else if (selectedInFiltered.length === filteredIds.length) {
    selectAll.value = true
    isIndeterminate.value = false
  } else {
    selectAll.value = false
    isIndeterminate.value = true
  }
}

// 追加日志
const appendLog = (text) => {
  logText.value += text
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

// 清空日志
const clearLog = () => {
  logText.value = ''
}

// 定时轮询状态
const startPollStatus = () => {
  stopPollStatus()
  pollTimer = setInterval(async () => {
    if (!taskId.value) return
    try {
      const res = await getBatchStatus(taskId.value)
      if (res.code === 0) {
        updateTaskStatus(res.data)
      }
    } catch (e) {
      // 忽略轮询错误
    }
  }, 2000) // 每2秒轮询一次
}

const stopPollStatus = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 连接WebSocket
const connectWebSocket = (tid) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/patrol/${tid}`
  
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
      } else if (data.type === 'error') {
        appendLog(`\n错误: ${data.message}\n`)
      }
    } catch (e) {
      appendLog(event.data)
    }
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket错误:', error)
    appendLog('\nWebSocket连接错误\n')
  }
  
  ws.onclose = () => {
    console.log('WebSocket连接关闭')
  }
}

// 更新任务状态
const updateTaskStatus = (status) => {
  const prevCompleted = (successCount.value + failCount.value)
  const nowCompleted = (status.success_count || 0) + (status.fail_count || 0)

  totalDevices.value = status.total_devices || 0
  successCount.value = status.success_count || 0
  failCount.value = status.fail_count || 0

  if (status.results) {
    patrolResults.value = status.results
  }

  // 任务完成时停止轮询并显示结果
  if (status.status === 'completed' || status.status === 'failed') {
    patrolling.value = false
    showResults.value = true
    stopPollStatus()
    appendLog('\n========== 巡检结束 ==========\n')
  }
}

// 开始批量巡检
const handleStartPatrol = async () => {
  if (!templateName.value) {
    ElMessage.warning('请选择巡检模板')
    return
  }
  
  if (selectedDeviceIds.value.length === 0) {
    ElMessage.warning('请至少选择一台设备')
    return
  }
  
  patrolling.value = true
  showProgress.value = true
  showResults.value = false
  logText.value = ''
  totalDevices.value = 0
  successCount.value = 0
  failCount.value = 0
  patrolResults.value = []
  
  appendLog('正在启动批量巡检任务...\n')
  
  try {
    const requestData = {
      template_name: templateName.value,
      max_workers: maxWorkers.value,
      device_ids: selectedDeviceIds.value
    }
    
    const res = await startBatchPatrol(requestData)
    
    if (res.code === 0) {
      taskId.value = res.data.task_id
      totalDevices.value = res.data.total_devices
      
      appendLog(`任务创建成功，任务ID: ${res.data.task_id}\n`)
      appendLog(`共 ${res.data.total_devices} 台设备待巡检\n\n`)
      
      // 连接WebSocket获取实时日志
      connectWebSocket(res.data.task_id)
      // 启动定时轮询作为备份
      startPollStatus()
    } else {
      patrolling.value = false
      ElMessage.error(res.message || '创建任务失败')
    }
  } catch (error) {
    patrolling.value = false
    appendLog(`\n创建任务失败: ${error.message}\n`)
    ElMessage.error('创建任务失败: ' + error.message)
  }
}

// 查看结果详情
const viewResultDetail = (row) => {
  currentDetail.value = row
  detailDialogVisible.value = true
}

onMounted(() => {
  loadTemplateList()
  loadDeviceList()
})

// 监听设备列表加载完成，自动选中从设备管理页带过来的设备
watch(deviceList, (newList) => {
  if (newList.length > 0 && route.query.deviceIds) {
    const ids = String(route.query.deviceIds).split(',').map(id => parseInt(id)).filter(id => !isNaN(id))
    if (ids.length > 0) {
      selectedDeviceIds.value = ids
      updateSelectAllStatus()
    }
  }
})

onBeforeUnmount(() => {
  if (ws) {
    ws.close()
    ws = null
  }
  stopPollStatus()
})
</script>

<style scoped>
.page-container {
  height: 100%;
}

.config-card {
  height: 100%;
}

.log-card {
  height: auto;
  min-height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.device-section {
  margin-top: 16px;
}

.device-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.device-list {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 8px;
}

.device-item {
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.device-item:hover {
  background-color: #f5f7fa;
}

.device-ip {
  margin-right: 8px;
  font-family: 'Consolas', monospace;
}

.device-username {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}

.selected-count {
  margin-top: 8px;
  color: #606266;
  font-size: 13px;
  text-align: right;
}

.selected-count b {
  color: #409EFF;
}

.progress-stats {
  padding: 16px;
  background-color: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 16px;
}

.log-area {
  display: flex;
  flex-direction: column;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.log-container {
  height: 400px;
  overflow-y: auto;
  background-color: #1e1e1e;
  border-radius: 4px;
  padding: 12px;
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

.result-card {
  max-height: 400px;
  overflow-y: auto;
}

.detail-output {
  background-color: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  max-height: 300px;
  overflow-y: auto;
}

.detail-output pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.detail-error {
  margin-top: 8px;
}
</style>

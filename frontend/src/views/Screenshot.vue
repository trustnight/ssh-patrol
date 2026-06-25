<template>
  <div class="page-container">
    <el-row :gutter="20">
      <!-- 左侧：URL导入 + 截图任务 -->
      <el-col :span="14">
        <!-- URL导入卡片 -->
        <el-card>
          <template #header>
            <div class="card-header">
              <span>URL列表</span>
              <div class="header-actions">
                <el-upload
                  :show-file-list="false"
                  :before-upload="handleFileUpload"
                  accept=".txt"
                >
                  <el-button type="primary" size="small">
                    <el-icon><Upload /></el-icon>
                    导入TXT
                  </el-button>
                </el-upload>
                <el-button type="danger" size="small" @click="handleClearUrls" :disabled="urlList.length === 0">
                  <el-icon><Delete /></el-icon>
                  清空
                </el-button>
              </div>
            </div>
          </template>

          <div class="url-input-area">
            <el-input
              v-model="urlText"
              type="textarea"
              :rows="4"
              placeholder="请输入URL列表，每行一个，例如：&#10;https://192.168.1.100:8588&#10;https://192.168.1.102"
            />
            <el-button type="success" @click="handleImportText" style="margin-top: 8px" size="small">
              <el-icon><Plus /></el-icon>
              导入文本
            </el-button>
            <span v-if="urlList.length > 0" class="url-count">已导入 {{ urlList.length }} 个URL</span>
          </div>
        </el-card>

        <!-- 截图任务卡片 -->
        <el-card style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span>截图任务</span>
              <el-button type="primary" size="small" @click="showCreateDialog" :disabled="urlList.length === 0">
                <el-icon><Plus /></el-icon>
                创建任务
              </el-button>
            </div>
          </template>

          <!-- 任务列表 -->
          <div v-if="taskList.length > 0" class="task-list">
            <div
              v-for="task in taskList"
              :key="task.id"
              class="task-item"
              :class="{ active: currentTaskId === task.id }"
              @click="switchTask(task.id)"
            >
              <span class="task-name">{{ task.name }}</span>
              <span class="task-time">{{ task.created_at }}</span>
              <el-button type="danger" link size="small" @click.stop="handleDeleteTask(task.id)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <el-empty v-else description="暂无截图任务，请先导入URL再创建任务" :image-size="60" />

          <!-- 当前任务设备列表 -->
          <template v-if="currentTaskId">
            <div class="device-section-header">
              <span>任务设备列表</span>
              <span class="device-count">
                待处理: <b>{{ pendingDevices.length }}</b> |
                已完成: <b>{{ doneDevices.length }}</b>
              </span>
            </div>

            <!-- 待处理设备 -->
            <div class="device-pending-list">
              <div
                v-for="device in pendingDevices"
                :key="device.id"
                class="device-row"
                :class="{ active: device.status === 'active' }"
                @click="handleSelectDevice(device)"
              >
                <div class="device-info">
                  <el-icon v-if="device.status === 'active'" class="active-icon" color="#67c23a"><VideoPlay /></el-icon>
                  <el-icon v-else class="pending-icon"><Clock /></el-icon>
                  <span class="device-ip">{{ device.ip }}</span>
                  <span class="device-url" :title="device.url">{{ device.url }}</span>
                </div>
                <div class="device-meta">
                  <el-tag v-if="device.status === 'active'" type="success" size="small">当前</el-tag>
                  <span v-if="device.screenshot_count > 0" class="screenshot-count">{{ device.screenshot_count }}张</span>
                </div>
              </div>
            </div>

            <!-- 已完成设备 -->
            <div v-if="doneDevices.length > 0" class="device-done-section">
              <div class="done-header" @click="showDoneDevices = !showDoneDevices">
                <el-icon><ArrowDown v-if="!showDoneDevices" /><ArrowUp v-else /></el-icon>
                <span>已完成 ({{ doneDevices.length }})</span>
              </div>
              <div v-show="showDoneDevices" class="device-done-list">
                <div
                  v-for="device in doneDevices"
                  :key="device.id"
                  class="device-row done"
                  @click="handleSelectDevice(device)"
                >
                  <div class="device-info">
                    <el-icon class="done-icon" color="#909399"><CircleCheck /></el-icon>
                    <span class="device-ip">{{ device.ip }}</span>
                    <span class="device-url" :title="device.url">{{ device.url }}</span>
                  </div>
                  <div class="device-meta">
                    <span class="screenshot-count">{{ device.screenshot_count }}张</span>
                  </div>
                </div>
              </div>
            </div>

            <el-empty v-if="taskDevices.length === 0" description="该任务没有设备" :image-size="40" />
          </template>
        </el-card>
      </el-col>

      <!-- 右侧：截图控制 -->
      <el-col :span="10">
        <!-- 状态卡片 -->
        <el-card class="status-card">
          <template #header>
            <div class="card-header">
              <span>截图状态</span>
              <el-tag :type="status.is_listening ? 'success' : 'danger'" size="small">
                {{ status.is_listening ? '监听中' : '未监听' }}
              </el-tag>
            </div>
          </template>

          <div class="status-info">
            <div class="status-item">
              <span class="label">当前IP：</span>
              <span class="value">{{ status.current_ip || '未选择' }}</span>
            </div>
            <div class="status-item">
              <span class="label">当前URL：</span>
              <span class="value url-value">{{ status.current_url || '未选择' }}</span>
            </div>
            <div class="status-item">
              <span class="label">截图数量：</span>
              <span class="value">{{ status.screenshot_count }}</span>
            </div>
            <div class="status-item">
              <span class="label">快捷键：</span>
              <span class="value">{{ status.hotkey }}</span>
            </div>
          </div>

          <div class="action-buttons">
            <el-button
              type="primary"
              size="large"
              @click="handleManualCapture"
              :disabled="!status.current_ip"
            >
              <el-icon><Camera /></el-icon>
              手动截图
            </el-button>
            <el-button
              :type="status.is_listening ? 'danger' : 'success'"
              size="large"
              @click="handleToggleListening"
            >
              <el-icon><VideoPlay v-if="!status.is_listening" /><VideoPause v-else /></el-icon>
              {{ status.is_listening ? '停止监听' : '开始监听' }}
            </el-button>
          </div>
        </el-card>

        <!-- 快捷键设置 -->
        <el-card style="margin-top: 16px">
          <template #header>
            <span>快捷键设置</span>
          </template>
          <div class="hotkey-setting">
            <el-input
              v-model="hotkeyInput"
              placeholder="例如: <alt>+q, <ctrl>+<shift>+s"
            >
              <template #append>
                <el-button @click="handleSetHotkey">保存</el-button>
              </template>
            </el-input>
            <div class="hotkey-tips">
              <p>支持的修饰键: &lt;ctrl&gt;, &lt;alt&gt;, &lt;shift&gt;</p>
              <p>示例: &lt;alt&gt;+q, &lt;ctrl&gt;+&lt;shift&gt;+s, f12</p>
            </div>
          </div>
        </el-card>

        <!-- 截图历史 -->
        <el-card style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span>截图历史</span>
              <div class="header-actions">
                <el-button type="success" link @click="handleOpenFolder">
                  <el-icon><FolderOpened /></el-icon>
                  打开文件夹
                </el-button>
                <el-button type="primary" link @click="loadHistory">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </div>
          </template>
          <el-table :data="historyList" style="width: 100%" max-height="300">
            <el-table-column prop="ip" label="IP" width="120" />
            <el-table-column prop="file_path" label="文件路径" show-overflow-tooltip />
            <el-table-column prop="created_at" label="时间" width="160" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 创建任务对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建截图任务" width="500px">
      <el-form label-width="80px">
        <el-form-item label="任务名称">
          <el-input v-model="newTaskName" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="选择URL">
          <div class="dialog-url-select">
            <el-checkbox
              v-model="selectAllUrls"
              :indeterminate="isIndeterminate"
              @change="handleSelectAllUrls"
            >
              全选 ({{ urlList.length }}个)
            </el-checkbox>
            <div class="dialog-url-list">
              <el-checkbox-group v-model="selectedUrlIds">
                <div v-for="url in urlList" :key="url.id" class="dialog-url-item">
                  <el-checkbox :value="url.id">
                    <span class="dialog-url-ip">{{ url.ip }}</span>
                    <span class="dialog-url-text">{{ url.url }}</span>
                  </el-checkbox>
                </div>
              </el-checkbox-group>
            </div>
            <div class="dialog-selected-count">
              已选择 <b>{{ selectedUrlIds.length }}</b> 个URL
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreateTask" :disabled="selectedUrlIds.length === 0 || !newTaskName.trim()">
          确认创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  importUrls, getUrlList, clearUrls,
  createScreenshotTask, getScreenshotTasks, getTaskDevices,
  setTaskActiveDevice, completeTaskDevice, deleteScreenshotTask,
  captureScreen, getScreenshotStatus, setHotkey,
  getScreenshotHistory, startListening, stopListening,
  openScreenshotFolder
} from '@/api/screenshot'

// ==================== 状态 ====================
const loading = ref(false)
const urlText = ref('')
const urlList = ref([])
const historyList = ref([])
const hotkeyInput = ref('<alt>+q')

const status = ref({
  current_url: null,
  current_ip: null,
  current_task_id: null,
  current_device_id: null,
  screenshot_count: 0,
  is_listening: false,
  hotkey: '<alt>+q'
})

// 任务相关
const taskList = ref([])
const currentTaskId = ref(null)
const taskDevices = ref([])
const showDoneDevices = ref(true)

// 创建任务对话框
const createDialogVisible = ref(false)
const newTaskName = ref('')
const selectedUrlIds = ref([])
const selectAllUrls = ref(false)

// 截图计数变化检测（用于自动刷新历史）
const lastScreenshotCount = ref(0)

// 定时器
let statusTimer = null

// ==================== 计算属性 ====================

const pendingDevices = computed(() => {
  return taskDevices.value.filter(d => d.status === 'active' || d.status === 'pending')
})

const doneDevices = computed(() => {
  return taskDevices.value.filter(d => d.status === 'done')
})

const isIndeterminate = computed(() => {
  const selected = selectedUrlIds.value.length
  return selected > 0 && selected < urlList.value.length
})

// ==================== 生命周期 ====================

onMounted(() => {
  loadUrls()
  loadTasks()
  loadHistory()
  refreshStatus()
  statusTimer = setInterval(refreshStatus, 2000)
})

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer)
  }
})

// ==================== URL管理 ====================

async function loadUrls() {
  loading.value = true
  try {
    const res = await getUrlList()
    if (res.code === 0) {
      urlList.value = res.data.urls
    }
  } catch (e) {
    ElMessage.error('加载URL列表失败')
  } finally {
    loading.value = false
  }
}

async function handleImportText() {
  if (!urlText.value.trim()) {
    ElMessage.warning('请输入URL')
    return
  }
  try {
    const res = await importUrls(urlText.value)
    if (res.code === 0) {
      ElMessage.success(res.message)
      urlText.value = ''
      loadUrls()
    } else {
      ElMessage.warning(res.message)
    }
  } catch (e) {
    ElMessage.error('导入失败')
  }
}

function handleFileUpload(file) {
  const reader = new FileReader()
  reader.onload = async (e) => {
    const text = e.target.result
    try {
      const res = await importUrls(text)
      if (res.code === 0) {
        ElMessage.success(res.message)
        loadUrls()
      } else {
        ElMessage.warning(res.message)
      }
    } catch (err) {
      ElMessage.error('导入失败')
    }
  }
  reader.readAsText(file)
  return false
}

async function handleClearUrls() {
  try {
    await ElMessageBox.confirm('确定要清空所有URL吗？', '提示', { type: 'warning' })
    await clearUrls()
    urlList.value = []
    ElMessage.success('已清空')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('清空失败')
    }
  }
}

// ==================== 任务管理 ====================

async function loadTasks() {
  try {
    const res = await getScreenshotTasks()
    if (res.code === 0) {
      taskList.value = res.data.tasks
    }
  } catch (e) {
    // 静默处理
  }
}

async function loadTaskDevices(taskId) {
  if (!taskId) {
    taskDevices.value = []
    return
  }
  try {
    const res = await getTaskDevices(taskId)
    if (res.code === 0) {
      taskDevices.value = res.data.devices
    }
  } catch (e) {
    // 静默处理
  }
}

function switchTask(taskId) {
  currentTaskId.value = taskId
  loadTaskDevices(taskId)
}

function showCreateDialog() {
  newTaskName.value = `截图任务 ${new Date().toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}`
  selectedUrlIds.value = []
  selectAllUrls.value = false
  createDialogVisible.value = true
}

function handleSelectAllUrls(checked) {
  if (checked) {
    selectedUrlIds.value = urlList.value.map(u => u.id)
  } else {
    selectedUrlIds.value = []
  }
}

async function handleCreateTask() {
  if (!newTaskName.value.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  if (selectedUrlIds.value.length === 0) {
    ElMessage.warning('请选择至少一个URL')
    return
  }
  try {
    const res = await createScreenshotTask({
      name: newTaskName.value.trim(),
      url_ids: selectedUrlIds.value
    })
    if (res.code === 0) {
      ElMessage.success('任务创建成功')
      createDialogVisible.value = false
      await loadTasks()
      // 自动切换到新创建的任务
      switchTask(res.data.task_id)
    } else {
      ElMessage.error(res.message)
    }
  } catch (e) {
    ElMessage.error('创建任务失败')
  }
}

async function handleDeleteTask(taskId) {
  try {
    await ElMessageBox.confirm('确定要删除该截图任务吗？', '提示', { type: 'warning' })
    await deleteScreenshotTask(taskId)
    ElMessage.success('任务已删除')
    if (currentTaskId.value === taskId) {
      currentTaskId.value = null
      taskDevices.value = []
    }
    loadTasks()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// ==================== 设备操作 ====================

async function handleSelectDevice(device) {
  if (!currentTaskId.value) return

  try {
    const res = await setTaskActiveDevice(currentTaskId.value, device.id)
    if (res.code === 0) {
      ElMessage.success(`已选择设备: ${device.ip}`)
      // 刷新设备列表（状态会重新排序）
      await loadTaskDevices(currentTaskId.value)
      refreshStatus()
    } else {
      ElMessage.error(res.message)
    }
  } catch (e) {
    ElMessage.error('设置失败')
  }
}

// ==================== 截图操作 ====================

async function refreshStatus() {
  try {
    const res = await getScreenshotStatus()
    if (res.code === 0) {
      status.value = res.data
      hotkeyInput.value = res.data.hotkey
      // 检测截图计数变化（快捷键截图后自动刷新历史和设备列表）
      if (res.data.screenshot_count !== lastScreenshotCount.value) {
        lastScreenshotCount.value = res.data.screenshot_count
        loadHistory()
        if (currentTaskId.value) {
          loadTaskDevices(currentTaskId.value)
        }
      }
    }
  } catch (e) {
    // 静默处理
  }
}

async function handleManualCapture() {
  try {
    const res = await captureScreen()
    if (res.code === 0) {
      ElMessage.success('截图成功: ' + res.data.file_path)
      refreshStatus()
      loadHistory()
    } else {
      ElMessage.error(res.message)
    }
  } catch (e) {
    ElMessage.error('截图失败')
  }
}

async function handleToggleListening() {
  try {
    if (status.value.is_listening) {
      // 停止监听前，把当前活跃设备标记为完成
      if (currentTaskId.value && status.value.current_device_id) {
        await completeTaskDevice(currentTaskId.value)
        await loadTaskDevices(currentTaskId.value)
      }
      const res = await stopListening()
      if (res.code === 0) {
        ElMessage.success('已停止监听')
        refreshStatus()
      } else {
        ElMessage.error(res.message)
      }
    } else {
      const res = await startListening()
      if (res.code === 0) {
        ElMessage.success(res.message)
        refreshStatus()
      } else {
        ElMessage.error(res.message)
      }
    }
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function handleSetHotkey() {
  if (!hotkeyInput.value.trim()) {
    ElMessage.warning('请输入快捷键')
    return
  }
  try {
    const res = await setHotkey(hotkeyInput.value)
    if (res.code === 0) {
      ElMessage.success(res.message)
      refreshStatus()
    } else {
      ElMessage.error(res.message)
    }
  } catch (e) {
    ElMessage.error('设置失败')
  }
}

async function loadHistory() {
  try {
    const res = await getScreenshotHistory()
    if (res.code === 0) {
      historyList.value = res.data.records
    }
  } catch (e) {
    ElMessage.error('加载截图历史失败')
  }
}

async function handleOpenFolder() {
  try {
    const res = await openScreenshotFolder()
    if (res.code !== 0) {
      ElMessage.error(res.message)
    }
  } catch (e) {
    ElMessage.error('打开文件夹失败')
  }
}
</script>

<style scoped>
.page-container {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.url-input-area {
  margin-bottom: 8px;
}

.url-count {
  margin-left: 12px;
  font-size: 13px;
  color: #909399;
}

/* 任务列表 */
.task-list {
  margin-bottom: 16px;
}

.task-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.task-item:hover {
  border-color: #409eff;
  background: #f0f7ff;
}

.task-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.task-name {
  flex: 1;
  font-weight: 500;
}

.task-time {
  font-size: 12px;
  color: #909399;
  margin-right: 8px;
}

/* 设备列表 */
.device-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 16px 0 10px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
  font-weight: 500;
  font-size: 14px;
}

.device-count {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}

.device-count b {
  color: #303133;
}

.device-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.device-row:hover {
  border-color: #409eff;
  background: #f0f7ff;
}

.device-row.active {
  border-color: #67c23a;
  background: #f0f9eb;
}

.device-row.done {
  opacity: 0.65;
  cursor: pointer;
}

.device-row.done:hover {
  opacity: 1;
}

.device-info {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.active-icon,
.pending-icon,
.done-icon {
  flex-shrink: 0;
}

.device-ip {
  font-weight: 500;
  flex-shrink: 0;
}

.device-url {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.device-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  margin-left: 8px;
}

.screenshot-count {
  font-size: 12px;
  color: #909399;
}

/* 已完成区域 */
.device-done-section {
  margin-top: 8px;
}

.done-header {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #909399;
  cursor: pointer;
  padding: 4px 0;
}

.done-header:hover {
  color: #409eff;
}

.device-done-list {
  margin-top: 4px;
}

/* 状态卡片 */
.status-card {
  margin-bottom: 0;
}

.status-info {
  padding: 8px 0;
}

.status-item {
  display: flex;
  margin-bottom: 10px;
  font-size: 14px;
}

.status-item .label {
  color: #909399;
  width: 80px;
  flex-shrink: 0;
}

.status-item .value {
  color: #303133;
  word-break: break-all;
}

.url-value {
  font-size: 12px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.action-buttons .el-button {
  flex: 1;
}

/* 快捷键 */
.hotkey-setting {
  padding: 4px 0;
}

.hotkey-tips {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.hotkey-tips p {
  margin: 3px 0;
}

/* 创建任务对话框 */
.dialog-url-select {
  width: 100%;
}

.dialog-url-list {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 8px;
  margin-top: 8px;
}

.dialog-url-item {
  padding: 4px 0;
}

.dialog-url-ip {
  font-weight: 500;
  margin-right: 8px;
}

.dialog-url-text {
  font-size: 12px;
  color: #909399;
}

.dialog-selected-count {
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
}

.dialog-selected-count b {
  color: #303133;
}
</style>

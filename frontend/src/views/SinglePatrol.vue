<template>
  <div class="page-container">
    <!-- 设备信息表单 -->
    <el-card class="form-card">
      <template #header>
        <div class="card-header">
          <span>设备信息</span>
        </div>
      </template>
      <el-form :model="form" label-width="100px">
        <el-form-item label="选择设备">
          <el-select
            v-model="selectedDeviceId"
            placeholder="从已保存设备中选择（可选）"
            style="width: 100%"
            filterable
            clearable
            @change="handleDeviceSelect"
          >
            <el-option
              v-for="device in deviceList"
              :key="device.id"
              :label="`${maskText(device.ip, 'ip')} - ${device.manufacturer}`"
              :value="device.id"
            />
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="设备IP">
              <el-input v-model="form.ip" placeholder="请输入设备IP地址" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="端口">
              <el-input v-model="form.port" placeholder="默认22" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="用户名">
              <el-input v-model="form.username" placeholder="请输入用户名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="密码">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
                show-password
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="设备厂商">
              <el-select v-model="form.manufacturer" placeholder="请选择厂商" style="width: 100%">
                <el-option label="Hillstone" value="Hillstone" />
                <el-option label="Huawei" value="Huawei" />
                <el-option label="Cisco" value="Cisco" />
                <el-option label="H3C" value="H3C" />
                <el-option label="其他" value="Other" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="巡检模板">
              <el-select
                v-model="form.template_name"
                placeholder="请选择巡检模板"
                style="width: 100%"
                @change="handleTemplateChange"
              >
                <el-option
                  v-for="template in templateList"
                  :key="template.template_name"
                  :label="template.template_name"
                  :value="template.template_name"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" :loading="patrolling" @click="handlePatrol">
            <el-icon><VideoPlay /></el-icon>
            开始巡检
          </el-button>
          <el-button :disabled="patrolling" @click="handleReset">
            <el-icon><RefreshRight /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 巡检日志区域 -->
    <el-card v-if="showLog" class="log-card">
      <template #header>
        <div class="card-header">
          <span>巡检日志</span>
          <el-tag :type="patrolling ? 'warning' : (patrolSuccess ? 'success' : 'danger')" size="small">
            {{ patrolling ? '巡检中...' : (patrolSuccess ? '巡检成功' : '巡检失败') }}
          </el-tag>
        </div>
      </template>
      <el-progress v-if="patrolling" :percentage="progress" :stroke-width="8" status="success" />
      <div ref="logContainer" class="log-container">
        <pre class="log-content">{{ logText }}</pre>
      </div>
    </el-card>

    <!-- 巡检结果区域 -->
    <el-card v-if="showResult" class="result-card">
      <template #header>
        <div class="card-header">
          <span>巡检结果</span>
          <div>
            <el-tag v-if="patrolResult.log_path" type="success" size="small">
              日志已保存: {{ patrolResult.log_path }}
            </el-tag>
          </div>
        </div>
      </template>
      <el-collapse>
        <el-collapse-item
          v-for="(item, index) in patrolResult.results"
          :key="index"
          :title="`${index + 1}. ${item.command}`"
          :name="index"
        >
          <div class="result-output">
            <pre>{{ item.output || '无输出' }}</pre>
            <div v-if="item.error" class="result-error">
              <el-tag type="danger">错误: {{ item.error }}</el-tag>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { singlePatrol } from '@/api/patrol'
import { getDeviceList } from '@/api/devices'
import { getTemplateList } from '@/api/templates'
import { useSettings } from '@/composables/useSettings'

const { maskText } = useSettings()

// 设备列表
const deviceList = ref([])

// 模板列表
const templateList = ref([])

// 选中的设备ID
const selectedDeviceId = ref(null)

// 表单数据
const form = reactive({
  ip: '',
  port: '22',
  username: '',
  password: '',
  manufacturer: 'Hillstone',
  template_name: ''
})

// 巡检状态
const patrolling = ref(false)
const showLog = ref(false)
const showResult = ref(false)
const progress = ref(0)
const logText = ref('')
const patrolSuccess = ref(false)
const logContainer = ref(null)

// 巡检结果
const patrolResult = reactive({
  success: false,
  ip: '',
  results: [],
  error_msg: '',
  log_path: ''
})

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

// 加载模板列表
const loadTemplateList = async () => {
  try {
    const res = await getTemplateList()
    if (res.code === 0) {
      templateList.value = res.data.templates || []
      if (templateList.value.length > 0 && !form.template_name) {
        form.template_name = templateList.value[0].template_name
      }
    }
  } catch (error) {
    console.error('加载模板列表失败:', error)
  }
}

// 选择设备
const handleDeviceSelect = async (deviceId) => {
  if (!deviceId) return
  const device = deviceList.value.find(d => d.id === deviceId)
  if (device) {
    form.ip = device.ip
    form.port = String(device.port || 22)
    form.username = device.username
    form.manufacturer = device.manufacturer || 'Hillstone'
    form.password = ''
  }
}

// 模板变化
const handleTemplateChange = () => {
  // 模板变化时可以做一些处理
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

// 开始巡检
const handlePatrol = async () => {
  if (!form.ip) {
    ElMessage.warning('请输入设备IP地址')
    return
  }
  if (!form.username) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!form.password && !selectedDeviceId.value) {
    ElMessage.warning('请输入密码')
    return
  }
  if (!form.template_name) {
    ElMessage.warning('请选择巡检模板')
    return
  }

  patrolling.value = true
  showLog.value = true
  showResult.value = false
  logText.value = ''
  progress.value = 0
  patrolSuccess.value = false

  appendLog('正在连接设备并执行巡检...\n')
  appendLog(`设备IP: ${maskText(form.ip, 'ip')}\n`)
  appendLog(`厂商: ${form.manufacturer}\n`)
  appendLog(`模板: ${form.template_name}\n`)
  appendLog('----------------------------------------\n')

  try {
    const requestData = {
      template_name: form.template_name
    }

    if (selectedDeviceId.value) {
      requestData.device_id = selectedDeviceId.value
    } else {
      requestData.device_info = {
        ip: form.ip,
        port: parseInt(form.port) || 22,
        username: form.username,
        password: form.password,
        manufacturer: form.manufacturer,
        template_name: form.template_name
      }
    }

    const res = await singlePatrol(requestData)

    if (res.code === 0) {
      patrolSuccess.value = res.data.success
      patrolResult.success = res.data.success
      patrolResult.ip = res.data.ip
      patrolResult.results = res.data.results || []
      patrolResult.error_msg = res.data.error_msg || ''
      patrolResult.log_path = res.data.log_path || ''

      progress.value = 100
      appendLog('\n----------------------------------------\n')
      appendLog(`巡检完成，共执行 ${patrolResult.results.length} 条命令\n`)

      if (res.data.success) {
        appendLog('状态: 成功\n')
        ElMessage.success('巡检完成')
      } else {
        appendLog(`状态: 失败 - ${res.data.error_msg || '未知错误'}\n`)
        ElMessage.error(`巡检失败: ${res.data.error_msg || '未知错误'}`)
      }

      if (res.data.log_path) {
        appendLog(`日志已保存至: ${res.data.log_path}\n`)
      }

      showResult.value = true
    } else {
      appendLog(`巡检失败: ${res.message}\n`)
      ElMessage.error(res.message || '巡检失败')
    }
  } catch (error) {
    appendLog(`\n巡检异常: ${error.message}\n`)
    ElMessage.error('巡检失败: ' + error.message)
  } finally {
    patrolling.value = false
  }
}

// 重置表单
const handleReset = () => {
  form.ip = ''
  form.port = '22'
  form.username = ''
  form.password = ''
  form.manufacturer = 'Hillstone'
  if (templateList.value.length > 0) {
    form.template_name = templateList.value[0].template_name
  } else {
    form.template_name = ''
  }
  selectedDeviceId.value = null
  showLog.value = false
  showResult.value = false
  logText.value = ''
  progress.value = 0
  patrolSuccess.value = false
  patrolResult.results = []
  patrolResult.log_path = ''
}

onMounted(() => {
  loadDeviceList()
  loadTemplateList()
})
</script>

<style scoped>
.page-container {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-card {
  margin-top: 0;
}

.log-container {
  height: 300px;
  overflow-y: auto;
  background-color: #1e1e1e;
  border-radius: 4px;
  padding: 12px;
  margin-top: 12px;
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
  margin-top: 0;
}

.result-output {
  background-color: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  max-height: 400px;
  overflow-y: auto;
}

.result-output pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.result-error {
  margin-top: 8px;
}
</style>

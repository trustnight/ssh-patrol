<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>设备管理</span>
          <div class="header-actions">
            <el-button type="info" @click="handleDownloadTemplate">
              <el-icon><Document /></el-icon>
              下载模板
            </el-button>
            <el-button type="success" @click="handleExport">
              <el-icon><Download /></el-icon>
              导出
            </el-button>
            <el-button type="warning" @click="handleImport">
              <el-icon><Upload /></el-icon>
              导入
            </el-button>
            <el-button
              type="primary"
              :disabled="selectedIds.length === 0"
              @click="handleBatchPatrol"
            >
              <el-icon><VideoPlay /></el-icon>
              批量巡检 ({{ selectedIds.length }})
            </el-button>
            <el-button
              type="danger"
              :disabled="selectedIds.length === 0"
              @click="handleBatchDelete"
            >
              <el-icon><Delete /></el-icon>
              批量删除 ({{ selectedIds.length }})
            </el-button>
            <el-select
              v-model="filterManufacturer"
              placeholder="厂商筛选"
              size="default"
              clearable
              style="width: 150px"
              @change="handleSearch"
            >
              <el-option label="Hillstone" value="Hillstone" />
              <el-option label="Huawei" value="Huawei" />
              <el-option label="Cisco" value="Cisco" />
              <el-option label="H3C" value="H3C" />
              <el-option label="其他" value="Other" />
            </el-select>
            <el-input
              v-model="searchKeyword"
              placeholder="搜索IP/用户名"
              style="width: 220px"
              clearable
              @keyup.enter="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="handleAdd">
              <el-icon><Plus /></el-icon>
              新增设备
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="deviceList"
        style="width: 100%"
        v-loading="loading"
        border
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="sort_order" label="序号" width="70" />
        <el-table-column prop="manufacturer" label="厂商" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.manufacturer }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="device_type" label="设备类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.device_type" size="small" type="warning">{{ row.device_type }}</el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP地址" width="160">
          <template #default="{ row }">
            <span class="ip-text">{{ maskText(row.ip, 'ip') }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="port" label="端口" width="100" />
        <el-table-column prop="url" label="Web管理URL" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.url">{{ maskText(row.url, 'url') }}</span>
            <span v-else class="text-muted">未配置</span>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" width="140">
          <template #default="{ row }">
            {{ maskText(row.username, 'username') }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ row.created_at || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button
              type="success"
              link
              size="small"
              @click="handleConnect(row)"
            >
              <el-icon><Connection /></el-icon>
              连接终端
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 新增/编辑设备对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="deviceForm"
        :rules="formRules"
        label-width="80px"
      >
        <el-form-item label="序号" prop="sort_order">
          <el-input-number
            v-model="deviceForm.sort_order"
            :min="0"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="厂商" prop="manufacturer">
          <el-select v-model="deviceForm.manufacturer" style="width: 100%">
            <el-option label="Hillstone" value="Hillstone" />
            <el-option label="Huawei" value="Huawei" />
            <el-option label="Cisco" value="Cisco" />
            <el-option label="H3C" value="H3C" />
            <el-option label="其他" value="Other" />
          </el-select>
        </el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="deviceForm.device_type" style="width: 100%" placeholder="请选择设备类型">
            <el-option label="FW" value="FW" />
            <el-option label="SW" value="SW" />
            <el-option label="RT" value="RT" />
            <el-option label="IPS" value="IPS" />
            <el-option label="WAF" value="WAF" />
            <el-option label="DDOS" value="DDOS" />
            <el-option label="WOC" value="WOC" />
            <el-option label="other" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="IP地址" prop="ip">
          <el-input v-model="deviceForm.ip" placeholder="请输入设备IP地址" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number
            v-model="deviceForm.port"
            :min="1"
            :max="65535"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="deviceForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="deviceForm.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="Web管理URL" prop="url">
          <el-input v-model="deviceForm.url" placeholder="如：https://192.168.1.1:8588" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 导入设备对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入设备" width="500px">
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".csv"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将CSV文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            CSV格式：order,manufacturer,device_type,ip,username,password,port,url<br>
            示例：1,Hillstone,FW,192.168.1.1,admin,password123,22,https://192.168.1.1:8588
          </div>
        </template>
      </el-upload>
      <div v-if="importPreview.length > 0" class="import-preview">
        <div class="preview-header">预览 ({{ importPreview.length }} 台设备)：</div>
        <el-table :data="importPreview" size="small" max-height="200">
          <el-table-column prop="sort_order" label="序号" width="60" />
          <el-table-column prop="manufacturer" label="厂商" width="100" />
          <el-table-column prop="device_type" label="设备类型" width="90" />
          <el-table-column prop="ip" label="IP" width="140" />
          <el-table-column prop="port" label="端口" width="70" />
          <el-table-column prop="username" label="用户名" width="120" />
          <el-table-column prop="url" label="Web管理URL" show-overflow-tooltip />
        </el-table>
      </div>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="importPreview.length === 0" @click="handleImportSubmit">
          确认导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { encrypt } from '@/utils/crypto'
import { useSettings } from '@/composables/useSettings'
import {
  getDeviceList,
  addDevice,
  updateDevice,
  deleteDevice,
  exportDevices,
  refreshTemplate,
  batchDeleteDevices
} from '@/api/devices'

const router = useRouter()
const { maskText } = useSettings()

// 搜索和筛选
const searchKeyword = ref('')
const filterManufacturer = ref('')

// 列表数据
const allDevices = ref([])
const deviceList = ref([])
const total = ref(0)
const loading = ref(false)
const pageSize = ref(20)
const currentPage = ref(1)

const slicePage = () => {
  const start = (currentPage.value - 1) * pageSize.value
  deviceList.value = allDevices.value.slice(start, start + pageSize.value)
  total.value = allDevices.value.length
}

// 选中的设备ID
const selectedIds = ref([])

// 对话框
const dialogVisible = ref(false)
const dialogType = ref('add')
const submitting = ref(false)
const formRef = ref(null)

// 导入对话框
const importDialogVisible = ref(false)
const importPreview = ref([])
const importing = ref(false)
const uploadRef = ref(null)

const dialogTitle = computed(() => {
  return dialogType.value === 'add' ? '新增设备' : '编辑设备'
})

// 设备表单
const deviceForm = reactive({
  id: null,
  sort_order: 0,
  manufacturer: 'Hillstone',
  device_type: 'FW',
  ip: '',
  port: 22,
  username: '',
  password: '',
  url: ''
})

// 表单验证规则
const formRules = {
  manufacturer: [
    { required: true, message: '请选择厂商', trigger: 'change' }
  ],
  ip: [
    { required: true, message: '请输入IP地址', trigger: 'blur' }
  ],
  port: [
    { required: true, message: '请输入端口', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

// 加载设备列表
const loadList = async () => {
  loading.value = true
  try {
    const params = {}
    if (searchKeyword.value) {
      params.keyword = searchKeyword.value
    }
    if (filterManufacturer.value) {
      params.manufacturer = filterManufacturer.value
    }
    const res = await getDeviceList(params)
    if (res.code === 0) {
      allDevices.value = res.data.devices || []
      currentPage.value = 1
      slicePage()
    }
  } catch (error) {
    console.error('加载设备列表失败:', error)
    ElMessage.error('加载设备列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  loadList()
}

// 分页变化
const handlePageChange = () => {
  slicePage()
}

// 新增
const handleAdd = () => {
  dialogType.value = 'add'
  deviceForm.id = null
  deviceForm.sort_order = 0
  deviceForm.manufacturer = 'Hillstone'
  deviceForm.device_type = 'FW'
  deviceForm.ip = ''
  deviceForm.port = 22
  deviceForm.username = ''
  deviceForm.password = ''
  deviceForm.url = ''
  dialogVisible.value = true
  
  nextTick(() => {
    if (formRef.value) {
      formRef.value.resetFields()
    }
  })
}

// 编辑
const handleEdit = (row) => {
  dialogType.value = 'edit'
  deviceForm.id = row.id
  deviceForm.sort_order = row.sort_order || 0
  deviceForm.manufacturer = row.manufacturer
  deviceForm.device_type = row.device_type || ''
  deviceForm.ip = row.ip
  deviceForm.port = row.port
  deviceForm.username = row.username
  deviceForm.password = ''
  deviceForm.url = row.url || ''
  dialogVisible.value = true
}

// 提交
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
  } catch (error) {
    return
  }
  
  submitting.value = true
  
  try {
    const data = {
      sort_order: deviceForm.sort_order || 0,
      manufacturer: deviceForm.manufacturer,
      device_type: deviceForm.device_type || '',
      ip: deviceForm.ip,
      port: deviceForm.port,
      username: deviceForm.username,
      password: encrypt(deviceForm.password),
      url: deviceForm.url || ''
    }
    
    let res
    if (dialogType.value === 'add') {
      res = await addDevice(data)
    } else {
      res = await updateDevice(deviceForm.id, data)
    }
    
    if (res.code === 0) {
      if (res.data && res.data.updated) {
        ElMessage.success(`设备已存在，已覆盖更新: ${deviceForm.ip}`)
      } else {
        ElMessage.success(dialogType.value === 'add' ? '添加成功' : '更新成功')
      }
      dialogVisible.value = false
      loadList()
    } else {
      ElMessage.error(res.message || '操作失败')
    }
  } catch (error) {
    console.error('提交失败:', error)
    ElMessage.error('操作失败: ' + error.message)
  } finally {
    submitting.value = false
  }
}

// 连接终端
const handleConnect = (row) => {
  router.push({
    path: '/ssh-terminal',
    query: {
      deviceId: row.id,
      ip: row.ip,
      port: row.port,
      username: row.username,
      manufacturer: row.manufacturer
    }
  })
}

// 删除
const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除设备"${row.ip}"吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      const res = await deleteDevice(row.id)
      if (res.code === 0) {
        ElMessage.success('删除成功')
        loadList()
      } else {
        ElMessage.error(res.message || '删除失败')
      }
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败: ' + error.message)
    }
  }).catch(() => {})
}

// 导出设备（含加密密码，防止泄露）
const handleExport = async () => {
  try {
    const res = await exportDevices()
    if (res.code !== 0 || !res.data || !res.data.devices) {
      ElMessage.error('获取导出数据失败')
      return
    }
    const devices = res.data.devices
    if (devices.length === 0) {
      ElMessage.warning('没有可导出的设备')
      return
    }
    const csvContent = [
      'order,manufacturer,device_type,ip,username,password,port,url',
      ...devices.map(d =>
        `${d.sort_order || 0},${d.manufacturer},${d.device_type || ''},${d.ip},${d.username},${d.password || ''},${d.port || 22},${d.url || ''}`
      )
    ].join('\n')
    const BOM = '﻿'
    const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `devices_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    ElMessage.success(`已导出 ${devices.length} 台设备（密码已加密）`)
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

// 下载导入模板
const handleDownloadTemplate = async () => {
  try {
    await refreshTemplate()
    ElMessage.success('模板已刷新（密码已加密）')
  } catch (e) {
    ElMessage.error('刷新模板失败')
  }
}

// 表格选择变化
const handleSelectionChange = (selection) => {
  selectedIds.value = selection.map(item => item.id)
}

// 批量删除设备
const handleBatchDelete = () => {
  ElMessageBox.confirm(
    `确定要删除选中的 ${selectedIds.value.length} 台设备吗？`,
    '提示',
    { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    try {
      await batchDeleteDevices(selectedIds.value)
      ElMessage.success(`已删除 ${selectedIds.value.length} 台设备`)
      selectedIds.value = []
      loadList()
    } catch (e) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// 跳转到批量巡检
const handleBatchPatrol = () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要巡检的设备')
    return
  }
  router.push({
    path: '/batch-patrol',
    query: { deviceIds: selectedIds.value.join(',') }
  })
}

// 打开导入对话框
const handleImport = () => {
  importPreview.value = []
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
  importDialogVisible.value = true
}

// 处理文件选择
const handleFileChange = (file) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const content = e.target.result
      const lines = content.split('\n').filter(line => line.trim())
      const devices = []

      for (let i = 1; i < lines.length; i++) { // 跳过表头
        const line = lines[i].trim()
        if (!line) continue
        const parts = line.split(',')
        // CSV列序: order,manufacturer,device_type,ip,username,password,port,url
        if (parts.length >= 7) {
          devices.push({
            sort_order: parseInt(parts[0].trim()) || 0,
            manufacturer: parts[1].trim(),
            device_type: parts[2].trim() || '',
            ip: parts[3].trim(),
            username: parts[4].trim(),
            password: parts[5].trim(),
            port: parseInt(parts[6].trim()) || 22,
            url: (parts.length >= 8 ? parts[7].trim() : '')
          })
        }
      }

      if (devices.length > 0) {
        importPreview.value = devices
      } else {
        ElMessage.warning('未找到有效的设备数据')
      }
    } catch (error) {
      ElMessage.error('解析CSV文件失败: ' + error.message)
    }
  }
  reader.readAsText(file.raw)
}

// 确认导入
const handleImportSubmit = async () => {
  if (importPreview.value.length === 0) {
    ElMessage.warning('请先选择要导入的文件')
    return
  }

  importing.value = true
  let addCount = 0    // 新增
  let updateCount = 0 // IP重复，已覆盖更新
  let failCount = 0

  try {
    for (const device of importPreview.value) {
      try {
        const password = encrypt(device.password)
        const res = await addDevice({
          sort_order: device.sort_order || 0,
          manufacturer: device.manufacturer,
          device_type: device.device_type || '',
          ip: device.ip,
          port: device.port,
          username: device.username,
          password: password,
          url: device.url || ''
        })
        if (res.code === 0) {
          if (res.data && res.data.updated) {
            updateCount++
          } else {
            addCount++
          }
        } else {
          failCount++
        }
      } catch (e) {
        failCount++
      }
    }

    // 导入完成后，刷新模板CSV（密码已加密写入磁盘，无弹窗）
    const successCount = addCount + updateCount
    if (successCount > 0) {
      await refreshTemplate()
    }

    const parts = [`新增 ${addCount} 台`]
    if (updateCount > 0) parts.push(`覆盖更新 ${updateCount} 台`)
    if (failCount > 0) parts.push(`失败 ${failCount} 台`)
    ElMessage.success(`导入完成：${parts.join('，')}` + (successCount > 0 ? '，CSV密码已加密' : ''))

    importDialogVisible.value = false
    loadList()
  } catch (error) {
    ElMessage.error('导入失败: ' + error.message)
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.page-container {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.ip-text {
  font-family: 'Consolas', monospace;
  color: #409EFF;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.text-muted {
  color: #c0c4cc;
  font-size: 12px;
}

.import-preview {
  margin-top: 16px;
}

.preview-header {
  margin-bottom: 8px;
  color: #606266;
  font-size: 14px;
}
</style>

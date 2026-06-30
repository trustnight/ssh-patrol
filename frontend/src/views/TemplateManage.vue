<template>
  <div class="page-container">
    <!-- 顶部选择区 -->
    <el-card class="header-card">
      <el-form :inline="true" :model="selectForm">
        <el-form-item label="模板">
          <el-select
            v-model="selectForm.templateName"
            placeholder="请选择模板"
            style="width: 250px"
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
        <el-form-item label="厂商">
          <el-select
            v-model="selectForm.manufacturer"
            placeholder="请选择厂商"
            style="width: 200px"
            @change="handleManufacturerChange"
          >
            <el-option
              v-for="mfr in manufacturerList"
              :key="mfr"
              :label="mfr"
              :value="mfr"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="设备类型">
          <el-select
            v-model="selectForm.deviceType"
            placeholder="设备类型"
            style="width: 160px"
            @change="handleDeviceTypeChange"
          >
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
        <el-form-item>
          <el-tag :type="templateTagType" size="small">{{ templateTagText }}</el-tag>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 主体内容 -->
    <el-row :gutter="20" class="content-row">
      <!-- 左侧：命令列表 -->
      <el-col :span="12">
        <el-card class="command-list-card">
          <template #header>
            <div class="card-header">
              <span>命令列表</span>
              <span class="command-count">共 {{ commandList.length }} 条命令</span>
            </div>
          </template>
          <div class="command-list">
            <div
              v-for="(cmd, index) in commandList"
              :key="index"
              class="command-item"
              :class="{ active: currentEditIndex === index }"
              @click="selectCommand(index)"
            >
              <div class="command-order">{{ index + 1 }}</div>
              <div class="command-info">
                <div class="command-text">{{ cmd.command }}</div>
                <el-tag v-if="cmd.is_custom" size="small" type="warning">自定义</el-tag>
              </div>
              <div class="command-actions">
                <el-button
                  type="primary"
                  link
                  size="small"
                  @click.stop="moveUp(index)"
                  :disabled="index === 0"
                >
                  <el-icon><Top /></el-icon>
                </el-button>
                <el-button
                  type="primary"
                  link
                  size="small"
                  @click.stop="moveDown(index)"
                  :disabled="index === commandList.length - 1"
                >
                  <el-icon><Bottom /></el-icon>
                </el-button>
                <el-button
                  type="danger"
                  link
                  size="small"
                  @click.stop="deleteCommand(index)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <el-empty v-if="commandList.length === 0" description="暂无命令" :image-size="80" />
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：命令编辑区 -->
      <el-col :span="12">
        <el-card class="edit-card">
          <template #header>
            <div class="card-header">
              <span>命令编辑</span>
            </div>
          </template>

          <!-- 添加新命令 -->
          <div class="add-section">
            <div class="section-title">添加新命令</div>
            <el-input
              v-model="newCommand"
              type="textarea"
              :rows="2"
              placeholder="请输入命令内容"
              resize="none"
            />
            <div class="add-actions">
              <el-button type="primary" @click="addCommand" :disabled="!newCommand.trim()">
                <el-icon><Plus /></el-icon>
                添加命令
              </el-button>
            </div>
          </div>

          <el-divider />

          <!-- 批量导入 -->
          <div class="batch-section">
            <div class="section-title">批量导入命令</div>
            <el-input
              v-model="batchCommands"
              type="textarea"
              :rows="6"
              placeholder="每行一条命令，例如：&#10;show version&#10;show interface&#10;show running-config"
              resize="vertical"
            />
            <div class="batch-actions">
              <el-button type="success" @click="batchAddCommands" :disabled="!batchCommands.trim()">
                <el-icon><Upload /></el-icon>
                批量添加
              </el-button>
              <el-button @click="batchCommands = ''">
                清空
              </el-button>
            </div>
          </div>

          <el-divider />

          <!-- 保存自定义模板 -->
          <div class="save-section">
            <div class="section-title">保存自定义模板</div>
            <el-form :model="saveForm" label-width="80px">
              <el-form-item label="模板名称">
                <el-input v-model="saveForm.templateName" placeholder="请输入模板名称" />
              </el-form-item>
              <el-form-item label="厂商">
                <el-select v-model="saveForm.manufacturer" placeholder="请选择厂商" style="width: 100%">
                  <el-option label="Hillstone" value="Hillstone" />
                  <el-option label="Huawei" value="Huawei" />
                  <el-option label="Cisco" value="Cisco" />
                  <el-option label="H3C" value="H3C" />
                  <el-option label="其他" value="Other" />
                </el-select>
              </el-form-item>
              <el-form-item label="设备类型">
                <el-select v-model="saveForm.deviceType" placeholder="设备类型" style="width: 100%">
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
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="saving"
                  @click="saveCustomTemplate"
                  :disabled="commandList.length === 0"
                >
                  <el-icon><DocumentAdd /></el-icon>
                  保存为自定义模板
                </el-button>
                <el-button @click="resetTemplate" :disabled="commandList.length === 0">
                  重置为内置模板
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getTemplateList,
  getTemplateManufacturers,
  getTemplateCommands,
  saveCustomTemplate as apiSaveCustomTemplate
} from '@/api/templates'

// 模板列表
const templateList = ref([])

// 厂商列表
const manufacturerList = ref([])

// 选择表单
const selectForm = reactive({
  templateName: '',
  manufacturer: '',
  deviceType: 'FW'
})

// 命令列表
const commandList = ref([])

// 当前编辑的命令索引
const currentEditIndex = ref(-1)

// 新命令
const newCommand = ref('')

// 批量命令
const batchCommands = ref('')

// 保存表单
const saveForm = reactive({
  templateName: '',
  manufacturer: '',
  deviceType: 'FW'
})

// 保存中
const saving = ref(false)

// 是否为自定义模板
const isCustomTemplate = computed(() => {
  return commandList.value.some(cmd => cmd.is_custom)
})

const templateTagType = computed(() => isCustomTemplate.value ? 'warning' : 'info')
const templateTagText = computed(() => isCustomTemplate.value ? '自定义模板' : '内置模板')

// 加载模板列表
const loadTemplateList = async () => {
  try {
    const res = await getTemplateList()
    if (res.code === 0) {
      templateList.value = res.data.templates || []
      if (templateList.value.length > 0 && !selectForm.templateName) {
        selectForm.templateName = templateList.value[0].template_name
        handleTemplateChange()
      }
    }
  } catch (error) {
    console.error('加载模板列表失败:', error)
    ElMessage.error('加载模板列表失败')
  }
}

// 模板变化
const handleTemplateChange = async () => {
  if (!selectForm.templateName) return
  
  manufacturerList.value = []
  selectForm.manufacturer = ''
  selectForm.deviceType = 'FW'
  commandList.value = []
  
  try {
    const res = await getTemplateManufacturers(selectForm.templateName)
    if (res.code === 0) {
      manufacturerList.value = res.data.manufacturers || []
      if (manufacturerList.value.length > 0) {
        selectForm.manufacturer = manufacturerList.value[0]
        await loadCommands()
      }
    }
  } catch (error) {
    console.error('加载厂商列表失败:', error)
  }
}

// 加载命令列表
const loadCommands = async () => {
  if (!selectForm.templateName || !selectForm.manufacturer) return
  
  try {
    const res = await getTemplateCommands(selectForm.templateName, selectForm.manufacturer, selectForm.deviceType || '')
    if (res.code === 0) {
      commandList.value = res.data.commands || []
      // 更新保存表单
      saveForm.templateName = selectForm.templateName
      saveForm.manufacturer = selectForm.manufacturer
    }
  } catch (error) {
    console.error('加载命令列表失败:', error)
    ElMessage.error('加载命令列表失败')
  }
}

// 设备类型变化
const handleDeviceTypeChange = async () => {
  await loadCommands()
}

// 选择命令
const selectCommand = (index) => {
  currentEditIndex.value = index
  newCommand.value = commandList.value[index].command
}

// 添加命令
const addCommand = () => {
  const cmd = newCommand.value.trim()
  if (!cmd) return
  
  commandList.value.push({
    command: cmd,
    cmd_order: commandList.value.length + 1,
    is_custom: true
  })
  
  newCommand.value = ''
  ElMessage.success('命令添加成功')
}

// 批量添加命令
const batchAddCommands = () => {
  const lines = batchCommands.value.split('\n').filter(line => line.trim())
  if (lines.length === 0) {
    ElMessage.warning('请输入命令')
    return
  }
  
  let count = 0
  lines.forEach(line => {
    const cmd = line.trim()
    if (cmd) {
      commandList.value.push({
        command: cmd,
        cmd_order: commandList.value.length + 1,
        is_custom: true
      })
      count++
    }
  })
  
  batchCommands.value = ''
  ElMessage.success(`成功添加 ${count} 条命令`)
}

// 删除命令
const deleteCommand = (index) => {
  ElMessageBox.confirm('确定要删除这条命令吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    commandList.value.splice(index, 1)
    // 更新排序
    commandList.value.forEach((cmd, i) => {
      cmd.cmd_order = i + 1
    })
    if (currentEditIndex.value === index) {
      currentEditIndex.value = -1
      newCommand.value = ''
    } else if (currentEditIndex.value > index) {
      currentEditIndex.value--
    }
    ElMessage.success('删除成功')
  }).catch(() => {})
}

// 上移
const moveUp = (index) => {
  if (index === 0) return
  const temp = commandList.value[index]
  commandList.value[index] = commandList.value[index - 1]
  commandList.value[index - 1] = temp
  // 更新排序
  commandList.value.forEach((cmd, i) => {
    cmd.cmd_order = i + 1
  })
  if (currentEditIndex.value === index) {
    currentEditIndex.value = index - 1
  } else if (currentEditIndex.value === index - 1) {
    currentEditIndex.value = index
  }
}

// 下移
const moveDown = (index) => {
  if (index === commandList.value.length - 1) return
  const temp = commandList.value[index]
  commandList.value[index] = commandList.value[index + 1]
  commandList.value[index + 1] = temp
  // 更新排序
  commandList.value.forEach((cmd, i) => {
    cmd.cmd_order = i + 1
  })
  if (currentEditIndex.value === index) {
    currentEditIndex.value = index + 1
  } else if (currentEditIndex.value === index + 1) {
    currentEditIndex.value = index
  }
}

// 保存自定义模板
const saveCustomTemplate = async () => {
  if (!saveForm.templateName) {
    ElMessage.warning('请输入模板名称')
    return
  }
  if (!saveForm.manufacturer) {
    ElMessage.warning('请选择厂商')
    return
  }
  if (commandList.value.length === 0) {
    ElMessage.warning('命令列表不能为空')
    return
  }
  
  saving.value = true
  
  try {
    const commands = commandList.value.map(cmd => cmd.command)
    const res = await apiSaveCustomTemplate(
      saveForm.templateName,
      saveForm.manufacturer,
      commands,
      saveForm.deviceType || ''
    )
    
    if (res.code === 0) {
      ElMessage.success('自定义模板保存成功')
      // 重新加载模板列表
      loadTemplateList()
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (error) {
    console.error('保存模板失败:', error)
    ElMessage.error('保存失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

// 重置为内置模板
const resetTemplate = () => {
  ElMessageBox.confirm('确定要重置为内置模板吗？所有自定义修改将丢失。', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    handleManufacturerChange()
    ElMessage.success('已重置为内置模板')
  }).catch(() => {})
}

onMounted(() => {
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
  gap: 16px;
}

.header-card {
  flex-shrink: 0;
}

.content-row {
  flex: 1;
  min-height: 0;
}

.command-list-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.command-list-card :deep(.el-card__body) {
  flex: 1;
  overflow-y: auto;
}

.edit-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.edit-card :deep(.el-card__body) {
  flex: 1;
  overflow-y: auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.command-count {
  font-size: 13px;
  color: #909399;
}

.command-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.command-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  background-color: #fff;
}

.command-item:hover {
  border-color: #409EFF;
  background-color: #ecf5ff;
}

.command-item.active {
  border-color: #409EFF;
  background-color: #ecf5ff;
}

.command-order {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #606266;
  margin-right: 12px;
  flex-shrink: 0;
}

.command-item.active .command-order {
  background-color: #409EFF;
  color: #fff;
}

.command-info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.command-text {
  flex: 1;
  font-family: 'Consolas', monospace;
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.command-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.command-item:hover .command-actions {
  opacity: 1;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 12px;
}

.add-actions,
.batch-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.save-section {
  padding-top: 8px;
}
</style>

<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>巡检任务</span>
          <div class="header-actions">
            <el-button type="danger" :disabled="selectedTaskIds.length === 0" @click="handleBatchDeleteTasks">
              <el-icon><Delete /></el-icon>
              批量删除 ({{ selectedTaskIds.length }})
            </el-button>
            <el-button type="primary" @click="handleCreateTask">
              <el-icon><Plus /></el-icon>
              新建任务
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
        @selection-change="handleTaskSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="task_id" label="任务ID" width="200" show-overflow-tooltip />
        <el-table-column prop="template_name" label="命令模板" width="150" />
        <el-table-column prop="total_devices" label="设备数" width="100" align="center" />
        <el-table-column prop="success_count" label="成功" width="80" align="center">
          <template #default="{ row }">
            <span style="color: #67c23a">{{ row.success_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="fail_count" label="失败" width="80" align="center">
          <template #default="{ row }">
            <span style="color: #f56c6c">{{ row.fail_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleViewDetail(row)">
              查看详情
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
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 新建任务对话框 -->
    <el-dialog v-model="dialogVisible" title="新建巡检任务" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="任务类型">
          <el-radio-group v-model="form.task_type">
            <el-radio value="single">单设备巡检</el-radio>
            <el-radio value="batch">批量巡检</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="命令模板">
          <el-select v-model="form.template_name" placeholder="请选择模板" style="width: 100%">
            <el-option
              v-for="tpl in templateList"
              :key="tpl.template_id"
              :label="tpl.template_name"
              :value="tpl.template_name"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.task_type === 'single'" label="选择设备">
          <el-select v-model="form.device_id" placeholder="请选择设备" style="width: 100%">
            <el-option
              v-for="dev in deviceList"
              :key="dev.id"
              :label="`${dev.ip} (${dev.manufacturer})`"
              :value="dev.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.task_type === 'batch'" label="选择设备">
          <div style="display: flex; flex-direction: column; gap: 6px; width: 100%">
            <div style="display: flex; gap: 8px">
              <el-button size="small" @click="selectAllDevices">全选</el-button>
              <el-button size="small" @click="form.device_ids = []">取消全选</el-button>
              <span style="line-height: 24px; color: #909399; font-size: 13px">
                已选 {{ form.device_ids.length }} / {{ deviceList.length }} 台
              </span>
            </div>
            <el-select
              v-model="form.device_ids"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              placeholder="搜索或选择设备"
              style="width: 100%"
            >
              <el-option
                v-for="dev in deviceList"
                :key="dev.id"
                :label="`${dev.ip} (${dev.manufacturer})`"
                :value="dev.id"
              />
            </el-select>
          </div>
        </el-form-item>
        <el-form-item v-if="form.task_type === 'batch'" label="并发数">
          <el-input-number v-model="form.max_workers" :min="1" :max="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          开始巡检
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTemplateList } from '@/api/templates'
import { getDeviceList } from '@/api/devices'
import { startBatchPatrol, getPatrolHistory, getRunningTasks, batchDeleteTasks } from '@/api/patrol'

const router = useRouter()

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const dialogVisible = ref(false)
const submitting = ref(false)
const templateList = ref([])
const deviceList = ref([])
const form = ref({
  task_type: 'single',
  template_name: '',
  device_id: null,
  device_ids: [],
  max_workers: 5
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
  return map[status] || 'info'
}

const loadData = async () => {
  loading.value = true
  const taskMap = {}

  try {
    // 运行中任务（不阻塞历史记录）
    try {
      const runningRes = await getRunningTasks()
      if (runningRes.code === 0 && runningRes.data && runningRes.data.tasks) {
        for (const task of runningRes.data.tasks) {
          taskMap[task.task_id] = {
            task_id: task.task_id,
            template_name: task.template_name || '',
            total_devices: task.total_devices || 0,
            success_count: task.success_count || 0,
            fail_count: task.fail_count || 0,
            status: task.status || 'pending',
            created_at: task.created_at
              ? new Date(task.created_at * 1000).toLocaleString('zh-CN')
              : ''
          }
        }
      }
    } catch (e) {
      console.error('加载运行中任务失败:', e)
    }

    // 历史记录
    try {
      const historyRes = await getPatrolHistory({
        page: currentPage.value,
        page_size: pageSize.value
      })
      if (historyRes.code === 0) {
        const records = historyRes.data.records || []
        for (const record of records) {
          const tid = record.task_id
          if (taskMap[tid]) {
            taskMap[tid].total_devices++
            if (record.success) taskMap[tid].success_count++
            else taskMap[tid].fail_count++
            if (!taskMap[tid].created_at) taskMap[tid].created_at = record.created_at
          } else {
            taskMap[tid] = {
              task_id: tid,
              template_name: record.template_name,
              total_devices: 1,
              success_count: record.success ? 1 : 0,
              fail_count: record.success ? 0 : 1,
              status: 'completed',
              created_at: record.created_at
            }
          }
        }
      }
    } catch (e) {
      console.error('加载历史记录失败:', e)
    }

    tableData.value = Object.values(taskMap).sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    )
    total.value = tableData.value.length
  } catch (e) {
    console.error('加载任务列表失败:', e)
  } finally {
    loading.value = false
  }
}

const selectedTaskIds = ref([])

const handleTaskSelectionChange = (selection) => {
  selectedTaskIds.value = selection.map(item => item.task_id)
}

const handleBatchDeleteTasks = () => {
  ElMessageBox.confirm(
    `确定要删除选中的 ${selectedTaskIds.value.length} 个任务吗？`,
    '提示',
    { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    try {
      await batchDeleteTasks(selectedTaskIds.value)
      ElMessage.success('删除成功')
      selectedTaskIds.value = []
      loadData()
    } catch (e) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const selectAllDevices = () => {
  form.value.device_ids = deviceList.value.map(d => d.id)
}

const handleCreateTask = async () => {
  form.value = {
    task_type: 'single',
    template_name: '',
    device_id: null,
    device_ids: [],
    max_workers: 5
  }
  try {
    const [tplRes, devRes] = await Promise.all([
      getTemplateList(),
      getDeviceList()
    ])
    if (tplRes.code === 0) {
      templateList.value = tplRes.data.templates || []
      if (templateList.value.length > 0 && !form.value.template_name) {
        form.value.template_name = templateList.value[0].template_name
      }
    }
    if (devRes.code === 0) {
      deviceList.value = devRes.data.devices || []
    }
  } catch (e) {
    console.error('加载数据失败:', e)
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!form.value.template_name) {
    ElMessage.warning('请选择命令模板')
    return
  }
  if (form.value.task_type === 'single' && !form.value.device_id) {
    ElMessage.warning('请选择设备')
    return
  }
  if (form.value.task_type === 'batch' && form.value.device_ids.length === 0) {
    ElMessage.warning('请选择至少一个设备')
    return
  }

  submitting.value = true
  try {
    const deviceIds = form.value.task_type === 'single'
      ? [form.value.device_id]
      : form.value.device_ids

    const res = await startBatchPatrol({
      device_ids: deviceIds,
      template_name: form.value.template_name,
      max_workers: form.value.max_workers
    })

    if (res.code === 0) {
      ElMessage.success('任务已启动')
      dialogVisible.value = false
      setTimeout(() => {
        loadData()
      }, 500)
    }
  } catch (e) {
    console.error('启动任务失败:', e)
  } finally {
    submitting.value = false
  }
}

const handleViewDetail = (row) => {
  router.push(`/patrol/${row.task_id}`)
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.page-container {
  min-height: calc(100vh - 120px);
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

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>

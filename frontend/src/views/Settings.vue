<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>系统设置</span>
        </div>
      </template>

      <!-- 脱敏展示 -->
      <div class="setting-section">
        <div class="setting-label">
          <el-icon :size="20"><View /></el-icon>
          <span>脱敏展示</span>
        </div>
        <div class="setting-desc">
          开启后，设备管理、截图界面的IP、用户名、密码将以星号掩藏，防止信息泄露
        </div>
        <el-switch
          v-model="desensitize"
          active-text="已开启"
          inactive-text="已关闭"
          size="large"
        />
      </div>

      <el-divider />

      <!-- 主题切换 -->
      <div class="setting-section">
        <div class="setting-label">
          <el-icon :size="20"><Sunny /></el-icon>
          <span>主题切换</span>
        </div>
        <div class="setting-desc">
          选择界面主题风格，支持浅色、深色、跟随系统
        </div>
        <el-radio-group v-model="theme" size="large">
          <el-radio-button value="light">
            <el-icon><Sunny /></el-icon>
            浅色
          </el-radio-button>
          <el-radio-button value="dark">
            <el-icon><Moon /></el-icon>
            深色
          </el-radio-button>
          <el-radio-button value="system">
            <el-icon><Monitor /></el-icon>
            跟随系统
          </el-radio-button>
        </el-radio-group>
      </div>

    </el-card>
  </div>
</template>

<script setup>
import { useSettings } from '@/composables/useSettings'

const { desensitize, theme } = useSettings()
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

.setting-section {
  display: flex;
  align-items: flex-start;
  gap: 24px;
  padding: 8px 0;
  flex-wrap: wrap;
}

.setting-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 500;
  color: #303133;
  min-width: 100px;
  flex-shrink: 0;
}

.setting-desc {
  flex: 1;
  min-width: 200px;
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}

/* 深色主题适配 */
html.dark .el-card {
  background-color: #1d1e1f;
  border-color: #333;
}
html.dark .setting-label {
  color: #e5e7eb;
}
html.dark .setting-desc {
  color: #9ca3af;
}
</style>

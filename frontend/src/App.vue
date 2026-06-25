<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon :size="24" color="#409EFF"><Monitor /></el-icon>
        <span class="logo-text">巡检助手</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="menu"
        @select="handleMenuSelect"
        background-color="#001529"
        text-color="rgba(255, 255, 255, 0.85)"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/patrol">
          <el-icon><List /></el-icon>
          <span>巡检任务</span>
        </el-menu-item>
        <el-menu-item index="/ssh-terminal">
          <el-icon><Terminal /></el-icon>
          <span>SSH终端</span>
        </el-menu-item>
        <el-menu-item index="/template-manage">
          <el-icon><Document /></el-icon>
          <span>模板管理</span>
        </el-menu-item>
        <el-menu-item index="/device-manage">
          <el-icon><Setting /></el-icon>
          <span>设备管理</span>
        </el-menu-item>
        <el-menu-item index="/screenshot">
          <el-icon><Camera /></el-icon>
          <span>截图</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="right-container">
      <el-header class="header">
        <div class="header-title">{{ currentPageTitle }}</div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const handleMenuSelect = (index) => {
  if (route.path !== index) {
    router.push(index)
  }
}

const activeMenu = computed(() => {
  if (route.path.startsWith('/patrol/')) {
    return '/patrol'
  }
  return route.path
})

const currentPageTitle = computed(() => {
  const titleMap = {
    '/patrol': '巡检任务',
    '/ssh-terminal': 'SSH终端',
    '/template-manage': '模板管理',
    '/device-manage': '设备管理',
    '/screenshot': '截图'
  }
  if (route.path.startsWith('/patrol/')) {
    return '任务详情'
  }
  return titleMap[route.path] || '巡检助手'
})
</script>

<style>
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
}
</style>

<style scoped>
.layout-container {
  height: 100vh;
  width: 100%;
}

.aside {
  background-color: #001529;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-text {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
}

.menu {
  flex: 1;
  border-right: none;
}

.right-container {
  height: 100%;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  padding: 0 24px;
  height: 60px;
  flex-shrink: 0;
}

.header-title {
  font-size: 18px;
  font-weight: 500;
  color: #303133;
}

.main {
  background-color: #f5f7fa;
  padding: 20px;
  flex: 1;
  height: 0;
  min-height: 0;
  overflow: auto;
  box-sizing: border-box;
}
</style>

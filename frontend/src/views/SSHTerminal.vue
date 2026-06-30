<template>
  <div class="page-container">
    <!-- 连接配置卡片 -->
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>
            <el-icon style="margin-right: 6px; vertical-align: -2px"><Connection /></el-icon>
            远程终端
          </span>
          <div>
            <el-tag v-if="connected" type="success" size="small">
              <el-icon class="el-icon--left"><CircleCheck /></el-icon>
              已连接 {{ maskText(form.ip, 'ip') }}
            </el-tag>
            <el-tag v-else type="info" size="small">
              <el-icon class="el-icon--left"><CircleClose /></el-icon>
              未连接
            </el-tag>
            <el-tag v-if="connected" size="small" type="warning" style="margin-left: 8px">
              编码: {{ currentEncoding }}
            </el-tag>
          </div>
        </div>
      </template>
      <el-form :inline="true" :model="form" class="connect-form" @submit.prevent="handleConnect" @keydown.enter.prevent="handleConnect">
        <el-form-item label="主机">
          <el-input v-model="form.ip" placeholder="IP地址" :disabled="connected" style="width: 160px" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input v-model="form.port" placeholder="22" :disabled="connected" style="width: 80px" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="用户名" :disabled="connected" style="width: 140px" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            :placeholder="hasDeviceId ? '使用已保存的密码' : '密码'"
            show-password
            :disabled="connected || hasDeviceId"
            style="width: 140px"
          />
        </el-form-item>
        <el-form-item label="编码">
          <el-select v-model="form.encoding" :disabled="connected" style="width: 120px">
            <el-option label="UTF-8" value="utf-8" />
            <el-option label="GBK" value="gbk" />
            <el-option label="GB2312" value="gb2312" />
            <el-option label="GB18030" value="gb18030" />
            <el-option label="BIG5" value="big5" />
            <el-option label="ASCII" value="ascii" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 未连接状态：连接按钮 + 历史下拉 -->
          <template v-if="!connected">
            <el-button
              type="primary"
              :disabled="connecting"
              native-type="submit"
              @click="handleConnect"
            >
              <el-icon><Connection /></el-icon>
              连接
            </el-button>
            <el-select
              v-if="historyList.length > 0"
              v-model="selectedHistory"
              placeholder="历史记录"
              clearable
              size="default"
              style="width: 200px; margin-left: 8px"
              @change="fillFromHistory"
              @clear="selectedHistory = null"
            >
              <el-option
                v-for="item in historyList"
                :key="item.id"
                :label="`${maskText(item.ip, 'ip')}:${item.port} (${maskText(item.username || '?', 'username')})`"
                :value="item.id"
              />
            </el-select>
          </template>
          <!-- 已连接状态：断开按钮 -->
          <el-button v-if="connected" type="danger" @click="handleDisconnect">
            <el-icon><Close /></el-icon>
            断开
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 终端区域 -->
    <el-card
      class="terminal-card"
      :class="{ 'terminal-card--fullscreen': isFullscreen }"
      @mousemove="onTerminalMouseMove"
      @mouseleave="showFullscreenBtn = false"
    >
      <div class="terminal-container" ref="terminalContainer">
        <!-- 全屏 / 退出全屏按钮 —— 鼠标移到右上角时浮动显示 -->
        <transition name="fade-zoom">
          <div
            v-if="connected && showFullscreenBtn"
            class="fullscreen-toggle"
            :class="{ 'is-fullscreen': isFullscreen }"
            @click="toggleFullscreen"
          >
            <el-icon :size="16">
              <FullScreen v-if="!isFullscreen" />
              <ScaleToOriginal v-else />
            </el-icon>
          </div>
        </transition>

        <!-- 未连接状态 -->
        <div v-if="!connected && !connecting" class="terminal-placeholder">
          <div class="placeholder-logo">
            <el-icon :size="56" color="#409EFF"><Monitor /></el-icon>
            <div class="placeholder-title">巡检助手 - 远程终端</div>
          </div>
          <p class="placeholder-text">请填写连接信息并点击"连接"按钮</p>
        </div>

        <!-- 连接中 -->
        <div v-if="connecting" class="terminal-placeholder">
          <el-icon :size="48" color="#409EFF" class="is-loading"><Loading /></el-icon>
          <p class="placeholder-text">正在连接...</p>
        </div>

        <!-- xterm 终端挂载点 -->
        <div
          ref="xtermEl"
          class="xterm-wrapper"
          :style="{ display: connected ? 'block' : 'none' }"
        ></div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Terminal as XTerm } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { getTerminalHistory, saveTerminalHistory, clearTerminalHistory } from '@/api/terminal'
import { useSettings } from '@/composables/useSettings'

const route = useRoute()
const { maskText } = useSettings()

// 是否从设备管理页面跳转过来（有 deviceId）
const hasDeviceId = computed(() => !!route.query.deviceId)

// ===== 响应式状态 =====
const form = reactive({
  ip: '',
  port: '22',
  username: '',
  password: '',
  encoding: 'utf-8'
})

const connected = ref(false)
const connecting = ref(false)
const currentEncoding = ref('utf-8')
const terminalContainer = ref(null)
const xtermEl = ref(null)

// ===== 全屏 =====
const isFullscreen = ref(false)
const showFullscreenBtn = ref(false)

function onTerminalMouseMove(e) {
  if (!connected.value) return
  const rect = e.currentTarget.getBoundingClientRect()
  // 鼠标距右上角 <= 80px 时显示按钮
  const distX = rect.right - e.clientX
  const distY = e.clientY - rect.top
  showFullscreenBtn.value = distX <= 80 && distY <= 64
}

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
  // 进入全屏后隐藏按钮（需要重新 mouse move 到角落才显示）
  showFullscreenBtn.value = false
  // 全屏切换后重新 fit 终端大小
  nextTick(() => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (fitAddon) fitAddon.fit()
      })
    })
  })
}

function onKeydown(e) {
  if (e.key === 'Escape' && isFullscreen.value) {
    e.preventDefault()
    isFullscreen.value = false
    showFullscreenBtn.value = false
    nextTick(() => {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (fitAddon) fitAddon.fit()
        })
      })
    })
  }
}

// ===== 终端历史 ====="
const historyList = ref([])
const selectedHistory = ref(null)

async function loadHistory() {
  try {
    const res = await getTerminalHistory()
    if (res.code === 0) {
      historyList.value = res.data
    }
  } catch (e) { /* 忽略 */ }
}

async function handleClearHistory() {
  try {
    await clearTerminalHistory()
    historyList.value = []
    ElMessage.success('历史记录已清空')
  } catch (e) {
    ElMessage.error('清空失败')
  }
}

function fillFromHistory(id) {
  const item = historyList.value.find(h => h.id === id)
  if (!item) return
  form.ip = item.ip
  form.port = String(item.port)
  form.username = item.username || ''
  form.password = ''
  // 选中后自动连接
  nextTick(() => handleConnect())
}

// ===== xterm 实例（模块级，跨路由切换存活）=====
let terminal = null
let fitAddon = null
let ws = null
let pingTimer = null
let resizeObserver = null
let pendingBuffer = ''       // 终端被销毁期间缓存 ws 收到的数据
let connectedHost = ''       // 跨路由保留连接信息，显示在已连接 tag

// ===== 初始化 =====
// 从设备管理跳转时，全局捕获 Enter 键触发连接（el-select 会吞掉 keydown 事件）
function _onDeviceJumpEnter(e) {
  if (e.key !== 'Enter') return
  if (connected.value || connecting.value) return
  // 排除全屏终端内按 Enter 的情况
  if (document.activeElement && document.activeElement.closest('.xterm-wrapper')) return
  e.preventDefault()
  e.stopImmediatePropagation()
  handleConnect()
}

onMounted(() => {
  // 从设备管理页面跳转过来时，自动填入连接信息
  if (route.query.ip) form.ip = route.query.ip
  if (route.query.port) form.port = route.query.port
  if (route.query.username) form.username = route.query.username
  // 加载历史连接记录
  loadHistory()
  // 监听 ESC 退出全屏
  window.addEventListener('keydown', onKeydown)
  // 从设备管理跳转时，注册捕获阶段 Enter 监听
  if (hasDeviceId.value) {
    document.addEventListener('keydown', _onDeviceJumpEnter, true)
  }

  // 切页面回来时，如果 ws 还活着就重新挂载终端
  if (ws && ws.readyState === WebSocket.OPEN) {
    connected.value = true
    // 恢复连接标签显示
    if (connectedHost) form.ip = connectedHost
    nextTick(() => {
      createTerminal()
      // 把缓存的数据写回终端
      if (pendingBuffer && terminal) {
        terminal.write(pendingBuffer)
        pendingBuffer = ''
      }
    })
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.removeEventListener('keydown', _onDeviceJumpEnter, true)
  // ⚠️ 只销毁 xterm DOM（必须依附 DOM 元素），不关闭 WebSocket
  // 用户切其他页面再回来时连接保持存活
  destroyTerminal()
})

// ===== 终端管理 =====
function createTerminal() {
  if (terminal) return

  // 确保挂载 DOM 元素存在
  if (!xtermEl.value) {
    console.warn('[SSHTerminal] xtermEl 不存在，无法创建终端')
    return
  }

  try {
    terminal = new XTerm({
      cursorBlink: true,
      cursorStyle: 'bar',
      fontSize: 14,
      fontFamily: "Consolas, 'Courier New', monospace",
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#ffffff',
        selectionBackground: '#264f78',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#ffffff'
      },
      allowProposedApi: true,
      scrollback: 5000,
      tabStopWidth: 8
    })

    fitAddon = new FitAddon()
    terminal.loadAddon(fitAddon)

    terminal.open(xtermEl.value)
    // 等浏览器完成布局后再 fit，否则尺寸计算不准
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (fitAddon) fitAddon.fit()
      })
    })

    // 监听终端输入 → 发送到 WebSocket
    terminal.onData((data) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(data)
      }
    })

    // 监听终端大小变化 → 通知后端
    terminal.onResize(({ cols, rows }) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(`resize:${cols},${rows}`)
      }
    })

    // 监听容器大小变化自动调整终端大小
    resizeObserver = new ResizeObserver(() => {
      if (fitAddon && terminal) {
        try {
          fitAddon.fit()
        } catch (e) { /* 终端已销毁时忽略 */ }
      }
    })
    if (terminalContainer.value) {
      resizeObserver.observe(terminalContainer.value)
    }

    terminal.focus()
  } catch (e) {
    console.error('[SSHTerminal] 终端初始化失败:', e)
    // 初始化失败时清理，防止半初始化状态残留
    destroyTerminal()
    throw e
  }
}

function destroyTerminal() {
  try {
    if (resizeObserver) {
      resizeObserver.disconnect()
      resizeObserver = null
    }
    if (terminal) {
      // 先 dispose（会移除 xterm 创建的 DOM 元素），再置空引用
      const t = terminal
      terminal = null
      fitAddon = null
      t.dispose()
    }
  } catch (e) {
    // 忽略销毁时的错误（DOM 可能已被移除）
    terminal = null
    fitAddon = null
    resizeObserver = null
  }
}

// ===== WebSocket 管理 =====
function connectWebSocket(params) {
  return new Promise((resolve, reject) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/ssh?${params.toString()}`

    ws = new WebSocket(wsUrl)
    pendingBuffer = ''
    let connectionResolved = false

    ws.onopen = () => {
      // 启动心跳
      pingTimer = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send('__PING__')
        }
      }, 30000)
    }

    ws.onmessage = (event) => {
      const data = event.data

      // 检查连接成功标记
      if (data === '__CONNECTED__') {
        connectionResolved = true
        resolve(true)
        return
      }

      // 写给终端（如果终端已创建）
      if (terminal) {
        try {
          terminal.write(data)
        } catch (e) {
          // 终端可能正在被销毁
        }
      } else {
        // 终端还未创建（初始连接中 / 切页面后终端已销毁），统一缓存
        pendingBuffer += data
        // 仅在初始连接阶段检测错误消息（红色 ANSI 开头）
        if (!connectionResolved && pendingBuffer.includes('\x1b[31m')) {
          const cleanMsg = pendingBuffer.replace(/\x1b\[\d+m/g, '').trim()
          if (cleanMsg) {
            reject(new Error(cleanMsg))
            return
          }
        }
      }
    }

    ws.onerror = () => {
      reject(new Error('WebSocket连接错误'))
    }

    ws.onclose = () => {
      stopPing()
      // 还没连上就关了 → 说明连接失败
      if (!connected.value) {
        reject(new Error('连接已关闭（可能是认证失败或网络不通）'))
        return
      }
      // 断连时写提示到终端（如果终端存在）
      if (terminal) {
        try {
          terminal.write('\r\n\x1b[33m连接已断开\x1b[0m\r\n')
        } catch (e) { /* 忽略 */ }
      }
      // 清理状态
      connected.value = false
      connectedHost = ''
      pendingBuffer = ''
      ElMessage.info('连接已断开')
    }

    // 超时处理
    setTimeout(() => {
      if (!connected.value && ws && ws.readyState !== WebSocket.OPEN) {
        reject(new Error('连接超时'))
      }
    }, 15000)
  })
}

function disconnectWebSocket() {
  stopPing()
  if (ws) {
    ws.close()
    ws = null
  }
  connected.value = false
  connectedHost = ''
  pendingBuffer = ''
  selectedHistory.value = null
}

function stopPing() {
  if (pingTimer) {
    clearInterval(pingTimer)
    pingTimer = null
  }
}

// ===== 连接处理 =====
const handleConnect = async () => {
  // 防止重复触发（capture 阶段全局 Enter + bubble 阶段 form submit 可能同时触发）
  if (connecting.value || connected.value) return

  if (!form.ip) {
    ElMessage.warning('请输入主机IP地址')
    return
  }
  if (!form.username) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!hasDeviceId.value && !form.password) {
    ElMessage.warning('请输入密码')
    return
  }

  connecting.value = true
  currentEncoding.value = form.encoding

  try {
    destroyTerminal()
    disconnectWebSocket()

    // 如果用 deviceId 跳转过来，通过 device_id 连接（后端自动解密密码）
    const deviceId = route.query.deviceId
    const params = new URLSearchParams()
    if (deviceId) {
      params.set('device_id', deviceId)
    } else {
      params.set('ip', form.ip)
      params.set('port', form.port)
      params.set('username', form.username)
      params.set('password', form.password)
    }
    params.set('encoding', form.encoding)

    await connectWebSocket(params)
    await nextTick()
    createTerminal()

    connected.value = true
    connectedHost = form.ip
    currentEncoding.value = form.encoding
    ElMessage.success('连接成功')

    // 手动输入连接的才保存历史（从设备管理跳转的不记）
    if (!deviceId) {
      const protocol = String(form.port) === '23' ? 'telnet' : 'ssh'
      saveTerminalHistory(form.ip, form.port, form.username, protocol)
        .then(() => loadHistory())
        .catch(() => {})
    }
  } catch (error) {
    console.error('[SSHTerminal] 连接失败:', error)
    ElMessage.error(error.message || '连接失败')
    destroyTerminal()
    disconnectWebSocket()
  } finally {
    connecting.value = false
  }
}

// 断开连接
const handleDisconnect = () => {
  destroyTerminal()
  disconnectWebSocket()
  ElMessage.info('已断开连接')
}
</script>

<style scoped>
.page-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  overflow: hidden;
}

.config-card {
  flex-shrink: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.connect-form {
  margin: 0;
}

.terminal-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  transition: none; /* 全屏切换不用过渡，保持流畅 */
}

/* 全屏模式：终端卡片撑满整个视口 */
.terminal-card--fullscreen {
  position: fixed !important;
  inset: 0 !important;
  z-index: 9999 !important;
  border-radius: 0 !important;
  margin: 0 !important;
}

.terminal-card--fullscreen :deep(.el-card__header) {
  display: none;
}

.terminal-card :deep(.el-card__body) {
  flex: 1;
  padding: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.terminal-container {
  flex: 1;
  background-color: #1e1e1e;
  position: relative;
  min-height: 0;
}

.terminal-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  z-index: 1;
}

.placeholder-logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.placeholder-title {
  font-size: 18px;
  font-weight: 600;
  color: #409EFF;
}

.placeholder-text {
  margin-top: 16px;
  font-size: 14px;
}

/* ===== 全屏切换按钮 ===== */
.fullscreen-toggle {
  position: absolute;
  top: 5px;
  right: 5px;
  z-index: 10;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.45);
  color: rgba(255, 255, 255, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  backdrop-filter: blur(4px);
  transition: background 0.2s, color 0.2s;
}

.fullscreen-toggle:hover {
  background: rgba(0, 0, 0, 0.65);
  color: #fff;
}

.fullscreen-toggle.is-fullscreen {
  top: 5px;
  right: 5px;
  background: rgba(0, 0, 0, 0.55);
}

.fullscreen-toggle.is-fullscreen:hover {
  background: rgba(0, 0, 0, 0.75);
}

/* 按钮淡入动画 */
.fade-zoom-enter-active {
  transition: all 0.18s ease-out;
}
.fade-zoom-leave-active {
  transition: all 0.12s ease-in;
}
.fade-zoom-enter-from {
  opacity: 0;
  transform: scale(0.6);
}
.fade-zoom-leave-to {
  opacity: 0;
  transform: scale(0.6);
}

.xterm-wrapper {
  position: absolute;
  inset: 0;
}

/* xterm 通过 FitAddon 自适应，不要写死宽高 */
.xterm-wrapper :deep(.xterm) {
  padding: 4px 0 0 8px;
}

.xterm-wrapper :deep(.xterm-viewport) {
  width: 100% !important;
}

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

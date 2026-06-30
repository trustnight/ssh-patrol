import { ref, watch } from 'vue'

const STORAGE_KEY = 'patrol-assistant-settings'

// 全局单例设置
const desensitize = ref(false)
const theme = ref('light')

// 从 localStorage 恢复
function loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const data = JSON.parse(raw)
      desensitize.value = data.desensitize || false
      theme.value = data.theme || 'light'
    }
  } catch (e) {
    // ignore
  }
}

// 持久化
function saveSettings() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    desensitize: desensitize.value,
    theme: theme.value
  }))
}

// 监听变化自动保存
watch([desensitize, theme], saveSettings, { deep: true })

// 应用主题
function applyTheme(t) {
  const root = document.documentElement
  root.classList.remove('dark')
  if (t === 'dark') {
    root.classList.add('dark')
  } else if (t === 'system') {
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      root.classList.add('dark')
    }
  }
}

// 主题变化时应用
watch(theme, applyTheme, { immediate: true })

// 监听系统主题变化（仅在 system 模式下）
const systemDarkQuery = window.matchMedia('(prefers-color-scheme: dark)')
systemDarkQuery.addEventListener('change', () => {
  if (theme.value === 'system') {
    applyTheme('system')
  }
})

// 掩码工具函数
function maskText(text, type = 'default') {
  if (!text) return ''
  if (!desensitize.value) return text

  switch (type) {
    case 'ip': {
      // IP: 192.168.1.1 → 192.*.*.*
      const parts = text.split('.')
      if (parts.length === 4) {
        return parts[0] + '.*.*.*'
      }
      return maskText(text, 'default')
    }
    case 'username': {
      // 用户名: admin → a****
      if (text.length <= 1) return '*'
      return text[0] + '*'.repeat(Math.min(text.length - 1, 6))
    }
    case 'password': {
      return '******'
    }
    case 'url': {
      // URL: https://192.168.1.1:8443 → https://**********
      return text.replace(/:\/\/.*$/, '://********')
    }
    default: {
      // 默认掩码：保留首字符
      if (text.length <= 1) return '*'
      return text[0] + '*'.repeat(Math.min(text.length - 1, 8))
    }
  }
}

// 初始化加载
loadSettings()

export function useSettings() {
  return {
    desensitize,
    theme,
    maskText,
    toggleDesensitize() {
      desensitize.value = !desensitize.value
    },
    setTheme(t) {
      theme.value = t
    }
  }
}

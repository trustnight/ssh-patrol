import request from '@/utils/request'

// 获取模板列表
export function getTemplateList() {
  return request({
    url: '/templates/list',
    method: 'get'
  })
}

// 获取模板支持的厂商列表
export function getTemplateManufacturers(templateName) {
  return request({
    url: '/templates/manufacturers',
    method: 'get',
    params: { template_name: templateName }
  })
}

// 获取模板命令列表
export function getTemplateCommands(templateName, manufacturer, deviceType = '') {
  return request({
    url: '/templates/commands',
    method: 'get',
    params: {
      template_name: templateName,
      manufacturer: manufacturer,
      device_type: deviceType || ''
    }
  })
}

// 保存自定义模板
export function saveCustomTemplate(templateName, manufacturer, commands, deviceType = '') {
  return request({
    url: '/templates/custom/save',
    method: 'post',
    data: {
      template_name: templateName,
      manufacturer: manufacturer,
      device_type: deviceType || '',
      commands: commands
    }
  })
}

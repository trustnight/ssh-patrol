import request from '@/utils/request'

export function getTerminalHistory() {
  return request({ url: '/terminal/history', method: 'get' })
}

export function saveTerminalHistory(ip, port, username, protocol) {
  return request({
    url: '/terminal/history',
    method: 'post',
    params: { ip, port, username, protocol }
  })
}

export function clearTerminalHistory() {
  return request({ url: '/terminal/history', method: 'delete' })
}

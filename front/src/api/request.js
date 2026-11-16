import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/',
  timeout: 15000,
})

// 请求：携带操作人（后端认证预留）
request.interceptors.request.use((cfg) => {
  cfg.headers['X-Operator'] = localStorage.getItem('operator') || 'system'
  return cfg
})

// 响应：统一解包后端 Resp { code, message, data }
request.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body.data
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message))
    }
    return body
  },
  (err) => {
    const msg = err.response?.data?.message || err.message || '网络错误'
    ElMessage.error(msg)
    return Promise.reject(err)
  },
)

export default request

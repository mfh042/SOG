import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const request = axios.create({
  baseURL: '/',
  timeout: 15000,
})

request.interceptors.request.use((cfg) => {
  try {
    const auth = useAuthStore()
    if (auth.token) {
      cfg.headers['Authorization'] = `Bearer ${auth.token}`
    }
  } catch (e) {
    /* Pinia not yet initialized */
  }
  const op = localStorage.getItem('operator') || 'system'
  cfg.headers['X-Operator'] = op
  return cfg
})

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
    if (err.response?.status === 401) {
      try {
        const auth = useAuthStore()
        auth.logout()
      } catch (e) {}
      if (!location.hash.includes('/login')) {
        ElMessage.warning('登录已过期，请重新登录')
        router.push('/login')
      }
    }
    const msg = err.response?.data?.message || err.message || '网络错误'
    ElMessage.error(msg)
    return Promise.reject(err)
  },
)

export default request
import axios from 'axios'
import { ElMessage } from 'element-plus'

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const apiPrefix = import.meta.env.VITE_API_PREFIX ?? '/api'

const normalizedBaseUrl = rawBaseUrl.replace(/\/$/, '')
const normalizedPrefix = apiPrefix
  ? apiPrefix.startsWith('/')
    ? apiPrefix
    : `/${apiPrefix}`
  : ''

const request = axios.create({
  baseURL: `${normalizedBaseUrl}${normalizedPrefix}`,
  timeout: 30000,
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default request


import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '/system',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('jwt_token')
  if (token) {
    // Axios v1 uses AxiosHeaders internally, but keep a safe fallback.
    if (typeof (config.headers as any)?.set === 'function') {
      ;(config.headers as any).set('Authorization', `Bearer ${token}`)
    } else {
      ;(config.headers as any).Authorization = `Bearer ${token}`
    }
  }
  return config
})

// Handle errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('jwt_token')
      localStorage.removeItem('user')
      window.location.assign('/login')
    }
    return Promise.reject(error)
  },
)

export default api



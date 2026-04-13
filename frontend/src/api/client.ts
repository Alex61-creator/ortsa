/**
 * Axios baseURL = `/api/v1` (или VITE_API_URL). Пути в модулях api/* — относительно base.
 * Коллекции (роуты FastAPI с `@router.get("/")` / `post("/")` под prefix) запрашиваем **со слэшем**
 * (`/orders/`, `/tariffs/`, `/natal-data/`), чтобы совпадать с каноническим URL и не ловить 307.
 * Ресурс по id — без слэша в конце (`/orders/123`).
 */
import axios, { type AxiosError } from 'axios'
import { message } from 'antd'
import { useAuthStore } from '@/stores/authStore'

export function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_URL ?? '/api/v1'
}

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 60_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error: AxiosError<{ detail?: string | { msg: string }[] }>) => {
    const status = error.response?.status
    if (status === 401) {
      useAuthStore.getState().logout()
      const path = window.location.pathname
      if (path !== '/' && !path.startsWith('/auth/callback')) {
        window.location.assign('/')
      }
    } else if (status === 429) {
      message.warning('Слишком много запросов. Подождите немного.')
    } else if (status && status >= 500) {
      message.error('Ошибка сервера. Попробуйте позже.')
    } else {
      const d = error.response?.data?.detail
      const text =
        typeof d === 'string'
          ? d
          : Array.isArray(d)
            ? d.map((x) => x.msg).join(', ')
            : error.message
      if (text) message.error(text)
    }
    return Promise.reject(error)
  }
)

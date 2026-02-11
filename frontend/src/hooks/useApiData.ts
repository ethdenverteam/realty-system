/**
 * Переиспользуемый хук для загрузки данных через API
 * Цель: единый паттерн загрузки данных с обработкой ошибок и состояния загрузки
 */
import { useState, useEffect } from 'react'
import api from '../utils/api'
import { getErrorMessage, logError } from '../utils/errorHandler'
import type { ApiErrorResponse } from '../types/models'

interface UseApiDataOptions<T> {
  /**
   * URL для запроса данных
   */
  url: string
  /**
   * Параметры запроса (query params)
   */
  params?: Record<string, unknown>
  /**
   * Зависимости для перезагрузки данных (как в useEffect)
   */
  deps?: unknown[]
  /**
   * Сообщение об ошибке по умолчанию
   */
  defaultErrorMessage?: string
  /**
   * Контекст для логирования ошибок
   */
  errorContext?: string
  /**
   * Автоматически загружать данные при монтировании (по умолчанию true)
   */
  autoLoad?: boolean
}

interface UseApiDataResult<T> {
  /**
   * Загруженные данные
   */
  data: T | null
  /**
   * Состояние загрузки
   */
  loading: boolean
  /**
   * Сообщение об ошибке (если есть)
   */
  error: string
  /**
   * Функция для ручной перезагрузки данных
   */
  reload: () => Promise<void>
}

/**
 * Хук для загрузки данных через API
 * Логика: автоматически обрабатывает состояние загрузки, ошибки и перезагрузку данных
 */
export function useApiData<T>(options: UseApiDataOptions<T>): UseApiDataResult<T> {
  const { url, params, deps = [], defaultErrorMessage = 'Ошибка загрузки данных', errorContext = '', autoLoad = true } = options

  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState<boolean>(autoLoad)
  const [error, setError] = useState<string>('')

  const loadData = async (): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const response = await api.get<T>(url, { params })
      setData(response.data)
    } catch (err: unknown) {
      const message = getErrorMessage(err, defaultErrorMessage)
      setError(message)
      logError(err, errorContext || `Loading data from ${url}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (autoLoad) {
      void loadData()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, ...deps])

  return {
    data,
    loading,
    error,
    reload: loadData,
  }
}


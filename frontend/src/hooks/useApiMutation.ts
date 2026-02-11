/**
 * Переиспользуемый хук для мутаций (создание, обновление, удаление) через API
 * Цель: единый паттерн для операций изменения данных с обработкой ошибок
 */
import { useState } from 'react'
import api from '../utils/api'
import { getErrorMessage, logError } from '../utils/errorHandler'
import type { ApiErrorResponse } from '../types/models'

interface UseApiMutationOptions<TRequest, TResponse> {
  /**
   * URL для запроса
   */
  url: string
  /**
   * Метод HTTP (по умолчанию POST)
   */
  method?: 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  /**
   * Сообщение об ошибке по умолчанию
   */
  defaultErrorMessage?: string
  /**
   * Контекст для логирования ошибок
   */
  errorContext?: string
  /**
   * Callback при успешном выполнении
   */
  onSuccess?: (data: TResponse) => void
  /**
   * Callback при ошибке
   */
  onError?: (error: string) => void
}

interface UseApiMutationResult<TRequest, TResponse> {
  /**
   * Функция для выполнения мутации
   */
  mutate: (data: TRequest) => Promise<TResponse | null>
  /**
   * Состояние загрузки
   */
  loading: boolean
  /**
   * Сообщение об ошибке (если есть)
   */
  error: string
  /**
   * Очистка ошибки
   */
  clearError: () => void
}

/**
 * Хук для выполнения мутаций через API
 * Логика: обрабатывает состояние загрузки, ошибки и успешные операции
 */
export function useApiMutation<TRequest, TResponse = unknown>(
  options: UseApiMutationOptions<TRequest, TResponse>
): UseApiMutationResult<TRequest, TResponse> {
  const {
    url,
    method = 'POST',
    defaultErrorMessage = 'Ошибка выполнения операции',
    errorContext = '',
    onSuccess,
    onError,
  } = options

  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string>('')

  const mutate = async (data: TRequest): Promise<TResponse | null> => {
    try {
      setLoading(true)
      setError('')

      let response
      switch (method) {
        case 'POST':
          response = await api.post<TResponse>(url, data)
          break
        case 'PUT':
          response = await api.put<TResponse>(url, data)
          break
        case 'PATCH':
          response = await api.patch<TResponse>(url, data)
          break
        case 'DELETE':
          response = await api.delete<TResponse>(url)
          break
        default:
          throw new Error(`Unsupported method: ${method}`)
      }

      if (onSuccess) {
        onSuccess(response.data)
      }

      return response.data
    } catch (err: unknown) {
      const message = getErrorMessage(err, defaultErrorMessage)
      setError(message)
      logError(err, errorContext || `${method} ${url}`)
      if (onError) {
        onError(message)
      }
      return null
    } finally {
      setLoading(false)
    }
  }

  const clearError = (): void => {
    setError('')
  }

  return {
    mutate,
    loading,
    error,
    clearError,
  }
}


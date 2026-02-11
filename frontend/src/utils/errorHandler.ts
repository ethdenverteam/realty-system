/**
 * Утилиты для обработки ошибок API
 * Цель: единый способ обработки ошибок во всём приложении
 */
import axios, { AxiosError } from 'axios'
import type { ApiErrorResponse } from '../types/models'

/**
 * Извлекает сообщение об ошибке из ответа API или объекта ошибки
 * Логика: проверяет структуру ответа, возвращает понятное сообщение
 */
export function getErrorMessage(error: unknown, defaultMessage = 'Произошла ошибка'): string {
  if (axios.isAxiosError<ApiErrorResponse>(error)) {
    return error.response?.data?.error || error.response?.data?.message || error.message || defaultMessage
  }
  if (error instanceof Error) {
    return error.message || defaultMessage
  }
  return defaultMessage
}

/**
 * Логирует ошибку в консоль для отладки
 * Логика: выводит полную информацию об ошибке в консоль
 */
export function logError(error: unknown, context = ''): void {
  if (axios.isAxiosError<ApiErrorResponse>(error)) {
    console.error(`${context ? `${context}: ` : ''}`, error.response?.data || error.message)
  } else {
    console.error(`${context ? `${context}: ` : ''}`, error)
  }
}

/**
 * Проверяет, является ли ошибка ошибкой авторизации (401)
 * Логика: используется для автоматического редиректа на страницу входа
 */
export function isAuthError(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 401
}


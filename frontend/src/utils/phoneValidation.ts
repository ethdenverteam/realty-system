import { PHONE_PATTERN, PHONE_ERROR_MESSAGE } from './constants'

export interface PhoneValidationResult {
  isValid: boolean
  error?: string
}

/**
 * Валидирует номер телефона
 */
export function validatePhone(phone: string | null | undefined): PhoneValidationResult {
  if (!phone || !phone.trim()) {
    return { isValid: true } // Пустой телефон допустим
  }

  if (!PHONE_PATTERN.test(phone.trim())) {
    return { isValid: false, error: PHONE_ERROR_MESSAGE }
  }

  return { isValid: true }
}

/**
 * Валидирует оба номера телефона (основной и дополнительный)
 */
export function validatePhones(phone1: string | null | undefined, phone2: string | null | undefined): PhoneValidationResult {
  const result1 = validatePhone(phone1)
  if (!result1.isValid) {
    return result1
  }

  const result2 = validatePhone(phone2)
  if (!result2.isValid) {
    return { isValid: false, error: 'Второй номер телефона должен быть в формате 89693386969' }
  }

  return { isValid: true }
}


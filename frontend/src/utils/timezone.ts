/**
 * Глобальная переменная часового пояса системы
 * Можно менять в будущем, сейчас установлена МСК (GMT+3)
 */
export const SYSTEM_TIMEZONE = 'Europe/Moscow' // МСК (GMT+3)
export const SYSTEM_TIMEZONE_NAME = 'МСК'

/**
 * Время работы автопубликации (по МСК)
 */
export const AUTOPUBLISH_START_HOUR = 8  // Начало работы: 8:00 МСК
export const AUTOPUBLISH_END_HOUR = 22   // Конец работы: 22:00 МСК

/**
 * Форматировать дату/время в системном часовом поясе (МСК)
 */
export function formatSystemTime(iso?: string | null): string {
  if (!iso) return '-'
  const date = new Date(iso)
  try {
    return date.toLocaleString('ru-RU', { timeZone: SYSTEM_TIMEZONE })
  } catch {
    return date.toLocaleString('ru-RU')
  }
}

/**
 * Форматировать только дату в системном часовом поясе (МСК)
 */
export function formatSystemDate(iso?: string | null): string {
  if (!iso) return '-'
  const date = new Date(iso)
  try {
    return date.toLocaleDateString('ru-RU', { timeZone: SYSTEM_TIMEZONE })
  } catch {
    return date.toLocaleDateString('ru-RU')
  }
}

/**
 * Получить текущее время в системном часовом поясе (МСК)
 */
export function getCurrentSystemTime(): Date {
  const now = new Date()
  // Конвертируем в системный часовой пояс
  try {
    const formatter = new Intl.DateTimeFormat('ru-RU', {
      timeZone: SYSTEM_TIMEZONE,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
    const parts = formatter.formatToParts(now)
    const year = parseInt(parts.find(p => p.type === 'year')?.value || '0')
    const month = parseInt(parts.find(p => p.type === 'month')?.value || '0') - 1
    const day = parseInt(parts.find(p => p.type === 'day')?.value || '0')
    const hour = parseInt(parts.find(p => p.type === 'hour')?.value || '0')
    const minute = parseInt(parts.find(p => p.type === 'minute')?.value || '0')
    const second = parseInt(parts.find(p => p.type === 'second')?.value || '0')
    return new Date(year, month, day, hour, minute, second)
  } catch {
    return now
  }
}

/**
 * Проверить, находится ли текущее время в разрешенных часах для публикации (8:00-22:00 МСК)
 */
export function isWithinPublishHours(date?: Date): boolean {
  const checkDate = date || getCurrentSystemTime()
  return AUTOPUBLISH_START_HOUR <= checkDate.getHours() && checkDate.getHours() < AUTOPUBLISH_END_HOUR
}


/**
 * Форматирует время в часовом поясе Москвы
 */
export function formatMoscowTime(iso?: string | null): string {
  if (!iso) return '-'
  const date = new Date(iso)
  try {
    return date.toLocaleString('ru-RU', { timeZone: 'Europe/Moscow' })
  } catch {
    // Fallback, если нет поддержки timeZone
    return date.toLocaleString('ru-RU')
  }
}

/**
 * Форматирует категорию чата для отображения
 */
export function formatCategory(category?: string): string {
  if (!category) return 'Без категории'
  if (category.startsWith('rooms_')) {
    return `Комнаты: ${category.replace('rooms_', '')}`
  }
  if (category.startsWith('district_')) {
    return `Район: ${category.replace('district_', '')}`
  }
  if (category.startsWith('price_')) {
    const parts = category.replace('price_', '').split('_')
    if (parts.length === 2) {
      return `Цена: ${parts[0]}-${parts[1]} тыс.`
    }
  }
  return category
}


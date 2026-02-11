/**
 * Общие константы для всего приложения
 * Цель: один источник истины для всех перечислений и констант
 */

// Типы комнат (единый источник)
export const ROOMS_TYPES = [
  'Студия',
  '1к',
  '2к',
  '3к',
  '4+к',
  'Дом',
  'евро1к',
  'евро2к',
  'евро3к',
] as const

export type RoomsType = typeof ROOMS_TYPES[number]

// Типы ремонта (единый источник)
export const RENOVATION_TYPES = [
  'Черновая',
  'ПЧО',
  'Ремонт требует освежения',
  'Хороший ремонт',
  'Инстаграмный',
] as const

export type RenovationType = typeof RENOVATION_TYPES[number]

// Статусы объектов (единый источник)
export const OBJECT_STATUSES = [
  'черновик',
  'опубликовано',
  'запланировано',
  'архив',
] as const

export type ObjectStatus = typeof OBJECT_STATUSES[number]

// Опции сортировки (единый источник)
export interface SortOption {
  value: string
  label: string
  sortBy: string
  sortOrder: 'asc' | 'desc'
}

export const OBJECT_SORT_OPTIONS: SortOption[] = [
  { value: 'creation_date_desc', label: 'Новые сначала', sortBy: 'creation_date', sortOrder: 'desc' },
  { value: 'creation_date_asc', label: 'Старые сначала', sortBy: 'creation_date', sortOrder: 'asc' },
  { value: 'price_desc', label: 'Цена: дороже', sortBy: 'price', sortOrder: 'desc' },
  { value: 'price_asc', label: 'Цена: дешевле', sortBy: 'price', sortOrder: 'asc' },
]

// Валидация телефона
export const PHONE_PATTERN = /^8\d{10}$/
export const PHONE_ERROR_MESSAGE = 'Номер телефона должен быть в формате 89693386969 (11 цифр, начинается с 8)'


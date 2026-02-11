/**
 * Переиспользуемый компонент для фильтров-селектов
 * Цель: единый стиль и поведение для всех фильтров в приложении
 */
import './FilterSelect.css'

interface FilterSelectOption {
  value: string
  label: string
}

interface FilterSelectProps {
  /**
   * Текущее значение
   */
  value: string
  /**
   * Обработчик изменения значения
   */
  onChange: (value: string) => void
  /**
   * Опции для выбора
   */
  options: FilterSelectOption[]
  /**
   * Placeholder (первая опция с пустым значением)
   */
  placeholder?: string
  /**
   * Дополнительные CSS классы
   */
  className?: string
  /**
   * Размер (sm для маленьких, по умолчанию обычный)
   */
  size?: 'sm' | 'md'
}

/**
 * Компонент фильтра-селекта
 * Логика: единый стиль для всех фильтров, поддержка placeholder и размеров
 */
export function FilterSelect({
  value,
  onChange,
  options,
  placeholder = 'Все',
  className = '',
  size = 'md',
}: FilterSelectProps): JSX.Element {
  return (
    <select
      className={`filter-select form-input ${size === 'sm' ? 'form-input-sm' : ''} ${className}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}


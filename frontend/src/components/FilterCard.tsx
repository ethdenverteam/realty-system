/**
 * Переиспользуемый компонент карточки фильтров
 * Цель: единый стиль для всех блоков фильтров в приложении
 */
import { GlassCard } from './GlassCard'
import './FilterCard.css'

interface FilterCardProps {
  /**
   * Заголовок карточки фильтров
   */
  title?: string
  /**
   * Дополнительные действия в заголовке (кнопки и т.д.)
   */
  headerActions?: React.ReactNode
  /**
   * Дочерние элементы (фильтры)
   */
  children: React.ReactNode
  /**
   * Дополнительные CSS классы
   */
  className?: string
}

/**
 * Карточка фильтров
 * Логика: единый стиль для всех блоков фильтров, поддержка заголовка и действий
 */
export function FilterCard({ title = 'Фильтры', headerActions, children, className = '' }: FilterCardProps): JSX.Element {
  return (
    <GlassCard className={`filter-card ${className}`}>
      {(title || headerActions) && (
        <div className="filter-card-header">
          {title && <h2 className="filter-card-title">{title}</h2>}
          {headerActions && <div className="filter-card-actions">{headerActions}</div>}
        </div>
      )}
      <div className="filter-card-content">{children}</div>
    </GlassCard>
  )
}


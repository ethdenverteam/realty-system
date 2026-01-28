import { useRef } from 'react'
import type { RealtyObjectListItem } from '../types/models'
import './ObjectCard.css'

interface ObjectCardProps {
  object: RealtyObjectListItem
  onClick?: () => void
}

/**
 * Типизированная карточка объекта с эффектом жидкого стекла
 * Автоматически добавляет glow эффект при клике
 */
export function ObjectCard({ object, onClick }: ObjectCardProps): JSX.Element {
  const cardRef = useRef<HTMLDivElement>(null)

  const handleClick = (): void => {
    // Добавляем glow эффект
    const card = cardRef.current
    if (card) {
      card.classList.add('glow-active')
      setTimeout(() => {
        card.classList.remove('glow-active')
      }, 400)
    }
    onClick?.()
  }

  return (
    <div ref={cardRef} className="object-card glass-object-card compact" onClick={handleClick}>
      <div className="object-details-compact">
        {object.rooms_type && (
          <div className="object-detail-item">
            {object.rooms_type}
          </div>
        )}
        {object.price > 0 && (
          <div className="object-detail-item">
            {object.price} тыс. руб.
          </div>
        )}
        {object.area && (
          <div className="object-detail-item">
            {object.area} м²
          </div>
        )}
        {(object.districts_json?.length || 0) > 0 && (
          <div className="object-detail-item">
            {(object.districts_json || []).join(', ')}
          </div>
        )}
      </div>
    </div>
  )
}


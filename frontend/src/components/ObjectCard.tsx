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
    <div ref={cardRef} className="object-card glass-object-card" onClick={handleClick}>
      <div className="object-header">
        <h3 className="object-id">{object.object_id}</h3>
        <span
          className={`badge badge-${
            object.status === 'опубликовано'
              ? 'success'
              : object.status === 'черновик'
                ? 'warning'
                : 'secondary'
          }`}
        >
          {object.status}
        </span>
      </div>
      <div className="object-details">
        {object.rooms_type && (
          <div>
            <strong>Тип:</strong> {object.rooms_type}
          </div>
        )}
        {object.price > 0 && (
          <div>
            <strong>Цена:</strong> {object.price} тыс. руб.
          </div>
        )}
        {object.area && (
          <div>
            <strong>Площадь:</strong> {object.area} м²
          </div>
        )}
        {object.floor && (
          <div>
            <strong>Этаж:</strong> {object.floor}
          </div>
        )}
        {(object.districts_json?.length || 0) > 0 && (
          <div>
            <strong>Районы:</strong> {(object.districts_json || []).join(', ')}
          </div>
        )}
      </div>
      {object.comment && (
        <div className="object-comment">
          {object.comment.substring(0, 100)}
          {object.comment.length > 100 ? '...' : ''}
        </div>
      )}
    </div>
  )
}


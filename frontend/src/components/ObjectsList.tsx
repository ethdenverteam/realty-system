import type { RealtyObjectListItem } from '../types/models'
import { ObjectCard } from './ObjectCard'
import './ObjectsList.css'

interface ObjectsListProps {
  objects: RealtyObjectListItem[]
  onObjectClick?: (object: RealtyObjectListItem) => void
}

/**
 * Типизированный список объектов
 */
export function ObjectsList({ objects, onObjectClick }: ObjectsListProps): JSX.Element {
  return (
    <div className="objects-list">
      {objects.map((obj) => (
        <ObjectCard
          key={obj.object_id}
          object={obj}
          onClick={() => onObjectClick?.(obj)}
        />
      ))}
    </div>
  )
}


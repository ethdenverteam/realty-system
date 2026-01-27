import { useNavigate } from 'react-router-dom'
import { observer } from 'mobx-react-lite'
import { GlassButton } from './GlassButton'
import { uiStore } from '../stores/uiStore'
import type { RealtyObjectListItem } from '../types/models'
import './GlassMenuButton.css'

interface GlassObjectsButtonProps {
  objects: RealtyObjectListItem[]
}

/**
 * Стеклянная кнопка "объекты" с списком объектов из БД.
 * Всегда показывает текст "объекты", а при клике открывает select с объектами пользователя.
 * Состояние хранится в MobX store.
 */
function GlassObjectsButton({ objects }: GlassObjectsButtonProps): JSX.Element {
  const navigate = useNavigate()

  const handleObjectSelect = (value: string): void => {
    if (value) {
      uiStore.setSelectedObjectId(value)
      navigate(`/user/dashboard/objects/${value}`)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  return (
    <GlassButton className="glass-select-button">
      <span>объекты</span>
      <select
        className="glass-select-native"
        value={uiStore.selectedObjectId || ''}
        onChange={(e) => handleObjectSelect(e.target.value)}
      >
        <option value="">Выберите объект...</option>
        {objects.map((obj) => {
          const label = obj.rooms_type && obj.price
            ? `${obj.rooms_type} - ${obj.price} тыс. руб.`
            : `Объект #${obj.object_id}`
          return (
            <option key={obj.object_id} value={String(obj.object_id)}>
              {label}
            </option>
          )
        })}
      </select>
    </GlassButton>
  )
}

export default observer(GlassObjectsButton)


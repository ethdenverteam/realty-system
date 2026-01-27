import { useNavigate } from 'react-router-dom'
import { observer } from 'mobx-react-lite'
import { useRef, useEffect } from 'react'
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
 * 
 * Исправление для iOS: программное открытие select при клике на обёртку
 */
function GlassObjectsButton({ objects }: GlassObjectsButtonProps): JSX.Element {
  const navigate = useNavigate()
  const selectRef = useRef<HTMLSelectElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)

  const handleObjectSelect = (value: string): void => {
    if (value) {
      uiStore.setSelectedObjectId(value)
      navigate(`/user/dashboard/objects/${value}`)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  // Исправление для iOS: перехватываем клики на обёртке и программно открываем select
  useEffect(() => {
    const wrapper = wrapperRef.current
    const select = selectRef.current
    if (!wrapper || !select) return

    const handleClick = (e: MouseEvent | TouchEvent): void => {
      // Если клик не на самом select, открываем его программно
      if (e.target !== select && select) {
        e.preventDefault()
        e.stopPropagation()
        // Для iOS: используем setTimeout чтобы обойти задержку браузера
        setTimeout(() => {
          select.focus()
          select.click()
        }, 0)
      }
    }

    wrapper.addEventListener('click', handleClick, { passive: false })
    wrapper.addEventListener('touchend', handleClick, { passive: false })

    return () => {
      wrapper.removeEventListener('click', handleClick)
      wrapper.removeEventListener('touchend', handleClick)
    }
  }, [])

  return (
    <div ref={wrapperRef} className="glass-select-button-wrapper">
      <GlassButton className="glass-select-button">
        объекты
      </GlassButton>
      <select
        ref={selectRef}
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
    </div>
  )
}

export default observer(GlassObjectsButton)


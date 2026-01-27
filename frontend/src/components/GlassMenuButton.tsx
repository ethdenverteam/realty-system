import { useNavigate } from 'react-router-dom'
import { observer } from 'mobx-react-lite'
import { useRef, useEffect } from 'react'
import { GlassButton } from './GlassButton'
import { uiStore } from '../stores/uiStore'
import { createNavigationOptions } from './BottomNavDropdown'
import './GlassMenuButton.css'

/**
 * Стеклянная кнопка "меню" с навигацией внутри.
 * Всегда показывает текст "меню", а при клике открывает select с опциями навигации.
 * Состояние хранится в MobX store.
 * 
 * Исправление для iOS: программное открытие select при клике на обёртку
 */
function GlassMenuButton(): JSX.Element {
  const navigate = useNavigate()
  const navOptions = createNavigationOptions()
  const selectRef = useRef<HTMLSelectElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)

  const handleMenuSelect = (value: string): void => {
    uiStore.setMenuChoice(value)
    if (value) {
      navigate(value)
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
        меню
      </GlassButton>
      <select
        ref={selectRef}
        className="glass-select-native"
        value={uiStore.menuChoice}
        onChange={(e) => handleMenuSelect(e.target.value)}
      >
        <option value="">Выберите...</option>
        {navOptions.map((opt) => (
          <option key={String(opt.value)} value={String(opt.value)}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export default observer(GlassMenuButton)


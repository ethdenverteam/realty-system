import { useNavigate } from 'react-router-dom'
import { observer } from 'mobx-react-lite'
import { useRef, useEffect } from 'react'
import { GlassButton } from './GlassButton'
import { uiStore } from '../stores/uiStore'
import { createNavigationOptions } from './BottomNavDropdown'
import { useAuth } from '../contexts/AuthContext'
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
  const { isAdmin } = useAuth()
  const navOptions = createNavigationOptions(isAdmin)
  const selectRef = useRef<HTMLSelectElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

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

    let isProcessing = false
    let lastTouchTime = 0
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0

    const openSelect = (): void => {
      if (isProcessing) return
      
      const now = Date.now()
      // Предотвращаем двойное срабатывание в течение 400ms
      if (now - lastTouchTime < 400) return
      
      isProcessing = true
      lastTouchTime = now

      // Для iOS: используем requestAnimationFrame + setTimeout для надежного открытия
      requestAnimationFrame(() => {
        setTimeout(() => {
          try {
            select.focus()
            // Прямой вызов click() на select
            select.click()
          } catch (err) {
            console.error('Error opening select:', err)
          }
          
          // Сбрасываем флаг через задержку
          setTimeout(() => {
            isProcessing = false
          }, 400)
        }, 50) // Увеличиваем задержку для iOS
      })
    }

    const handleTouchStart = (e: TouchEvent): void => {
      // Проверяем, что тап на обёртке, а не на select
      const target = e.target as Node
      if (target !== select && wrapper.contains(target) && !select.contains(target)) {
        e.preventDefault()
        e.stopPropagation()
        openSelect()
      }
    }

    const handleClick = (e: MouseEvent): void => {
      // На touch-устройствах полностью игнорируем click события
      // чтобы избежать конфликта с touch событиями
      if (isTouchDevice) {
        e.preventDefault()
        e.stopPropagation()
        return
      }
      
      // Для не-touch устройств обрабатываем click
      const target = e.target as Node
      if (target !== select && wrapper.contains(target) && !select.contains(target)) {
        e.preventDefault()
        e.stopPropagation()
        openSelect()
      }
    }

    if (isTouchDevice) {
      // На touch-устройствах используем только touchstart
      wrapper.addEventListener('touchstart', handleTouchStart, { passive: false })
      // Блокируем click события на touch-устройствах
      wrapper.addEventListener('click', handleClick, { passive: false, capture: true })
    } else {
      wrapper.addEventListener('click', handleClick, { passive: false })
    }

    return () => {
      if (isTouchDevice) {
        wrapper.removeEventListener('touchstart', handleTouchStart)
        wrapper.removeEventListener('click', handleClick, { capture: true })
      } else {
        wrapper.removeEventListener('click', handleClick)
      }
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


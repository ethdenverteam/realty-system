import { useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { observer } from 'mobx-react-lite'
import { GlassButton } from './GlassButton'
import { uiStore } from '../stores/uiStore'
import { createNavigationOptions } from './BottomNavDropdown'
import './GlassMenuButton.css'

/**
 * Стеклянная кнопка "меню" с навигацией внутри.
 * Всегда показывает текст "меню", а при клике открывает select с опциями навигации.
 * Состояние хранится в MobX store.
 */
function GlassMenuButton(): JSX.Element {
  const navigate = useNavigate()
  const navOptions = createNavigationOptions()
  const selectRef = useRef<HTMLSelectElement>(null)

  const handleButtonClick = (): void => {
    // Программно открываем select при клике на кнопку
    if (selectRef.current) {
      selectRef.current.focus()
      selectRef.current.click()
    }
  }

  const handleMenuSelect = (value: string): void => {
    uiStore.setMenuChoice(value)
    if (value) {
      navigate(value)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  return (
    <GlassButton className="glass-select-button" onClick={handleButtonClick}>
      меню
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
    </GlassButton>
  )
}

export default observer(GlassMenuButton)


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

  const handleMenuSelect = (value: string): void => {
    uiStore.setMenuChoice(value)
    if (value) {
      navigate(value)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  return (
    <div className="glass-select-button-wrapper">
      <GlassButton className="glass-select-button">
        меню
      </GlassButton>
      <select
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


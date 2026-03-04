import Dropdown, { type DropdownOption } from '../Dropdown'
import { useTheme } from '../../contexts/ThemeContext'

export function ThemeSettings(): JSX.Element {
  const { theme, setTheme, availableThemes } = useTheme()

  return (
    <div className="form-section">
      <h3 className="card-title">Выбор темы</h3>
      <p className="card-description">
        Выберите тему оформления приложения. Изменения применяются сразу.
      </p>
      <div className="form-group">
        <label className="form-label">Тема оформления</label>
        <div className="theme-selector-wrapper">
          <Dropdown
            options={availableThemes.map((t) => ({
              value: t.value,
              label: t.label,
            })) as DropdownOption[]}
            value={theme}
            onChange={(value) => {
              setTheme(value as typeof theme)
            }}
            placeholder="Выберите тему..."
          />
        </div>
        <small className="form-hint">
          Текущая тема: <strong>{availableThemes.find((t) => t.value === theme)?.label}</strong>
        </small>
      </div>
    </div>
  )
}


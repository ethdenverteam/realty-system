interface UserSettings {
  phone: string
  contact_name: string
  default_show_username: boolean
  object_card_display_types?: string[]
  object_list_display_types?: string[]
}

interface DisplaySettingsProps {
  settings: UserSettings
  onChange: (field: keyof UserSettings, value: string | boolean | string[]) => void
}

const objectDisplayFields = [
  { key: 'rooms_type', label: 'Тип комнат' },
  { key: 'price', label: 'Цена' },
  { key: 'area', label: 'Площадь' },
  { key: 'floor', label: 'Этаж' },
  { key: 'districts', label: 'Районы' },
  { key: 'address', label: 'Адрес' },
  { key: 'renovation', label: 'Ремонт' },
  { key: 'comment', label: 'Комментарий' },
]

export function DisplaySettings({ settings, onChange }: DisplaySettingsProps): JSX.Element {
  const handleCardDisplayChange = (fieldKey: string, checked: boolean): void => {
    const current = settings.object_card_display_types || []
    const updated = checked
      ? [...current, fieldKey]
      : current.filter((t) => t !== fieldKey)
    onChange('object_card_display_types', updated)
  }

  const handleListDisplayChange = (fieldKey: string, checked: boolean): void => {
    const current = settings.object_list_display_types || []
    const updated = checked
      ? [...current, fieldKey]
      : current.filter((t) => t !== fieldKey)
    onChange('object_list_display_types', updated)
  }

  return (
    <div className="form-section">
      <h3 className="card-title">Настройки отображения объектов</h3>
      <p className="card-description">
        Выберите поля объекта для отображения в карточке объекта и списке объектов
      </p>

      <div className="form-group">
        <label className="form-label">Поля для карточки объекта (короткое описание)</label>
        <div className="checkbox-group">
          {objectDisplayFields.map((field) => (
            <label key={field.key} className="checkbox-label">
              <input
                type="checkbox"
                checked={settings.object_card_display_types?.includes(field.key) || false}
                onChange={(e) => handleCardDisplayChange(field.key, e.target.checked)}
              />
              <span>{field.label}</span>
            </label>
          ))}
        </div>
        <small className="form-hint">
          Если ничего не выбрано, будут показываться все поля
        </small>
      </div>

      <div className="form-group">
        <label className="form-label">Поля для списка объектов (одна строка)</label>
        <div className="checkbox-group">
          {objectDisplayFields.map((field) => (
            <label key={field.key} className="checkbox-label">
              <input
                type="checkbox"
                checked={settings.object_list_display_types?.includes(field.key) || false}
                onChange={(e) => handleListDisplayChange(field.key, e.target.checked)}
              />
              <span>{field.label}</span>
            </label>
          ))}
        </div>
        <small className="form-hint">
          Если ничего не выбрано, будут показываться все поля
        </small>
      </div>
    </div>
  )
}


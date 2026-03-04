import { PHONE_PATTERN, PHONE_ERROR_MESSAGE } from '../../utils/constants'

interface UserSettings {
  phone: string
  contact_name: string
  default_show_username: boolean
  object_card_display_types?: string[]
  object_list_display_types?: string[]
}

interface ContactSettingsProps {
  settings: UserSettings
  onChange: (field: keyof UserSettings, value: string | boolean | string[]) => void
}

export function ContactSettings({ settings, onChange }: ContactSettingsProps): JSX.Element {
  return (
    <div className="form-section">
      <div className="form-group">
        <label className="form-label">Номер телефона</label>
        <input
          type="tel"
          className="form-input"
          value={settings.phone}
          onChange={(e) => onChange('phone', e.target.value)}
          placeholder="89693386969"
          pattern="^8\d{10}$"
          title="Номер должен быть в формате 89693386969 (11 цифр, начинается с 8)"
        />
        <small className="form-hint">Формат: 89693386969 (11 цифр, начинается с 8)</small>
      </div>

      <div className="form-group">
        <label className="form-label">Имя контакта</label>
        <input
          type="text"
          className="form-input"
          value={settings.contact_name}
          onChange={(e) => onChange('contact_name', e.target.value)}
          placeholder="Ваше имя"
        />
        <small className="form-hint">Имя будет отображаться в объявлениях</small>
      </div>

      <div className="form-group">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={settings.default_show_username}
            onChange={(e) => onChange('default_show_username', e.target.checked)}
          />
          <span>Показывать username Telegram по умолчанию</span>
        </label>
        <small className="form-hint">
          При создании новых объектов будет включено отображение вашего Telegram username
        </small>
      </div>
    </div>
  )
}


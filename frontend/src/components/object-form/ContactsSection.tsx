import { type ChangeEvent } from 'react'
import type { ObjectFormData } from '../../types/models'

interface ContactsSectionProps {
  formData: ObjectFormData
  onInputChange: (field: keyof ObjectFormData) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void
  onChange: (field: keyof ObjectFormData, value: string | boolean) => void
}

export function ContactsSection({ formData, onInputChange, onChange }: ContactsSectionProps): JSX.Element {
  return (
    <div className="form-section">
      <h3 className="section-title">Контакты</h3>
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Имя контакта</label>
          <input
            type="text"
            className="form-input"
            value={formData.contact_name}
            onChange={onInputChange('contact_name')}
            autoComplete="off"
          />
        </div>
        <div className="form-group">
          <label className="form-label">Телефон</label>
          <input
            type="tel"
            className="form-input"
            value={formData.phone_number}
            onChange={onInputChange('phone_number')}
            placeholder="89693386969"
            pattern="^8\d{10}$"
            title="Номер должен быть в формате 89693386969 (11 цифр, начинается с 8)"
            autoComplete="off"
          />
          <small className="form-hint">Формат: 89693386969 (11 цифр, начинается с 8)</small>
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Имя контакта 2</label>
          <input
            type="text"
            className="form-input"
            value={formData.contact_name_2}
            onChange={onInputChange('contact_name_2')}
            autoComplete="off"
          />
        </div>
        <div className="form-group">
          <label className="form-label">Телефон 2</label>
          <input
            type="tel"
            className="form-input"
            value={formData.phone_number_2}
            onChange={onInputChange('phone_number_2')}
            placeholder="89693386969"
            pattern="^8\d{10}$"
            title="Номер должен быть в формате 89693386969 (11 цифр, начинается с 8)"
            autoComplete="off"
          />
          <small className="form-hint">Формат: 89693386969 (11 цифр, начинается с 8)</small>
        </div>
      </div>
      <div className="form-group">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={formData.show_username}
            onChange={(e) => onChange('show_username', e.target.checked)}
          />
          <span>Показывать username Telegram</span>
        </label>
      </div>
    </div>
  )
}


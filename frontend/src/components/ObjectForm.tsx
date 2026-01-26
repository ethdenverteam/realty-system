import { type ChangeEvent, type FormEvent } from 'react'
import type { ObjectFormData, RoomsType, RenovationType } from '../types/models'
import './ObjectForm.css'

interface ObjectFormProps {
  formData: ObjectFormData
  onChange: (data: ObjectFormData) => void
  onSubmit: (e: FormEvent<HTMLFormElement>) => void
  loading?: boolean
  submitLabel?: string
  cancelLabel?: string
  onCancel?: () => void
  error?: string
}

const ROOMS_OPTIONS: RoomsType[] = [
  'Студия',
  '1к',
  '2к',
  '3к',
  '4+к',
  'Дом',
  'евро1к',
  'евро2к',
  'евро3к',
]

const RENOVATION_OPTIONS: RenovationType[] = [
  'Черновая',
  'ПЧО',
  'Ремонт требует освежения',
  'Хороший ремонт',
  'Инстаграмный',
]

export default function ObjectForm({
  formData,
  onChange,
  onSubmit,
  loading = false,
  submitLabel = 'Сохранить',
  cancelLabel = 'Отмена',
  onCancel,
  error,
}: ObjectFormProps): JSX.Element {
  const handleChange = (field: keyof ObjectFormData, value: string | boolean): void => {
    onChange({
      ...formData,
      [field]: value,
    })
  }

  const handleInputChange = (field: keyof ObjectFormData) => (
    e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ): void => {
    const value = e.target.type === 'checkbox' 
      ? (e.target as HTMLInputElement).checked 
      : e.target.value
    handleChange(field, value)
  }

  return (
    <div className="object-form-container">
      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={onSubmit} className="create-object-form">
        <div className="form-section">
          <h3 className="section-title">Основная информация</h3>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Тип комнат *</label>
              <select
                className="form-input"
                value={formData.rooms_type}
                onChange={handleInputChange('rooms_type')}
                required
              >
                <option value="">Выберите тип</option>
                {ROOMS_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Цена (тыс. руб.) *</label>
              <input
                type="number"
                className="form-input"
                value={formData.price}
                onChange={handleInputChange('price')}
                step="0.01"
                min="0"
                required
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Площадь (м²) *</label>
              <input
                type="number"
                className="form-input"
                value={formData.area}
                onChange={handleInputChange('area')}
                step="0.01"
                min="0"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Этаж</label>
              <input
                type="text"
                className="form-input"
                value={formData.floor}
                onChange={handleInputChange('floor')}
                placeholder="например: 5/9"
              />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Районы</label>
            <input
              type="text"
              className="form-input"
              value={formData.districts}
              onChange={handleInputChange('districts')}
              placeholder="Введите районы через запятую"
            />
            <small className="form-hint">Например: ККБ, Музыкальный</small>
          </div>
        </div>

        <div className="form-section">
          <h3 className="section-title">Описание</h3>
          <div className="form-group">
            <label className="form-label">Комментарий</label>
            <textarea
              className="form-input"
              rows={4}
              value={formData.comment}
              onChange={handleInputChange('comment')}
              placeholder="Опишите квартиру и условия покупки"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Адрес</label>
            <input
              type="text"
              className="form-input"
              value={formData.address}
              onChange={handleInputChange('address')}
              placeholder="Улица и номер дома"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Состояние ремонта</label>
            <select
              className="form-input"
              value={formData.renovation}
              onChange={handleInputChange('renovation')}
            >
              <option value="">Не указано</option>
              {RENOVATION_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-section">
          <h3 className="section-title">Контакты</h3>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Имя контакта</label>
              <input
                type="text"
                className="form-input"
                value={formData.contact_name}
                onChange={handleInputChange('contact_name')}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Телефон</label>
              <input
                type="tel"
                className="form-input"
                value={formData.phone_number}
                onChange={handleInputChange('phone_number')}
                placeholder="+79991234567"
              />
            </div>
          </div>
          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={formData.show_username}
                onChange={(e) => handleChange('show_username', e.target.checked)}
              />
              <span>Показывать username Telegram</span>
            </label>
          </div>
        </div>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? 'Сохранение...' : submitLabel}
          </button>
          {onCancel && (
            <button
              type="button"
              className="btn btn-secondary btn-block"
              onClick={onCancel}
            >
              {cancelLabel}
            </button>
          )}
        </div>
      </form>
    </div>
  )
}


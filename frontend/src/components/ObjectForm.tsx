import { type ChangeEvent, type FormEvent, useState, useEffect } from 'react'
import type { ObjectFormData, RoomsType, RenovationType } from '../types/models'
import api from '../utils/api'
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
  const [districts, setDistricts] = useState<string[]>([])
  const [selectedDistricts, setSelectedDistricts] = useState<string[]>([])

  useEffect(() => {
    void loadDistricts()
  }, [])

  useEffect(() => {
    // Parse districts from formData (comma-separated string) when formData changes
    if (formData.districts) {
      const parsed = formData.districts.split(',').map(d => d.trim()).filter(d => d.length > 0)
      if (JSON.stringify(parsed.sort()) !== JSON.stringify(selectedDistricts.sort())) {
        setSelectedDistricts(parsed)
      }
    } else if (selectedDistricts.length > 0) {
      setSelectedDistricts([])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData.districts])

  useEffect(() => {
    // Update formData when selectedDistricts changes
    const districtsString = selectedDistricts.join(', ')
    if (districtsString !== formData.districts) {
      handleChange('districts', districtsString)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDistricts])

  const loadDistricts = async (): Promise<void> => {
    try {
      const res = await api.get<{ districts: string[] }>('/user/dashboard/districts')
      setDistricts(res.data.districts || [])
    } catch (err) {
      console.error('Error loading districts:', err)
    }
  }

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

  const handleDistrictsChange = (e: ChangeEvent<HTMLSelectElement>): void => {
    const selected = Array.from(e.target.selectedOptions, option => option.value)
    setSelectedDistricts(selected)
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
            <select
              multiple
              className="form-input form-input-multiple"
              value={selectedDistricts}
              onChange={handleDistrictsChange}
              size={Math.min(districts.length + 1, 8)}
            >
              {districts.map((district) => (
                <option key={district} value={district}>
                  {district}
                </option>
              ))}
            </select>
            <small className="form-hint">
              Удерживайте Ctrl (или Cmd на Mac) для выбора нескольких районов. Выбрано: {selectedDistricts.length}
            </small>
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
                placeholder="89693386969"
                pattern="^8\d{10}$"
                title="Номер должен быть в формате 89693386969 (11 цифр, начинается с 8)"
              />
              <small className="form-hint">Формат: 89693386969 (11 цифр, начинается с 8)</small>
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


import { type ChangeEvent, type FormEvent, useState, useEffect, useRef, useCallback } from 'react'
import type { ObjectFormData } from '../types/models'
import api from '../utils/api'
import { FilterSelect } from './FilterSelect'
import { ROOMS_TYPES, RENOVATION_TYPES } from '../utils/constants'
import './ObjectForm.css'

// Компонент для предпросмотра фото с правильной очисткой URL
function PhotoPreview({ file }: { file: File }): JSX.Element {
  const [previewUrl, setPreviewUrl] = useState<string>('')

  useEffect(() => {
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => {
      URL.revokeObjectURL(url)
    }
  }, [file])

  return (
    <div style={{ marginTop: '10px' }}>
      <img
        src={previewUrl}
        alt="Предпросмотр"
        style={{ maxWidth: '200px', maxHeight: '200px', borderRadius: '4px' }}
      />
      <p style={{ marginTop: '5px', fontSize: '14px', color: '#666' }}>
        {file.name}
      </p>
    </div>
  )
}

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
  // Флаг для предотвращения циклических обновлений при синхронизации formData -> selectedDistricts
  const isSyncingFromFormData = useRef(false)

  useEffect(() => {
    void loadDistricts()
  }, [])

  // Синхронизация selectedDistricts с formData.districts (когда formData меняется извне, например при загрузке объекта)
  useEffect(() => {
    if (isSyncingFromFormData.current) {
      isSyncingFromFormData.current = false
      return
    }
    
    const parsed = formData.districts 
      ? formData.districts.split(',').map(d => d.trim()).filter(d => d.length > 0)
      : []
    
    // Обновляем selectedDistricts только если он отличается от текущего
    const currentString = selectedDistricts.join(', ')
    const newString = parsed.join(', ')
    if (currentString !== newString) {
      setSelectedDistricts(parsed)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData.districts])

  const loadDistricts = async (): Promise<void> => {
    try {
      const res = await api.get<{ districts: string[] }>('/user/dashboard/districts')
      setDistricts(res.data.districts || [])
    } catch (err) {
      console.error('Error loading districts:', err)
    }
  }

  const handleChange = useCallback((field: keyof ObjectFormData, value: string | boolean): void => {
    onChange({
      ...formData,
      [field]: value,
    })
  }, [formData, onChange])

  const handleInputChange = useCallback((field: keyof ObjectFormData) => (
    e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ): void => {
    const value = e.target.type === 'checkbox' 
      ? (e.target as HTMLInputElement).checked 
      : e.target.value
    handleChange(field, value)
  }, [handleChange])

  const handleDistrictsChange = useCallback((e: ChangeEvent<HTMLSelectElement>): void => {
    const selected = Array.from(e.target.selectedOptions, option => option.value)
    setSelectedDistricts(selected)
    // Сразу обновляем formData.districts для немедленной синхронизации
    const districtsString = selected.join(', ')
    // Устанавливаем флаг, чтобы избежать обратной синхронизации в useEffect
    isSyncingFromFormData.current = true
    handleChange('districts', districtsString)
    console.log('ObjectForm - districts changed:', selected, '-> districtsString:', districtsString)
  }, [handleChange])

  return (
    <div className="object-form-container">
      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={onSubmit} className="create-object-form">
        <div className="form-section">
          <h3 className="section-title">Основная информация</h3>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Тип комнат *</label>
              <FilterSelect
                value={formData.rooms_type}
                onChange={(value) => handleChange('rooms_type', value)}
                options={ROOMS_TYPES.map((type) => ({ value: type, label: type }))}
                placeholder="Выберите тип"
                size="md"
                required
              />
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
                autoComplete="off"
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
                autoComplete="off"
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
                autoComplete="off"
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
            <label className="form-label">Фото объекта</label>
            <input
              type="file"
              accept="image/*"
              className="form-input"
              onChange={(e) => {
                const file = e.target.files?.[0] || null
                if (file) {
                  // Проверка типа файла
                  if (!file.type.startsWith('image/')) {
                    alert('Пожалуйста, выберите файл изображения')
                    e.target.value = ''
                    return
                  }
                }
                onChange({
                  ...formData,
                  photo: file,
                })
              }}
            />
            {formData.photo && (
              <PhotoPreview file={formData.photo} />
            )}
            <small className="form-hint">
              Разрешены только файлы изображений (JPG, PNG, GIF, WEBP и др.)
            </small>
          </div>
          <div className="form-group">
            <label className="form-label">Комментарий</label>
            <textarea
              className="form-input"
              rows={4}
              value={formData.comment}
              onChange={handleInputChange('comment')}
              placeholder="Опишите квартиру и условия покупки"
              autoComplete="off"
            />
          </div>
          <div className="form-group">
            <label className="form-label">ЖК (жилой комплекс)</label>
            <input
              type="text"
              className="form-input"
              value={formData.residential_complex}
              onChange={handleInputChange('residential_complex')}
              placeholder="Название жилого комплекса"
              autoComplete="off"
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
              autoComplete="off"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Состояние ремонта</label>
            <FilterSelect
              value={formData.renovation}
              onChange={(value) => handleChange('renovation', value)}
              options={RENOVATION_TYPES.map((type) => ({ value: type, label: type }))}
              placeholder="Не указано"
              size="md"
            />
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
                autoComplete="off"
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
                onChange={handleInputChange('contact_name_2')}
                autoComplete="off"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Телефон 2</label>
              <input
                type="tel"
                className="form-input"
                value={formData.phone_number_2}
                onChange={handleInputChange('phone_number_2')}
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


import { type ChangeEvent } from 'react'
import { FilterSelect } from '../FilterSelect'
import { ROOMS_TYPES } from '../../utils/constants'
import type { ObjectFormData } from '../../types/models'
import DistrictsSelector from './DistrictsSelector'

interface BasicInfoSectionProps {
  formData: ObjectFormData
  onInputChange: (field: keyof ObjectFormData) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void
  onChange: (field: keyof ObjectFormData, value: string | boolean) => void
}

export function BasicInfoSection({ formData, onInputChange, onChange }: BasicInfoSectionProps): JSX.Element {
  return (
    <div className="form-section">
      <h3 className="section-title">Основная информация</h3>
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Тип комнат *</label>
          <FilterSelect
            value={formData.rooms_type}
            onChange={(value) => onChange('rooms_type', value)}
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
            onChange={onInputChange('price')}
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
            onChange={onInputChange('area')}
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
            onChange={onInputChange('floor')}
            placeholder="например: 5/9"
            autoComplete="off"
          />
        </div>
      </div>
      <DistrictsSelector
        formData={formData}
        onChange={onChange}
      />
    </div>
  )
}


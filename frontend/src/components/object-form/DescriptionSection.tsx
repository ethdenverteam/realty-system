import { type ChangeEvent } from 'react'
import { FilterSelect } from '../FilterSelect'
import { RENOVATION_TYPES } from '../../utils/constants'
import type { ObjectFormData } from '../../types/models'

interface DescriptionSectionProps {
  formData: ObjectFormData
  onInputChange: (field: keyof ObjectFormData) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void
  onChange: (field: keyof ObjectFormData, value: string | boolean) => void
}

export function DescriptionSection({ formData, onInputChange, onChange }: DescriptionSectionProps): JSX.Element {
  return (
    <div className="form-section">
      <h3 className="section-title">Описание</h3>
      <div className="form-group">
        <label className="form-label">Комментарий</label>
        <textarea
          className="form-input"
          rows={4}
          value={formData.comment}
          onChange={onInputChange('comment')}
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
          onChange={onInputChange('residential_complex')}
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
          onChange={onInputChange('address')}
          placeholder="Улица и номер дома"
          autoComplete="off"
        />
      </div>
      <div className="form-group">
        <label className="form-label">Состояние ремонта</label>
        <FilterSelect
          value={formData.renovation}
          onChange={(value) => onChange('renovation', value)}
          options={RENOVATION_TYPES.map((type) => ({ value: type, label: type }))}
          placeholder="Не указано"
          size="md"
        />
      </div>
    </div>
  )
}


import { type ChangeEvent, type FormEvent, useCallback } from 'react'
import type { ObjectFormData } from '../types/models'
import { BasicInfoSection } from './object-form/BasicInfoSection'
import { PhotoSection } from './object-form/PhotoSection'
import { DescriptionSection } from './object-form/DescriptionSection'
import { ContactsSection } from './object-form/ContactsSection'
import './ObjectForm.css'
import './Glass.css'

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

  return (
    <div className="object-form-container">
      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={onSubmit} className="create-object-form">
        <BasicInfoSection
          formData={formData}
          onInputChange={handleInputChange}
          onChange={handleChange}
        />
        <PhotoSection
          formData={formData}
          onChange={onChange}
        />
        <DescriptionSection
          formData={formData}
          onInputChange={handleInputChange}
          onChange={handleChange}
        />
        <ContactsSection
          formData={formData}
          onInputChange={handleInputChange}
          onChange={handleChange}
        />

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


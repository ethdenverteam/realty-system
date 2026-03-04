import { type ChangeEvent } from 'react'
import type { ObjectFormData } from '../../types/models'

interface PhotoSectionProps {
  formData: ObjectFormData
  onChange: (data: ObjectFormData) => void
}

import { useState, useEffect } from 'react'

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

export function PhotoSection({ formData, onChange }: PhotoSectionProps): JSX.Element {
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>): void => {
    const file = e.target.files?.[0] || null
    if (file) {
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
  }

  return (
    <div className="form-section glass-card" style={{ marginTop: '20px', marginBottom: '20px' }}>
      <h3 className="section-title">Фото объекта</h3>
      <div className="form-group">
        <label className="form-label">Выберите фото</label>
        <input
          type="file"
          accept="image/*"
          className="form-input"
          onChange={handleFileChange}
        />
        {formData.photo && (
          <PhotoPreview file={formData.photo} />
        )}
        <small className="form-hint">
          Разрешены только файлы изображений (JPG, PNG, GIF, WEBP и др.)
        </small>
      </div>
    </div>
  )
}


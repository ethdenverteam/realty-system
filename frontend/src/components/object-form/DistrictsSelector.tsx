import { useState, useEffect, useRef, useCallback, type ChangeEvent } from 'react'
import api from '../../utils/api'
import type { ObjectFormData } from '../../types/models'

interface DistrictsSelectorProps {
  formData: ObjectFormData
  onChange: (field: keyof ObjectFormData, value: string | boolean) => void
}

export default function DistrictsSelector({ formData, onChange }: DistrictsSelectorProps): JSX.Element {
  const [districts, setDistricts] = useState<string[]>([])
  const [selectedDistricts, setSelectedDistricts] = useState<string[]>([])
  const [districtSearch, setDistrictSearch] = useState<string>('')
  const isSyncingFromFormData = useRef(false)

  useEffect(() => {
    void loadDistricts()
  }, [])

  useEffect(() => {
    if (isSyncingFromFormData.current) {
      isSyncingFromFormData.current = false
      return
    }
    
    const parsed = formData.districts 
      ? formData.districts.split(',').map(d => d.trim()).filter(d => d.length > 0)
      : []
    
    const currentString = selectedDistricts.join(', ')
    const newString = parsed.join(', ')
    if (currentString !== newString) {
      setSelectedDistricts(parsed)
    }
  }, [formData.districts])

  const loadDistricts = async (): Promise<void> => {
    try {
      const res = await api.get<{ districts: string[] }>('/user/dashboard/districts')
      setDistricts(res.data.districts || [])
    } catch (err) {
      console.error('Error loading districts:', err)
    }
  }

  const handleDistrictsChange = useCallback((e: ChangeEvent<HTMLSelectElement>): void => {
    const selected = Array.from(e.target.selectedOptions, option => option.value)
    setSelectedDistricts(selected)
    const districtsString = selected.join(', ')
    isSyncingFromFormData.current = true
    onChange('districts', districtsString)
  }, [onChange])

  return (
    <div className="form-group">
      <label className="form-label">Районы</label>
      <div style={{ position: 'relative' }}>
        <input
          type="text"
          className="form-input"
          placeholder="Поиск района..."
          value={districtSearch}
          onChange={(e) => setDistrictSearch(e.target.value)}
          style={{ marginBottom: '8px', paddingRight: '30px' }}
          autoComplete="off"
        />
        <select
          multiple
          className="form-input form-input-multiple"
          value={selectedDistricts}
          onChange={handleDistrictsChange}
          size={Math.min(districts.length + 1, 8)}
          style={{ 
            overflowY: 'auto', 
            overflowX: 'hidden',
            maxHeight: '250px'
          }}
        >
          {districts.map((district) => {
            const matchesSearch = !districtSearch || 
              district.toLowerCase().includes(districtSearch.toLowerCase())
            const isSelected = selectedDistricts.includes(district)
            const shouldShow = matchesSearch || isSelected
            return (
              <option 
                key={district} 
                value={district}
                style={{ display: shouldShow ? 'block' : 'none' }}
              >
                {district}
              </option>
            )
          })}
        </select>
      </div>
      <small className="form-hint">
        Удерживайте Ctrl (или Cmd на Mac) для выбора нескольких районов. Выбрано: {selectedDistricts.length}
        {selectedDistricts.length > 0 && (
          <span style={{ display: 'block', marginTop: '4px', fontSize: '12px', color: '#666' }}>
            Выбрано: {selectedDistricts.join(', ')}
          </span>
        )}
      </small>
    </div>
  )
}


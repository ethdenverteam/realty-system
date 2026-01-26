import axios from 'axios'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import ObjectForm from '../../components/ObjectForm'
import api from '../../utils/api'
import type { ObjectFormData, CreateObjectRequest, CreateObjectResponse, ApiErrorResponse } from '../../types/models'
import './CreateObject.css'

const initialFormData: ObjectFormData = {
  rooms_type: '',
  price: '',
  area: '',
  floor: '',
  districts: '',
  comment: '',
  address: '',
  renovation: '',
  contact_name: '',
  phone_number: '',
  show_username: false,
}

interface UserSettings {
  phone: string
  contact_name: string
  default_show_username: boolean
}

export default function UserCreateObject(): JSX.Element {
  const navigate = useNavigate()
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string>('')
  const [formData, setFormData] = useState<ObjectFormData>(initialFormData)

  useEffect(() => {
    void loadUserSettings()
  }, [])

  const loadUserSettings = async (): Promise<void> => {
    try {
      const response = await api.get<UserSettings>('/user/dashboard/settings/data')
      setFormData((prev) => ({
        ...prev,
        phone_number: response.data.phone || '',
        contact_name: response.data.contact_name || '',
        show_username: response.data.default_show_username || false,
      }))
    } catch (err: unknown) {
      // Silently fail - settings are optional
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error('Failed to load user settings:', err.response?.data || err.message)
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    setError('')
    
    // Validate phone number if provided
    if (formData.phone_number && formData.phone_number.trim()) {
      const phonePattern = /^8\d{10}$/
      if (!phonePattern.test(formData.phone_number.trim())) {
        setError('Номер телефона должен быть в формате 89693386969 (11 цифр, начинается с 8)')
        return
      }
    }
    
    setLoading(true)

    try {
      const districts = formData.districts
        ? formData.districts
            .split(',')
            .map((d) => d.trim())
            .filter((d) => d.length > 0)
        : []

      const requestData: CreateObjectRequest = {
        rooms_type: formData.rooms_type,
        price: parseFloat(formData.price),
        area: formData.area ? parseFloat(formData.area) : null,
        floor: formData.floor || null,
        districts_json: districts,
        comment: formData.comment || null,
        address: formData.address || null,
        renovation: formData.renovation || null,
        contact_name: formData.contact_name || null,
        phone_number: formData.phone_number?.trim() || null,
        show_username: formData.show_username,
      }

      const response = await api.post<CreateObjectResponse>('/objects/', requestData)

      if (response.data.success || response.data.object_id) {
        navigate('/user/dashboard/objects', { replace: true })
      } else {
        setError('Ошибка при создании объекта')
      }
    } catch (err: unknown) {
      let message = 'Ошибка при создании объекта'
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        message = err.response?.data?.error || err.message || message
      }
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = (): void => {
    navigate('/user/dashboard/objects')
  }

  return (
    <Layout title="Создать объект">
      <div className="create-object-page">
        <ObjectForm
          formData={formData}
          onChange={setFormData}
          onSubmit={handleSubmit}
          loading={loading}
          submitLabel="Создать объект"
          cancelLabel="Отмена"
          onCancel={handleCancel}
          error={error}
        />
      </div>
    </Layout>
  )
}

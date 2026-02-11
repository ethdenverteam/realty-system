import axios from 'axios'
import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import ObjectForm from '../../components/ObjectForm'
import api from '../../utils/api'
import type {
  ObjectFormData,
  RealtyObject,
  UpdateObjectRequest,
  ApiErrorResponse,
} from '../../types/models'
import './CreateObject.css'

const initialFormData: ObjectFormData = {
  rooms_type: '',
  price: '',
  area: '',
  floor: '',
  districts: '',
  comment: '',
  address: '',
  residential_complex: '',
  renovation: '',
  contact_name: '',
  phone_number: '',
  show_username: false,
}

export default function EditObject(): JSX.Element {
  const { objectId } = useParams<{ objectId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState<boolean>(true)
  const [saving, setSaving] = useState<boolean>(false)
  const [error, setError] = useState<string>('')
  const [object, setObject] = useState<RealtyObject | null>(null)
  const [formData, setFormData] = useState<ObjectFormData>(initialFormData)

  const loadObject = useCallback(async (): Promise<void> => {
    if (!objectId) return
    try {
      setLoading(true)
      setError('')
      const res = await api.get<RealtyObject>(`/user/dashboard/objects/${objectId}`)
      const obj = res.data
      setObject(obj)

      // Fill form with object data
      setFormData({
        rooms_type: obj.rooms_type || '',
        price: obj.price ? String(obj.price) : '',
        area: obj.area ? String(obj.area) : '',
        floor: obj.floor || '',
        districts: (obj.districts_json || []).join(', '),
        comment: obj.comment || '',
        address: obj.address || '',
        residential_complex: obj.residential_complex || '',
        renovation: obj.renovation || '',
        contact_name: obj.contact_name || '',
        phone_number: obj.phone_number || '',
        show_username: obj.show_username || false,
      })
    } catch (err: unknown) {
      setError('Ошибка загрузки объекта')
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error(err.response?.data || err.message)
      } else {
        console.error(err)
      }
    } finally {
      setLoading(false)
    }
  }, [objectId])

  useEffect(() => {
    void loadObject()
  }, [loadObject])

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    if (!objectId) return

    setError('')
    
    // Validate phone number if provided
    if (formData.phone_number && formData.phone_number.trim()) {
      const phonePattern = /^8\d{10}$/
      if (!phonePattern.test(formData.phone_number.trim())) {
        setError('Номер телефона должен быть в формате 89693386969 (11 цифр, начинается с 8)')
        return
      }
    }
    
    setSaving(true)

    try {
      const districts = formData.districts
        .split(',')
        .map((d) => d.trim())
        .filter((d) => d.length > 0)

      const requestData: UpdateObjectRequest = {
        rooms_type: formData.rooms_type || null,
        price: parseFloat(formData.price) || 0,
        area: formData.area ? parseFloat(formData.area) : null,
        floor: formData.floor || null,
        districts_json: districts,
        comment: formData.comment || null,
        address: formData.address || null,
        residential_complex: formData.residential_complex || null,
        renovation: formData.renovation || null,
        contact_name: formData.contact_name || null,
        phone_number: formData.phone_number?.trim() || null,
        show_username: formData.show_username,
      }

      await api.put<RealtyObject>(`/objects/${objectId}`, requestData)
      navigate(`/user/dashboard/objects/${objectId}`, { replace: true })
    } catch (err: unknown) {
      let message = 'Ошибка при сохранении объекта'
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        message = err.response?.data?.error || err.message || message
      }
      setError(message)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = (): void => {
    if (objectId) {
      navigate(`/user/dashboard/objects/${objectId}`)
    } else {
      navigate('/user/dashboard/objects')
    }
  }

  if (loading) {
    return (
      <Layout title="Редактирование объекта">
        <div className="create-object-page">
          <div className="loading">Загрузка...</div>
        </div>
      </Layout>
    )
  }

  if (error && !object) {
    return (
      <Layout title="Ошибка">
        <div className="create-object-page">
          <div className="alert alert-error">{error}</div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => navigate('/user/dashboard/objects')}
          >
            Вернуться к списку
          </button>
        </div>
      </Layout>
    )
  }

  return (
    <Layout title="Редактировать объект">
      <div className="create-object-page">
        <ObjectForm
          formData={formData}
          onChange={setFormData}
          onSubmit={handleSubmit}
          loading={saving}
          submitLabel="Сохранить изменения"
          cancelLabel="Отмена"
          onCancel={handleCancel}
          error={error}
        />
      </div>
    </Layout>
  )
}

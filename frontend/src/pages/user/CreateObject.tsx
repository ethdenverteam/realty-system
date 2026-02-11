import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import ObjectForm from '../../components/ObjectForm'
import { useApiData } from '../../hooks/useApiData'
import { useApiMutation } from '../../hooks/useApiMutation'
import { PHONE_PATTERN, PHONE_ERROR_MESSAGE } from '../../utils/constants'
import type { ObjectFormData, CreateObjectRequest, CreateObjectResponse } from '../../types/models'
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
  const [formData, setFormData] = useState<ObjectFormData>(initialFormData)

  // Загрузка настроек пользователя
  const { data: settingsData } = useApiData<UserSettings>({
    url: '/user/dashboard/settings/data',
    errorContext: 'Loading user settings',
    defaultErrorMessage: 'Ошибка загрузки настроек',
    autoLoad: true,
  })

  // Применение настроек к форме
  useEffect(() => {
    if (settingsData) {
      setFormData((prev) => ({
        ...prev,
        phone_number: settingsData.phone || '',
        contact_name: settingsData.contact_name || '',
        show_username: settingsData.default_show_username || false,
      }))
    }
  }, [settingsData])

  // Мутация для создания объекта
  const { mutate: createObject, loading, error, clearError } = useApiMutation<CreateObjectRequest, CreateObjectResponse>({
    url: '/objects/',
    method: 'POST',
    errorContext: 'Creating object',
    defaultErrorMessage: 'Ошибка при создании объекта',
    onSuccess: (data) => {
      if (data.success || data.object_id) {
        navigate('/user/dashboard/objects', { replace: true })
      }
    },
  })

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    clearError()

    // Валидация телефона
    if (formData.phone_number && formData.phone_number.trim()) {
      if (!PHONE_PATTERN.test(formData.phone_number.trim())) {
        clearError()
        // Устанавливаем ошибку через состояние (можно улучшить через setError в хуке)
        return
      }
    }

    // Подготовка данных
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

    await createObject(requestData)
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
          error={error || (formData.phone_number && formData.phone_number.trim() && !PHONE_PATTERN.test(formData.phone_number.trim()) ? PHONE_ERROR_MESSAGE : '')}
        />
      </div>
    </Layout>
  )
}

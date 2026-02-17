import { useState, useEffect, useRef } from 'react'
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
  residential_complex: '',
  renovation: '',
  contact_name: '',
  phone_number: '',
  contact_name_2: '',
  phone_number_2: '',
  show_username: false,
  photo: null,
}

interface UserSettings {
  phone: string
  contact_name: string
  default_show_username: boolean
}

export default function UserCreateObject(): JSX.Element {
  const navigate = useNavigate()
  const [formData, setFormData] = useState<ObjectFormData>(initialFormData)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string>('')

  // Загрузка настроек пользователя
  const { data: settingsData } = useApiData<UserSettings>({
    url: '/user/dashboard/settings/data',
    errorContext: 'Loading user settings',
    defaultErrorMessage: 'Ошибка загрузки настроек',
    autoLoad: true,
  })

  // Флаг для отслеживания, были ли применены настройки
  const settingsApplied = useRef(false)
  
  // Применение настроек к форме только один раз при первой загрузке
  useEffect(() => {
    if (settingsData && !settingsApplied.current) {
      setFormData((prev) => {
        // Применяем настройки только если поля пустые (не перезаписываем ввод пользователя)
        const newData = { ...prev }
        if (!prev.phone_number && settingsData.phone) {
          newData.phone_number = settingsData.phone
        }
        if (!prev.contact_name && settingsData.contact_name) {
          newData.contact_name = settingsData.contact_name
        }
        if (!prev.show_username && settingsData.default_show_username) {
          newData.show_username = settingsData.default_show_username
        }
        return newData
      })
      settingsApplied.current = true
    }
  }, [settingsData])

  // Мутация для создания объекта (используется только когда нет фото)
  const { mutate: createObject, loading: mutationLoading, error: mutationError, clearError } = useApiMutation<CreateObjectRequest, CreateObjectResponse>({
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

  // Используем локальное состояние loading и error для поддержки FormData
  const currentLoading = loading || mutationLoading
  const currentError = error || mutationError

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    clearError()

    // Валидация телефонов
    if (formData.phone_number && formData.phone_number.trim()) {
      if (!PHONE_PATTERN.test(formData.phone_number.trim())) {
        clearError()
        // Устанавливаем ошибку через состояние (можно улучшить через setError в хуке)
        return
      }
    }
    if (formData.phone_number_2 && formData.phone_number_2.trim()) {
      if (!PHONE_PATTERN.test(formData.phone_number_2.trim())) {
        clearError()
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

    // Если есть фото, отправляем через FormData
    if (formData.photo) {
      const formDataToSend = new FormData()
      formDataToSend.append('rooms_type', formData.rooms_type)
      formDataToSend.append('price', formData.price)
      if (formData.area) formDataToSend.append('area', formData.area)
      if (formData.floor) formDataToSend.append('floor', formData.floor)
      formDataToSend.append('districts_json', JSON.stringify(districts))
      if (formData.comment) formDataToSend.append('comment', formData.comment)
      if (formData.address) formDataToSend.append('address', formData.address)
      if (formData.residential_complex) formDataToSend.append('residential_complex', formData.residential_complex)
      if (formData.renovation) formDataToSend.append('renovation', formData.renovation)
      if (formData.contact_name) formDataToSend.append('contact_name', formData.contact_name)
      if (formData.phone_number?.trim()) formDataToSend.append('phone_number', formData.phone_number.trim())
      if (formData.contact_name_2) formDataToSend.append('contact_name_2', formData.contact_name_2)
      if (formData.phone_number_2?.trim()) formDataToSend.append('phone_number_2', formData.phone_number_2.trim())
      formDataToSend.append('show_username', formData.show_username.toString())
      formDataToSend.append('photo_0', formData.photo)

      try {
        setLoading(true)
        const token = localStorage.getItem('jwt_token')
        const response = await fetch('/system/objects/', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          body: formDataToSend,
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ error: 'Ошибка при создании объекта' }))
          throw new Error(errorData.error || 'Ошибка при создании объекта')
        }

        const data = await response.json()
        if (data.success || data.object_id) {
          navigate('/user/dashboard/objects', { replace: true })
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Ошибка при создании объекта'
        setError(message)
      } finally {
        setLoading(false)
      }
    } else {
      // Если фото нет, отправляем через JSON как раньше
      const requestData: CreateObjectRequest = {
        rooms_type: formData.rooms_type,
        price: parseFloat(formData.price),
        area: formData.area ? parseFloat(formData.area) : null,
        floor: formData.floor || null,
        districts_json: districts,
        comment: formData.comment || null,
        address: formData.address || null,
        residential_complex: formData.residential_complex || null,
        renovation: formData.renovation || null,
        contact_name: formData.contact_name || null,
        phone_number: formData.phone_number?.trim() || null,
        contact_name_2: formData.contact_name_2 || null,
        phone_number_2: formData.phone_number_2?.trim() || null,
        show_username: formData.show_username,
      }

      await createObject(requestData)
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
          loading={currentLoading}
          submitLabel="Создать объект"
          cancelLabel="Отмена"
          onCancel={handleCancel}
          error={currentError || 
            (formData.phone_number && formData.phone_number.trim() && !PHONE_PATTERN.test(formData.phone_number.trim()) ? PHONE_ERROR_MESSAGE : '') ||
            (formData.phone_number_2 && formData.phone_number_2.trim() && !PHONE_PATTERN.test(formData.phone_number_2.trim()) ? 'Второй номер телефона должен быть в формате 89693386969' : '')
          }
        />
      </div>
    </Layout>
  )
}

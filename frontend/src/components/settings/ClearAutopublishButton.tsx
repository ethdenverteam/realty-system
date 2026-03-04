import { useState } from 'react'
import { useApiMutation } from '../../hooks/useApiMutation'

export function ClearAutopublishButton(): JSX.Element {
  const [success, setSuccess] = useState<string>('')

  const { mutate: clearAutopublish, loading, error } = useApiMutation<Record<string, never>, { success: boolean; message: string; deleted: { configs: number; publication_queues: number; account_queues: number } }>({
    url: '/user/dashboard/settings/clear-autopublish',
    method: 'POST',
    errorContext: 'Clearing autopublish',
    defaultErrorMessage: 'Ошибка при очистке автопубликации',
    onSuccess: (data) => {
      setSuccess(`Автопубликация успешно очищена. Удалено: ${data.deleted.configs} конфигураций, ${data.deleted.publication_queues + data.deleted.account_queues} задач в очереди.`)
    },
  })

  const handleClear = (): void => {
    if (!confirm('Вы уверены, что хотите снять все объекты с автопубликации и очистить очередь? Это действие нельзя отменить.')) {
      return
    }

    setSuccess('')
    void clearAutopublish({})
  }

  return (
    <div>
      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}
      <button
        type="button"
        className="btn btn-warning btn-block"
        onClick={handleClear}
        disabled={loading}
      >
        {loading ? 'Очистка...' : 'Снять автопубликацию и очистить очередь'}
      </button>
    </div>
  )
}


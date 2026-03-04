import { useEffect, useState } from 'react'
import api from '../utils/api'
import type { RealtyObjectListItem, ObjectsListResponse } from '../types/models'

export function useObjects(): RealtyObjectListItem[] {
  const [objects, setObjects] = useState<RealtyObjectListItem[]>([])

  useEffect(() => {
    void loadObjects()
  }, [])

  const loadObjects = async (): Promise<void> => {
    try {
      const res = await api.get<ObjectsListResponse>('/user/dashboard/objects/list', {
        params: { per_page: 100 },
      })
      setObjects(res.data.objects || [])
    } catch (err) {
      console.error('Error loading objects:', err)
    }
  }

  return objects
}


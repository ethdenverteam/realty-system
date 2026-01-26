import { Navigate } from 'react-router-dom'
import type { ReactElement } from 'react'
import { useAuth } from '../contexts/AuthContext'

export default function ProtectedRoute({
  children,
  requireAdmin = false,
}: {
  children: ReactElement
  requireAdmin?: boolean
}): JSX.Element {
  const { isAuthenticated, isAdmin, loading } = useAuth()

  if (loading) {
    return <div>Загрузка...</div>
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/user/dashboard" replace />
  }

  return children
}



import axios from 'axios'
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import api from '../utils/api'
import type { User } from '../types/models'

type LoginResult =
  | { success: true; user: User }
  | { success: false; error: string }

interface LoginResponse {
  token: string
  user: User
}

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (code: string) => Promise<LoginResult>
  logout: () => Promise<void>
  isAuthenticated: boolean
  isAdmin: boolean
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }): JSX.Element {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('jwt_token')
    const userData = localStorage.getItem('user')

    if (token && userData) {
      try {
        setUser(JSON.parse(userData) as User)
      } catch (e) {
        console.error('Error parsing user data:', e)
        localStorage.removeItem('jwt_token')
        localStorage.removeItem('user')
      }
    }
    setLoading(false)
  }, [])

  const login = async (code: string): Promise<LoginResult> => {
    try {
      const response = await api.post<LoginResponse>('/auth/login', { code })
      const { token, user: userData } = response.data

      localStorage.setItem('jwt_token', token)
      localStorage.setItem('user', JSON.stringify(userData))
      setUser(userData)

      return { success: true, user: userData }
    } catch (error: unknown) {
      const message = axios.isAxiosError(error)
        ? (error.response?.data as any)?.error || 'Ошибка входа'
        : 'Ошибка входа'
      return { success: false, error: String(message) }
    }
  }

  const logout = async (): Promise<void> => {
    try {
      await api.post('/auth/logout')
    } catch (e) {
      console.error('Logout error:', e)
    } finally {
      localStorage.removeItem('jwt_token')
      localStorage.removeItem('user')
      setUser(null)
    }
  }

  const value: AuthContextValue = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      isAuthenticated: !!user,
      isAdmin: user?.web_role === 'admin',
    }),
    [user, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}



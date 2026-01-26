import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import Landing from './pages/Landing'
import Login from './pages/Login'
import AdminBotChats from './pages/admin/BotChats'
import AdminDashboard from './pages/admin/Dashboard'
import AdminLogs from './pages/admin/Logs'
import UserCreateObject from './pages/user/CreateObject'
import UserDashboard from './pages/user/Dashboard'
import UserObjects from './pages/user/Objects'
import UserViewObject from './pages/user/ViewObject'
import './App.css'

export default function App(): JSX.Element {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />

            {/* Admin routes */}
            <Route
              path="/admin/dashboard"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/bot-chats"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminBotChats />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/logs"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminLogs />
                </ProtectedRoute>
              }
            />

            {/* User routes */}
            <Route
              path="/user/dashboard"
              element={
                <ProtectedRoute>
                  <UserDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/user/dashboard/objects"
              element={
                <ProtectedRoute>
                  <UserObjects />
                </ProtectedRoute>
              }
            />
            <Route
              path="/user/dashboard/objects/create"
              element={
                <ProtectedRoute>
                  <UserCreateObject />
                </ProtectedRoute>
              }
            />
            <Route
              path="/user/dashboard/objects/:objectId"
              element={
                <ProtectedRoute>
                  <UserViewObject />
                </ProtectedRoute>
              }
            />

            {/* Default redirect */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}



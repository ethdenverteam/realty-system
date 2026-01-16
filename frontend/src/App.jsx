import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Landing from './pages/Landing'
import Login from './pages/Login'
import AdminDashboard from './pages/admin/Dashboard'
import AdminBotChats from './pages/admin/BotChats'
import AdminLogs from './pages/admin/Logs'
import UserDashboard from './pages/user/Dashboard'
import UserObjects from './pages/user/Objects'
import UserCreateObject from './pages/user/CreateObject'
import './App.css'

function App() {
  return (
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
          
          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App


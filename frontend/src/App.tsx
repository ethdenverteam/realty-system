import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import Landing from './pages/Landing'
import Login from './pages/Login'
import AdminBotChats from './pages/admin/BotChats'
import AdminDashboard from './pages/admin/Dashboard'
import AdminLogs from './pages/admin/Logs'
import AdminUsers from './pages/admin/Users'
import AdminDatabaseSchema from './pages/admin/DatabaseSchema'
import AdminDropdownTest from './pages/admin/DropdownTest'
import AdminTest from './pages/admin/test/Test'
import AdminTestIndex from './pages/admin/test/TestIndex'
import AdminTypeScriptTypes from './pages/admin/TypeScriptTypes'
import AdminMobXStore from './pages/admin/MobXStore'
import UserCreateObject from './pages/user/CreateObject'
import UserDashboard from './pages/user/Dashboard'
import UserEditObject from './pages/user/EditObject'
import UserObjects from './pages/user/Objects'
import UserSettings from './pages/user/Settings'
import UserViewObject from './pages/user/ViewObject'
import Autopublish from './pages/user/Autopublish'
import Chats from './pages/user/Chats'
import TelegramAccounts from './pages/user/TelegramAccounts'
import ConnectTelegramAccount from './pages/user/ConnectTelegramAccount'
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
            <Route
              path="/admin/dashboard/users"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminUsers />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/database-schema"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminDatabaseSchema />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/dropdown-test"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminDropdownTest />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/test"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminTestIndex />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/test/components"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminTest />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/test/dropdown-test"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminDropdownTest />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/typescript-types"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminTypeScriptTypes />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/mobx-store"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminMobXStore />
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
              path="/user/dashboard/objects/:objectId/edit"
              element={
                <ProtectedRoute>
                  <UserEditObject />
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
            <Route
              path="/user/dashboard/settings"
              element={
                <ProtectedRoute>
                  <UserSettings />
                </ProtectedRoute>
              }
            />
            <Route
              path="/user/dashboard/autopublish"
              element={
                <ProtectedRoute>
                  <Autopublish />
                </ProtectedRoute>
              }
            />
            <Route
              path="/user/dashboard/chats"
              element={
                <ProtectedRoute>
                  <Chats />
                </ProtectedRoute>
              }
            />
            <Route
              path="/user/dashboard/telegram-accounts"
              element={
                <ProtectedRoute>
                  <TelegramAccounts />
                </ProtectedRoute>
              }
            />
            <Route
              path="/user/dashboard/telegram-accounts/connect"
              element={
                <ProtectedRoute>
                  <ConnectTelegramAccount />
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



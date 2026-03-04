import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

interface LayoutTopNavProps {
  isAdmin: boolean
}

export function LayoutTopNav({ isAdmin }: LayoutTopNavProps): JSX.Element {
  const location = useLocation()
  const { user } = useAuth()

  if (isAdmin) {
    return <AdminTopNav location={location} />
  }

  return <UserTopNav location={location} user={user} />
}

function AdminTopNav({ location }: { location: ReturnType<typeof useLocation> }): JSX.Element {
  const navItems = [
    { path: '/admin/dashboard', label: 'Главная', icon: HomeIcon },
    { path: '/admin/dashboard/bot-chats', label: 'Чаты', icon: ChatsIcon, match: '/bot-chats' },
    { path: '/admin/dashboard/chat-lists', label: 'Списки чатов', icon: ChatListsIcon, match: '/chat-lists' },
    { path: '/admin/dashboard/logs', label: 'Логи', icon: LogsIcon, match: '/logs' },
    { path: '/admin/dashboard/publication-queues', label: 'Очереди', icon: QueuesIcon, match: '/publication-queues' },
    { path: '/admin/dashboard/account-autopublish-monitor', label: 'Аккаунт авто', icon: MonitorIcon, match: '/account-autopublish-monitor' },
    { path: '/admin/dashboard/database-schema', label: 'База данных', icon: DatabaseIcon, match: '/database-schema' },
    { path: '/admin/dashboard/test', label: 'Тесты', icon: TestIcon, match: '/test' },
    { path: '/admin/dashboard/typescript-types', label: 'TypeScript', icon: TypeScriptIcon, match: '/typescript-types' },
    { path: '/admin/dashboard/mobx-store', label: 'MobX Store', icon: MobXIcon, match: '/mobx-store' },
    { path: '/user/dashboard', label: 'Пользователь', icon: UserIcon },
  ]

  return (
    <nav className="top-nav">
      {navItems.map((item) => {
        const isActive = item.match
          ? location.pathname.includes(item.match)
          : location.pathname === item.path
        return (
          <Link
            key={item.path}
            to={item.path}
            className={`top-nav-item ${isActive ? 'active' : ''}`}
          >
            <item.icon />
            <span>{item.label}</span>
          </Link>
        )
      })}
    </nav>
  )
}

function UserTopNav({ location, user }: { location: ReturnType<typeof useLocation>; user: any }): JSX.Element {
  const navItems = [
    { path: '/user/dashboard', label: 'Главная', icon: HomeIcon },
    { path: '/user/dashboard/objects', label: 'Объекты', icon: ObjectsIcon, match: '/objects', exclude: '/create' },
    { path: '/user/dashboard/objects/create', label: 'Создать', icon: CreateIcon, match: '/create' },
    { path: '/user/dashboard/telegram-accounts', label: 'Telegram', icon: TelegramIcon, match: '/telegram-accounts' },
  ]

  return (
    <nav className="top-nav">
      {navItems.map((item) => {
        let isActive = false
        if (item.match) {
          isActive = location.pathname.includes(item.match)
          if (item.exclude && location.pathname.includes(item.exclude)) {
            isActive = false
          }
        } else {
          isActive = location.pathname === item.path
        }
        return (
          <Link
            key={item.path}
            to={item.path}
            className={`top-nav-item ${isActive ? 'active' : ''}`}
          >
            <item.icon />
            <span>{item.label}</span>
          </Link>
        )
      })}
      {user?.web_role === 'admin' && (
        <Link to="/admin/dashboard" className="top-nav-item">
          <AdminIcon />
          <span>Админ</span>
        </Link>
      )}
    </nav>
  )
}

// Icon components
function HomeIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M3 10L9 4L9 9L17 9L17 11L9 11L9 16L3 10Z" fill="currentColor" />
    </svg>
  )
}

function ChatsIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path
        d="M2 5L10 9L18 5M2 15L10 19L18 15M2 10L10 14L18 10"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function ChatListsIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path
        d="M3 4H17M3 10H17M3 16H11"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function LogsIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M4 4H16V16H4V4Z" stroke="currentColor" strokeWidth="2" />
      <path d="M4 8H16M4 12H12" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}

function QueuesIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M2 4L10 8L18 4M2 12L10 16L18 12M2 8L10 12L18 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function MonitorIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M3 16H17M4 13L8 9L11 12L16 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function DatabaseIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M4 4H16V16H4V4Z" stroke="currentColor" strokeWidth="2" />
      <path d="M4 8H16M4 12H16" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}

function TestIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function TypeScriptIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M4 4H16V16H4V4Z" stroke="currentColor" strokeWidth="2" />
      <path d="M4 8H16M4 12H16" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}

function MobXIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M10 2L2 7L10 12L18 7L10 2Z" fill="currentColor" />
      <path d="M2 13L10 18L18 13M2 10L10 15L18 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function UserIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path
        d="M10 10C12.7614 10 15 7.76142 15 5C15 2.23858 12.7614 0 10 0C7.23858 0 5 2.23858 5 5C5 7.76142 7.23858 10 10 10Z"
        fill="currentColor"
      />
      <path
        d="M10 12C5.58172 12 2 14.2386 2 17V20H18V17C18 14.2386 14.4183 12 10 12Z"
        fill="currentColor"
      />
    </svg>
  )
}

function ObjectsIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path
        d="M2 5L10 9L18 5M2 15L10 19L18 15M2 10L10 14L18 10"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function CreateIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path
        d="M10 4V16M4 10H16"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  )
}

function TelegramIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path
        d="M10 2C8.89543 2 8 2.89543 8 4C8 5.10457 8.89543 6 10 6C11.1046 6 12 5.10457 12 4C12 2.89543 11.1046 2 10 2Z"
        fill="currentColor"
      />
      <path
        d="M5 16C5 13.7909 7.23858 12 10 12C12.7614 12 15 13.7909 15 16V18H5V16Z"
        fill="currentColor"
      />
    </svg>
  )
}

function AdminIcon(): JSX.Element {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M10 2L2 7L10 12L18 7L10 2Z" fill="currentColor" />
      <path
        d="M2 13L10 18L18 13M2 10L10 15L18 10"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}


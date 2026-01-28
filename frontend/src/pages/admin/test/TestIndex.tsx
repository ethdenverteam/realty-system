import { Link } from 'react-router-dom'
import Layout from '../../../components/Layout'
import { GlassCard } from '../../../components/GlassCard'
import './TestIndex.css'

/**
 * Навигация по тестам в админ панели
 */
export default function TestIndex(): JSX.Element {
  const tests = [
    {
      path: '/admin/dashboard/test',
      title: 'Тест компонентов',
      description: 'Тестирование карточек объектов и списков объектов',
      icon: '🧪',
    },
    {
      path: '/admin/dashboard/test/dropdown-test',
      title: 'Тест выпадающих меню',
      description: 'Демонстрация различных вариантов использования Dropdown и BottomNavDropdown',
      icon: '📋',
    },
  ]

  return (
    <Layout title="Тесты" isAdmin>
      <div className="test-index-page">
        <GlassCard>
          <h2>Навигация по тестам</h2>
          <p>Выберите тест для просмотра</p>
        </GlassCard>

        <div className="tests-grid">
          {tests.map((test) => (
            <Link key={test.path} to={test.path} className="test-card-link">
              <GlassCard className="test-card">
                <div className="test-icon">{test.icon}</div>
                <h3 className="test-title">{test.title}</h3>
                <p className="test-description">{test.description}</p>
              </GlassCard>
            </Link>
          ))}
        </div>
      </div>
    </Layout>
  )
}


import { Link } from 'react-router-dom'
import './Landing.css'

export default function Landing() {
  return (
    <div className="landing-page">
      <div className="landing-container">
        <div className="landing-content">
          <h1 className="landing-title">
            Система управления<br />
            публикациями недвижимости
          </h1>
          <p className="landing-description">
            Современная платформа для автоматизации публикации объявлений о недвижимости
            в Telegram каналах и группах. Управляйте объектами, настраивайте публикации
            и отслеживайте статистику в удобном веб-интерфейсе.
          </p>
          <div className="landing-features">
            <div className="feature">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M3 9L12 2L21 9V20C21 20.5304 20.7893 21.0391 20.4142 21.4142C20.0391 21.7893 19.5304 22 19 22H5C4.46957 22 3.96086 21.7893 3.58579 21.4142C3.21071 21.0391 3 20.5304 3 20V9Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M9 22V12H15V22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <h3>Управление объектами</h3>
              <p>Создавайте и редактируйте объявления о недвижимости</p>
            </div>
            <div className="feature">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <h3>Автоматические публикации</h3>
              <p>Настройте автоматическую публикацию в Telegram каналы</p>
            </div>
            <div className="feature">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M9 19C9 19.5304 9.21071 20.0391 9.58579 20.4142C9.96086 20.7893 10.4696 21 11 21H13C13.5304 21 14.0391 20.7893 14.4142 20.4142C14.7893 20.0391 15 19.5304 15 19V17H9V19Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M13 5H11C10.4696 5 9.96086 5.21071 9.58579 5.58579C9.21071 5.96086 9 6.46957 9 7V17H15V7C15 6.46957 14.7893 5.96086 14.4142 5.58579C14.0391 5.21071 13.5304 5 13 5Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <h3>Аналитика и статистика</h3>
              <p>Отслеживайте публикации и эффективность работы</p>
            </div>
          </div>
          <div className="landing-actions">
            <Link to="/login" className="btn btn-primary btn-large">
              Войти в систему
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}


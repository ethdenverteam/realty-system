import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import './QuickAccessObjects.css'

interface QuickAccessObjectsProps {
  objects?: Array<{ object_id: string | number; [key: string]: unknown }>
  onClose?: () => void
}

export default function QuickAccessObjects({ objects, onClose }: QuickAccessObjectsProps): JSX.Element {
  const navigate = useNavigate()
  const [isOpen, setIsOpen] = useState(true)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent): void => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        if (onClose) {
          onClose()
        }
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen, onClose])

  const handleObjectClick = (objectId: string | number): void => {
    navigate(`/user/dashboard/objects/${objectId}`)
    setIsOpen(false)
    if (onClose) {
      onClose()
    }
  }

  if (!objects || objects.length === 0) {
    return (
      <div className="quick-access-objects-empty">
        <p>Нет объектов</p>
      </div>
    )
  }

  return (
    <div className="quick-access-objects" ref={menuRef}>
      <div className="quick-access-header">
        <span>Выберите объект</span>
      </div>
      <div className="quick-access-list">
        {objects.map((obj) => (
          <button
            key={obj.object_id}
            className="quick-access-item"
            onClick={() => handleObjectClick(obj.object_id)}
          >
            {String(obj.object_id)}
          </button>
        ))}
      </div>
    </div>
  )
}


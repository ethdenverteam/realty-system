import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

type Theme = 'dark' | 'light' | 'dark-lines' | 'light-lines' | 'dark-random-lines'

interface ThemeContextValue {
  theme: Theme
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

export function ThemeProvider({ children }: { children: ReactNode }): JSX.Element {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme')
    return saved === 'light' || saved === 'dark' || saved === 'dark-lines' || saved === 'light-lines' || saved === 'dark-random-lines'
      ? (saved as Theme)
      : 'dark'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
    
    // Генерация случайных линий для темы dark-random-lines
    if (theme === 'dark-random-lines') {
      generateRandomLines()
    }
  }, [theme])

  const generateRandomLines = (): void => {
    const numLines = 15 + Math.floor(Math.random() * 20) // 15-35 линий
    const lines: string[] = []
    const colors = [
      'rgba(255, 23, 68, 0.4)',
      'rgba(0, 170, 255, 0.4)',
      'rgba(120, 255, 120, 0.4)',
      'rgba(255, 120, 200, 0.4)',
      'rgba(120, 120, 255, 0.4)',
      'rgba(255, 200, 0, 0.4)',
    ]
    
    for (let i = 0; i < numLines; i++) {
      const angle = Math.random() * 360
      const x1 = Math.random() * 100
      const y1 = Math.random() * 100
      const length = 20 + Math.random() * 30
      const x2 = x1 + length * Math.cos((angle * Math.PI) / 180)
      const y2 = y1 + length * Math.sin((angle * Math.PI) / 180)
      const color = colors[Math.floor(Math.random() * colors.length)]
      const width = 1 + Math.random() * 2
      
      lines.push(
        `linear-gradient(${angle}deg, transparent ${x1}% ${y1}%, ${color} ${x1}% ${y1}%, ${color} ${x2}% ${y2}%, transparent ${x2}% ${y2}%)`
      )
    }
    
    document.documentElement.style.setProperty('--random-lines-bg', lines.join(', '))
  }

  const toggleTheme = () => {
    setTheme((prev) => {
      if (prev === 'dark') return 'dark-lines'
      if (prev === 'dark-lines') return 'light'
      if (prev === 'light') return 'light-lines'
      if (prev === 'light-lines') return 'dark-random-lines'
      return 'dark'
    })
  }

  const value: ThemeContextValue = useMemo(() => ({ theme, toggleTheme }), [theme])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}



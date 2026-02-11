import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

type Theme = 'dark' | 'light' | 'dark-lines' | 'light-lines' | 'dark-random-lines'

interface ThemeContextValue {
  theme: Theme
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
  availableThemes: { value: Theme; label: string }[]
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

export function ThemeProvider({ children }: { children: ReactNode }): JSX.Element {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme')
    return saved === 'light' || saved === 'dark' || saved === 'dark-lines' || saved === 'light-lines' || saved === 'dark-random-lines'
      ? (saved as Theme)
      : 'dark-lines' // По умолчанию тема с линиями
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
    
    // Генерация случайных линий для темы dark-random-lines
    if (theme === 'dark-random-lines') {
      generateRandomLines()
    }
    
    // Генерация случайного градиента для темы dark-lines
    if (theme === 'dark-lines') {
      generateRandomGradient()
    }

    // Генерация случайного тоннера стекла для всех тем
    generateRandomGlassTint()
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

  const generateRandomGradient = (): void => {
    // Генерируем случайные позиции и цвета для градиента
    const numGradients = 2 + Math.floor(Math.random() * 3) // 2-4 градиента
    const gradients: string[] = []
    const colors = [
      { r: 255, g: 0, b: 120 },
      { r: 0, g: 170, b: 255 },
      { r: 120, g: 255, b: 120 },
      { r: 255, g: 120, b: 200 },
      { r: 120, g: 120, b: 255 },
      { r: 255, g: 200, b: 0 },
      { r: 255, g: 23, b: 68 },
    ]
    
    for (let i = 0; i < numGradients; i++) {
      const x = Math.random() * 100
      const y = Math.random() * 100
      const size = 20 + Math.random() * 40
      const color = colors[Math.floor(Math.random() * colors.length)]
      const opacity = 0.15 + Math.random() * 0.15 // 0.15-0.3
      
      gradients.push(
        `radial-gradient(circle at ${x}% ${y}%, rgba(${color.r}, ${color.g}, ${color.b}, ${opacity}), transparent ${size}%)`
      )
    }
    
    const gradientString = gradients.join(', ') + ', #000000'
    document.documentElement.style.setProperty('--random-gradient-bg', gradientString)
  }

  const generateRandomGlassTint = (): void => {
    // Рандомный тон стекла в диапазоне от красных до синих оттенков
    // Генерируем цвет в формате rgba для совместимости с backdrop-filter
    const hue = Math.floor(Math.random() * 241) // 0-240 (от красного до синего)
    const saturation = 70
    const lightness = 80
    const alpha = 0.08 // прозрачность для backdrop-filter (примерно как #rrggbb14)
    
    // Конвертируем HSL в RGB
    const h = hue / 360
    const s = saturation / 100
    const l = lightness / 100
    
    let r: number, g: number, b: number
    
    if (s === 0) {
      r = g = b = l // achromatic
    } else {
      const hue2rgb = (p: number, q: number, t: number): number => {
        if (t < 0) t += 1
        if (t > 1) t -= 1
        if (t < 1/6) return p + (q - p) * 6 * t
        if (t < 1/2) return q
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6
        return p
      }
      
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s
      const p = 2 * l - q
      r = hue2rgb(p, q, h + 1/3)
      g = hue2rgb(p, q, h)
      b = hue2rgb(p, q, h - 1/3)
    }
    
    // Конвертируем в RGB значения (0-255)
    const rInt = Math.round(r * 255)
    const gInt = Math.round(g * 255)
    const bInt = Math.round(b * 255)
    
    // Формат rgba для совместимости с backdrop-filter
    const glassColorRgba = `rgba(${rInt}, ${gInt}, ${bInt}, ${alpha})`
    
    // Также создаем hex версию для справки (без альфы, т.к. альфа в rgba)
    const rHex = rInt.toString(16).padStart(2, '0')
    const gHex = gInt.toString(16).padStart(2, '0')
    const bHex = bInt.toString(16).padStart(2, '0')
    const alphaHex = Math.round(alpha * 255).toString(16).padStart(2, '0')
    const glassColorHex = `#${rHex}${gHex}${bHex}${alphaHex}` // для справки

    // Инвертированный тон для иконок (противоположный hue)
    const invertedHue = (hue + 180) % 360
    const iconLightness = 30 // иконка темнее, чтобы быть читаемой
    const iconH = invertedHue / 360
    const iconS = saturation / 100
    const iconL = iconLightness / 100
    
    let iconR: number, iconG: number, iconB: number
    
    if (iconS === 0) {
      iconR = iconG = iconB = iconL
    } else {
      const hue2rgb = (p: number, q: number, t: number): number => {
        if (t < 0) t += 1
        if (t > 1) t -= 1
        if (t < 1/6) return p + (q - p) * 6 * t
        if (t < 1/2) return q
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6
        return p
      }
      
      const q = iconL < 0.5 ? iconL * (1 + iconS) : iconL + iconS - iconL * iconS
      const p = 2 * iconL - q
      iconR = hue2rgb(p, q, iconH + 1/3)
      iconG = hue2rgb(p, q, iconH)
      iconB = hue2rgb(p, q, iconH - 1/3)
    }
    
    const iconRHex = Math.round(iconR * 255).toString(16).padStart(2, '0')
    const iconGHex = Math.round(iconG * 255).toString(16).padStart(2, '0')
    const iconBHex = Math.round(iconB * 255).toString(16).padStart(2, '0')
    const iconColorHex = `#${iconRHex}${iconGHex}${iconBHex}`

    // Один цвет для всех стекол и иконок до перезагрузки страницы / смены темы
    // Используем rgba формат для совместимости с backdrop-filter
    document.documentElement.style.setProperty('--glass-bg-flex', glassColorRgba)
    document.documentElement.style.setProperty('--glass-icon-color', iconColorHex)
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

  const availableThemes: { value: Theme; label: string }[] = useMemo(
    () => [
      { value: 'dark', label: 'Темная' },
      { value: 'dark-lines', label: 'Темная с линиями' },
      { value: 'light', label: 'Светлая' },
      { value: 'light-lines', label: 'Светлая с линиями' },
      { value: 'dark-random-lines', label: 'Темная со случайными линиями' },
    ],
    []
  )

  const value: ThemeContextValue = useMemo(
    () => ({ theme, toggleTheme, setTheme, availableThemes }),
    [theme, availableThemes]
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}



import { makeAutoObservable } from 'mobx'

class UiStore {
  // Включен ли эффект стекла для демо‑компонентов
  glassEnabled = true

  // Демонстрационный фильтр района (как на Objects.tsx), но в MobX
  districtFilter = ''

  // Состояние для стеклянной кнопки
  glassButtonClicks = 0
  glassMode: 'default' | 'highlighted' = 'default'

  constructor() {
    makeAutoObservable(this)
  }

  setGlassEnabled(value: boolean): void {
    this.glassEnabled = value
  }

  setDistrictFilter(value: string): void {
    this.districtFilter = value
  }

  incrementGlassButton(): void {
    this.glassButtonClicks += 1
  }

  setGlassMode(mode: 'default' | 'highlighted'): void {
    this.glassMode = mode
  }
}

export const uiStore = new UiStore()

import { makeAutoObservable } from 'mobx'

/**
 * UIStore: глобальное состояние для демо стеклянных компонентов и фильтров
 */
class UIStore {
  // Демонстрационное состояние фильтра (аналог districtFilter)
  districtFilter = ''

  // Состояние для демо карточки (например, режим отображения)
  glassMode: 'default' | 'highlighted' = 'default'

  // Счётчик нажатий на стеклянную кнопку
  glassButtonClicks = 0

  constructor() {
    makeAutoObservable(this)
  }

  setDistrictFilter(value: string): void {
    this.districtFilter = value
  }

  setGlassMode(mode: 'default' | 'highlighted'): void {
    this.glassMode = mode
  }

  incrementGlassButton(): void {
    this.glassButtonClicks += 1
  }
}

export const uiStore = new UIStore()



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

  // Выбранный пункт меню навигации (для стеклянной кнопки "меню")
  menuChoice = ''

  // Выбранный ID объекта (для стеклянной кнопки "объекты")
  selectedObjectId = ''

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

  setMenuChoice(value: string): void {
    this.menuChoice = value
  }

  setSelectedObjectId(value: string): void {
    this.selectedObjectId = value
  }
}

export const uiStore = new UIStore()



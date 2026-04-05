import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export type Theme = 'dark' | 'light' | 'system'

export interface SettingsContextType {
  theme: Theme
  setTheme: (theme: Theme) => void
  defaultCharacterId: number | null
  setDefaultCharacterId: (characterId: number | null) => void
  refreshInterval: number
  setRefreshInterval: (interval: number) => void
  autoRefresh: boolean
  setAutoRefresh: (enabled: boolean) => void
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

const SETTINGS_KEY = 'eve-copilot-settings'

interface StoredSettings {
  theme: Theme
  defaultCharacterId: number | null
  refreshInterval: number
  autoRefresh: boolean
}

const defaultSettings: StoredSettings = {
  theme: 'dark',
  defaultCharacterId: null,
  refreshInterval: 5, // minutes
  autoRefresh: true,
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<StoredSettings>(() => {
    const stored = localStorage.getItem(SETTINGS_KEY)
    if (stored) {
      try {
        return { ...defaultSettings, ...JSON.parse(stored) }
      } catch {
        return defaultSettings
      }
    }
    return defaultSettings
  })

  // Persist settings to localStorage
  useEffect(() => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
  }, [settings])

  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement

    if (settings.theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      root.classList.toggle('dark', systemTheme === 'dark')
    } else {
      root.classList.toggle('dark', settings.theme === 'dark')
    }
  }, [settings.theme])

  const setTheme = (theme: Theme) => {
    setSettings((prev) => ({ ...prev, theme }))
  }

  const setDefaultCharacterId = (characterId: number | null) => {
    setSettings((prev) => ({ ...prev, defaultCharacterId: characterId }))
  }

  const setRefreshInterval = (interval: number) => {
    setSettings((prev) => ({ ...prev, refreshInterval: interval }))
  }

  const setAutoRefresh = (enabled: boolean) => {
    setSettings((prev) => ({ ...prev, autoRefresh: enabled }))
  }

  return (
    <SettingsContext.Provider
      value={{
        theme: settings.theme,
        setTheme,
        defaultCharacterId: settings.defaultCharacterId,
        setDefaultCharacterId,
        refreshInterval: settings.refreshInterval,
        setRefreshInterval,
        autoRefresh: settings.autoRefresh,
        setAutoRefresh,
      }}
    >
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider')
  }
  return context
}

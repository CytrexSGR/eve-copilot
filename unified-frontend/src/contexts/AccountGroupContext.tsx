import { createContext, useContext, useState, ReactNode } from 'react'

export interface AccountGroup {
  id: string
  name: string
  characterIds: number[]
}

type ViewMode = 'single' | 'group' | 'all'

interface AccountGroupContextType {
  groups: AccountGroup[]
  selectedGroup: AccountGroup | null
  setSelectedGroupId: (groupId: string | null) => void
  viewMode: ViewMode
  setViewMode: (mode: ViewMode) => void
}

const AccountGroupContext = createContext<AccountGroupContextType | undefined>(undefined)

export function AccountGroupProvider({ children }: { children: ReactNode }) {
  const [groups] = useState<AccountGroup[]>([])
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('single')

  const selectedGroup = groups.find((g) => g.id === selectedGroupId) ?? null

  return (
    <AccountGroupContext.Provider
      value={{
        groups,
        selectedGroup,
        setSelectedGroupId,
        viewMode,
        setViewMode,
      }}
    >
      {children}
    </AccountGroupContext.Provider>
  )
}

export function useAccountGroupContext() {
  const context = useContext(AccountGroupContext)
  if (context === undefined) {
    throw new Error('useAccountGroupContext must be used within an AccountGroupProvider')
  }
  return context
}

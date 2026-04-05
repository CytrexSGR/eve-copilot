import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useCharacters } from '@/hooks/useCharacters'
import type { Character } from '@/types/character'

interface CharacterContextType {
  characters: Character[]
  selectedCharacter: Character | null
  setSelectedCharacter: (character: Character) => void
  isLoading: boolean
}

const CharacterContext = createContext<CharacterContextType | undefined>(undefined)

export function CharacterProvider({ children }: { children: ReactNode }) {
  const { data, isLoading } = useCharacters()
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null)

  const characters = data?.characters ?? []

  // Auto-select first character if none selected
  useEffect(() => {
    if (!selectedCharacter && characters.length > 0) {
      // Try to load from localStorage first
      const savedId = localStorage.getItem('selectedCharacterId')
      if (savedId) {
        const saved = characters.find((c) => c.character_id === parseInt(savedId, 10))
        if (saved) {
          setSelectedCharacter(saved)
          return
        }
      }
      // Fall back to first character
      setSelectedCharacter(characters[0])
    }
  }, [characters, selectedCharacter])

  // Persist selection
  const handleSetSelectedCharacter = (character: Character) => {
    setSelectedCharacter(character)
    localStorage.setItem('selectedCharacterId', character.character_id.toString())
  }

  return (
    <CharacterContext.Provider
      value={{
        characters,
        selectedCharacter,
        setSelectedCharacter: handleSetSelectedCharacter,
        isLoading,
      }}
    >
      {children}
    </CharacterContext.Provider>
  )
}

export function useCharacterContext() {
  const context = useContext(CharacterContext)
  if (context === undefined) {
    throw new Error('useCharacterContext must be used within a CharacterProvider')
  }
  return context
}

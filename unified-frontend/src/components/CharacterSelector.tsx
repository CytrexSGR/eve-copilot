import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { useAccountGroupContext } from '@/contexts/AccountGroupContext'
import { ChevronDown, Check, Users, User } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'

export function CharacterSelector() {
  const { characters, selectedCharacter, setSelectedCharacter, isLoading } = useCharacterContext()
  const {
    groups,
    selectedGroup,
    setSelectedGroupId,
    viewMode,
    setViewMode,
  } = useAccountGroupContext()

  if (isLoading) {
    return <Skeleton className="h-10 w-40" />
  }

  if (!selectedCharacter) {
    return null
  }

  const portraitUrl = `https://images.evetech.net/characters/${selectedCharacter.character_id}/portrait?size=64`

  // Current selection display
  const isGroupView = viewMode === 'group' && selectedGroup
  const displayName = isGroupView ? selectedGroup.name : selectedCharacter.character_name
  const memberCount = selectedGroup?.members.length ?? 0

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="flex items-center gap-2">
          {isGroupView ? (
            <>
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
                <Users className="h-4 w-4 text-primary" />
              </div>
              <div className="flex flex-col items-start">
                <span className="text-sm font-medium">{displayName}</span>
                <span className="text-xs text-muted-foreground">{memberCount} characters</span>
              </div>
            </>
          ) : (
            <>
              <Avatar className="h-8 w-8">
                <AvatarImage src={portraitUrl} alt={selectedCharacter.character_name} />
                <AvatarFallback>
                  {selectedCharacter.character_name.slice(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <span className="text-sm font-medium">{selectedCharacter.character_name}</span>
            </>
          )}
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        {/* Characters Section */}
        <DropdownMenuLabel className="flex items-center gap-2">
          <User className="h-4 w-4" />
          Characters
        </DropdownMenuLabel>
        {characters.map((char) => {
          const isSelected =
            viewMode === 'single' && char.character_id === selectedCharacter.character_id
          return (
            <DropdownMenuItem
              key={char.character_id}
              onClick={() => {
                setSelectedCharacter(char)
                setViewMode('single')
                setSelectedGroupId(null)
              }}
              className="flex items-center gap-2"
            >
              <Avatar className="h-6 w-6">
                <AvatarImage
                  src={`https://images.evetech.net/characters/${char.character_id}/portrait?size=64`}
                  alt={char.character_name}
                />
                <AvatarFallback>{char.character_name.slice(0, 2).toUpperCase()}</AvatarFallback>
              </Avatar>
              <span className="flex-1">{char.character_name}</span>
              {isSelected && <Check className="h-4 w-4" />}
            </DropdownMenuItem>
          )
        })}

        {/* Groups Section (if any groups exist) */}
        {groups.length > 0 && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Account Groups
            </DropdownMenuLabel>
            {groups.map((group) => {
              const isSelected = viewMode === 'group' && selectedGroup?.id === group.id
              return (
                <DropdownMenuItem
                  key={group.id}
                  onClick={() => {
                    setSelectedGroupId(group.id)
                  }}
                  className="flex items-center gap-2"
                >
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10">
                    <Users className="h-3 w-3 text-primary" />
                  </div>
                  <span className="flex-1">{group.name}</span>
                  {isSelected && <Check className="h-4 w-4" />}
                </DropdownMenuItem>
              )
            })}
          </>
        )}

        {/* Quick "All Characters" option */}
        {characters.length > 1 && groups.length === 0 && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => {
                setViewMode('group')
                setSelectedGroupId(null)
              }}
              className="flex items-center gap-2"
            >
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10">
                <Users className="h-3 w-3 text-primary" />
              </div>
              <span className="flex-1">All Characters</span>
              <Badge variant="secondary" className="text-xs">
                {characters.length}
              </Badge>
              {viewMode === 'group' && !selectedGroup && <Check className="h-4 w-4" />}
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

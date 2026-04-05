import { Header } from '@/components/layout/Header'
import { CharacterCard, CharacterCardSkeleton } from '@/components/dashboard/CharacterCard'
import { useCharacters } from '@/hooks/useCharacters'
import { useCharacterSummaries } from '@/hooks/useCharacterSummary'
import { AlertTriangle, Users, UserPlus, Building2, Wallet } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { charactersApi } from '@/api/characters'
import { formatISK } from '@/lib/utils'

export function Dashboard() {
  const { data: charactersData, isLoading: isLoadingCharacters, isError: isCharactersError } = useCharacters()

  const characters = charactersData?.characters ?? []
  const { data: summaries, corporations, isLoading: isLoadingSummaries, refetch } = useCharacterSummaries(characters)

  const isLoading = isLoadingCharacters || isLoadingSummaries

  if (isCharactersError) {
    return (
      <div>
        <Header title="Dashboard" subtitle="Overview of all characters" />
        <div className="p-6">
          <Card className="border-destructive">
            <CardContent className="flex items-center gap-4 p-6">
              <AlertTriangle className="h-8 w-8 text-destructive" />
              <div>
                <h3 className="font-semibold">Failed to load characters</h3>
                <p className="text-sm text-muted-foreground">
                  Make sure the backend is running and characters are authenticated.
                </p>
              </div>
              <Button onClick={() => window.location.reload()} className="ml-auto">
                Retry
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div>
      <Header
        title="Dashboard"
        subtitle={`${characters.length} characters`}
        onRefresh={refetch}
        isRefreshing={isLoading}
      />

      <div className="p-6">
        {/* Stats Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card>
            <CardContent className="flex items-center gap-4 p-6">
              <Users className="h-8 w-8 text-primary" />
              <div>
                <p className="text-2xl font-bold">{characters.length}</p>
                <p className="text-sm text-muted-foreground">Characters</p>
              </div>
            </CardContent>
          </Card>
          <Card className="hover:border-primary/50 transition-colors cursor-pointer" onClick={() => charactersApi.addCharacter()}>
            <CardContent className="flex items-center gap-4 p-6">
              <UserPlus className="h-8 w-8 text-primary" />
              <div>
                <p className="text-lg font-semibold">Add Character</p>
                <p className="text-sm text-muted-foreground">Login via EVE SSO</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-4 p-6">
              <Building2 className="h-8 w-8 text-primary" />
              <div>
                <p className="text-2xl font-bold">{corporations.length}</p>
                <p className="text-sm text-muted-foreground">Corporations</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Corporations Section */}
        {corporations.length > 0 && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Corporations
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {corporations.map((corp) => {
                const corpMembers = summaries.filter(s => s.corporation_id === corp.corporation_id)
                const totalWallet = corpMembers.reduce((sum, m) => sum + m.wallet_balance, 0)
                return (
                  <Card key={corp.corporation_id} className="hover:border-primary/50 transition-colors">
                    <CardContent className="flex items-center gap-4 p-4">
                      <img
                        src={`https://images.evetech.net/corporations/${corp.corporation_id}/logo?size=64`}
                        alt={corp.name}
                        className="h-12 w-12 rounded bg-black"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold truncate">[{corp.ticker}] {corp.name}</p>
                        <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                          <span className="flex items-center gap-1">
                            <Users className="h-3.5 w-3.5" />
                            {corpMembers.length}
                          </span>
                          <span className="flex items-center gap-1 text-primary">
                            <Wallet className="h-3.5 w-3.5" />
                            {formatISK(totalWallet)}
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </div>
        )}

        {/* Character Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {isLoading ? (
            <>
              <CharacterCardSkeleton />
              <CharacterCardSkeleton />
              <CharacterCardSkeleton />
            </>
          ) : (
            summaries.map((character) => (
              <CharacterCard key={character.character_id} character={character} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}

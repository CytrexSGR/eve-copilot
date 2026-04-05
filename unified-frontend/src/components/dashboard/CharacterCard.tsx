import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { SkillQueueProgress } from './SkillQueueProgress'
import { formatISK, formatSP } from '@/lib/utils'
import type { CharacterSummary } from '@/types/character'
import { Wallet, Brain, MapPin, Ship, Factory, Building2 } from 'lucide-react'

interface CharacterCardProps {
  character: CharacterSummary
}

export function CharacterCard({ character }: CharacterCardProps) {
  return (
    <Link to={`/character/${character.character_id}`}>
      <Card className="hover:border-primary/50 transition-colors cursor-pointer">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <Avatar className="h-12 w-12">
            <AvatarImage src={character.portrait_url} alt={character.character_name} />
            <AvatarFallback>{character.character_name.slice(0, 2).toUpperCase()}</AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold truncate">{character.character_name}</h3>
            {character.corporation_name && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-0.5">
                <img
                  src={`https://images.evetech.net/corporations/${character.corporation_id}/logo?size=32`}
                  alt=""
                  className="h-4 w-4 rounded"
                />
                <span className="truncate">[{character.corporation_ticker}] {character.corporation_name}</span>
              </div>
            )}
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className="text-xs">
                <Wallet className="h-3 w-3 mr-1" />
                {formatISK(character.wallet_balance)}
              </Badge>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Location & Ship */}
        {(character.location || character.ship) && (
          <div className="space-y-1.5 text-sm">
            {character.location && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="truncate">{character.location.solar_system_name}</span>
              </div>
            )}
            {character.ship && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Ship className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="truncate">{character.ship.ship_name}</span>
              </div>
            )}
          </div>
        )}

        {/* Skill Points */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Brain className="h-4 w-4" />
            <span>Skill Points</span>
          </div>
          <span className="font-medium">{formatSP(character.total_sp)}</span>
        </div>

        {character.unallocated_sp > 0 && (
          <div className="text-sm text-success">
            +{formatSP(character.unallocated_sp)} unallocated
          </div>
        )}

        {/* Industry Jobs */}
        {(character.active_industry_jobs ?? 0) > 0 && (
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Factory className="h-4 w-4" />
              <span>Industry Jobs</span>
            </div>
            <Badge variant="secondary" className="text-xs">
              {character.active_industry_jobs} active
            </Badge>
          </div>
        )}

        {/* Skill Queue */}
        <div className="pt-2 border-t border-border">
          <SkillQueueProgress
            currentSkill={character.current_skill}
            skillsInQueue={character.skills_in_queue}
          />
        </div>
      </CardContent>
    </Card>
    </Link>
  )
}

export function CharacterCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <Skeleton className="h-12 w-12 rounded-full" />
          <div className="flex-1">
            <Skeleton className="h-5 w-32 mb-2" />
            <Skeleton className="h-5 w-24" />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-8 w-full" />
      </CardContent>
    </Card>
  )
}

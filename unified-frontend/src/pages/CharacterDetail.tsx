import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { SkillQueueProgress } from '@/components/dashboard/SkillQueueProgress'
import { AssetsTab } from '@/components/character/AssetsTab'
import {
  useCharacterWallet,
  useCharacterSkills,
  useCharacterSkillQueue,
  useCharacterInfo,
} from '@/hooks/useCharacters'
import { formatISK, formatSP, formatRelativeTime } from '@/lib/utils'
import { ArrowLeft, Wallet, Brain, Clock, GraduationCap, Info, User, Package } from 'lucide-react'

export function CharacterDetail() {
  const { characterId } = useParams<{ characterId: string }>()
  const id = parseInt(characterId ?? '0', 10)
  const [activeTab, setActiveTab] = useState<'overview' | 'assets'>('overview')

  const { data: wallet, isLoading: isLoadingWallet } = useCharacterWallet(id)
  const { data: skills, isLoading: isLoadingSkills } = useCharacterSkills(id)
  const { data: queue, isLoading: isLoadingQueue } = useCharacterSkillQueue(id)
  const { data: info, isLoading: isLoadingInfo } = useCharacterInfo(id)

  const portraitUrl = `https://images.evetech.net/characters/${id}/portrait?size=256`

  const currentSkill = queue?.queue?.find((item) => {
    const finishDate = new Date(item.finish_date)
    return finishDate > new Date()
  })

  return (
    <div>
      <Header title={info?.name ?? 'Character'} subtitle="Character Details" />

      <div className="p-6">
        {/* Back Button */}
        <Link to="/">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
        </Link>

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6">
          <Button
            variant={activeTab === 'overview' ? 'default' : 'ghost'}
            onClick={() => setActiveTab('overview')}
          >
            <User className="h-4 w-4 mr-2" />
            Overview
          </Button>
          <Button
            variant={activeTab === 'assets' ? 'default' : 'ghost'}
            onClick={() => setActiveTab('assets')}
          >
            <Package className="h-4 w-4 mr-2" />
            Assets
          </Button>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
        <>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Character Info Card */}
          <Card className="lg:col-span-1">
            <CardContent className="pt-6">
              <div className="flex flex-col items-center text-center">
                <Avatar className="h-32 w-32 mb-4">
                  <AvatarImage src={portraitUrl} alt={info?.name} />
                  <AvatarFallback>{info?.name?.slice(0, 2).toUpperCase()}</AvatarFallback>
                </Avatar>

                {isLoadingInfo ? (
                  <Skeleton className="h-6 w-32 mb-2" />
                ) : (
                  <h2 className="text-xl font-bold mb-2">{info?.name}</h2>
                )}

                {info?.security_status !== undefined && (
                  <Badge variant={info.security_status >= 0 ? 'success' : 'destructive'}>
                    Security: {info.security_status.toFixed(2)}
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Stats Cards */}
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Wallet */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Wallet className="h-4 w-4" />
                  Wallet Balance
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isLoadingWallet ? (
                  <Skeleton className="h-8 w-32" />
                ) : (
                  <p className="text-2xl font-bold">{formatISK(wallet?.balance ?? 0)}</p>
                )}
              </CardContent>
            </Card>

            {/* Skill Points */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Brain className="h-4 w-4" />
                  Skill Points
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isLoadingSkills ? (
                  <Skeleton className="h-8 w-32" />
                ) : (
                  <>
                    <p className="text-2xl font-bold">{formatSP(skills?.total_sp ?? 0)}</p>
                    {(skills?.unallocated_sp ?? 0) > 0 && (
                      <p className="text-sm text-success">
                        +{formatSP(skills?.unallocated_sp ?? 0)} unallocated
                      </p>
                    )}
                  </>
                )}
              </CardContent>
            </Card>

            {/* Current Training */}
            <Card className="md:col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <GraduationCap className="h-4 w-4" />
                  Skill Training
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isLoadingQueue ? (
                  <Skeleton className="h-16 w-full" />
                ) : (
                  <SkillQueueProgress
                    currentSkill={currentSkill}
                    skillsInQueue={queue?.queue?.length ?? 0}
                  />
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Skill Queue List */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Skill Queue ({queue?.queue?.length ?? 0} skills)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TooltipProvider>
              {isLoadingQueue ? (
                <div className="space-y-2">
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-20 w-full" />
                </div>
              ) : queue?.queue?.length === 0 ? (
                <p className="text-muted-foreground">No skills in queue</p>
              ) : (
                <div className="space-y-3">
                  {queue?.queue?.map((skill, index) => {
                    const finishDate = new Date(skill.finish_date)
                    const isComplete = finishDate <= new Date()
                    const isCurrentlyTraining = index === 0 && !isComplete

                    return (
                      <div
                        key={`${skill.skill_id}-${skill.finished_level}`}
                        className={`p-4 rounded-lg border ${
                          isCurrentlyTraining
                            ? 'border-primary/50 bg-primary/5'
                            : 'border-border bg-secondary/30'
                        }`}
                      >
                        {/* Header row */}
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-3">
                            <span className="text-muted-foreground w-6 text-sm">
                              {index + 1}.
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="font-medium">
                                {skill.skill_name}
                              </span>
                              <Badge variant="outline" className="text-xs">
                                Level {skill.finished_level}
                              </Badge>
                              {skill.skill_description && (
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                                  </TooltipTrigger>
                                  <TooltipContent side="right" className="max-w-sm">
                                    <p className="text-sm whitespace-pre-wrap">
                                      {skill.skill_description}
                                    </p>
                                  </TooltipContent>
                                </Tooltip>
                              )}
                            </div>
                          </div>
                          <div className="text-right">
                            {isComplete ? (
                              <Badge variant="success">Complete</Badge>
                            ) : isCurrentlyTraining ? (
                              <Badge variant="default">Training</Badge>
                            ) : (
                              <span className="text-sm text-muted-foreground">
                                {formatRelativeTime(skill.finish_date)}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* SP Progress row */}
                        <div className="ml-9">
                          <div className="flex items-center justify-between text-sm mb-1">
                            <span className="text-muted-foreground">
                              {formatSP(skill.level_end_sp - skill.sp_remaining)} /{' '}
                              {formatSP(skill.level_end_sp)}
                            </span>
                            <span className="text-muted-foreground">
                              {formatSP(skill.sp_remaining)} remaining
                            </span>
                          </div>

                          {/* Progress bar */}
                          <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                            <div
                              className={`h-full transition-all duration-300 ${
                                isComplete
                                  ? 'bg-success'
                                  : isCurrentlyTraining
                                  ? 'bg-primary'
                                  : 'bg-muted-foreground/50'
                              }`}
                              style={{ width: `${Math.min(100, skill.training_progress)}%` }}
                            />
                          </div>

                          <div className="flex items-center justify-between text-xs mt-1">
                            <span className="text-muted-foreground">
                              {skill.training_progress.toFixed(1)}% complete
                            </span>
                            {!isComplete && skill.finish_date && (
                              <span className="text-muted-foreground">
                                Finishes: {new Date(skill.finish_date).toLocaleDateString()}{' '}
                                {new Date(skill.finish_date).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })}
                              </span>
                            )}
                          </div>

                          {/* Unlocks at this level */}
                          {skill.unlocks_at_level && skill.unlocks_at_level.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-border/50">
                              <p className="text-xs font-medium text-muted-foreground mb-2">
                                Unlocks at Level {skill.finished_level}:
                              </p>
                              <div className="flex flex-wrap gap-1.5">
                                {skill.unlocks_at_level.map((unlock) => (
                                  <Tooltip key={unlock.type_id}>
                                    <TooltipTrigger asChild>
                                      <Badge
                                        variant="secondary"
                                        className="text-xs cursor-help"
                                      >
                                        {unlock.type_name}
                                      </Badge>
                                    </TooltipTrigger>
                                    <TooltipContent side="top">
                                      <p className="text-sm">
                                        {unlock.group_name} ({unlock.category_name})
                                      </p>
                                    </TooltipContent>
                                  </Tooltip>
                                ))}
                                {skill.unlocks_at_level.length >= 15 && (
                                  <Badge variant="outline" className="text-xs">
                                    +more...
                                  </Badge>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </TooltipProvider>
          </CardContent>
        </Card>
        </>
        )}

        {/* Assets Tab */}
        {activeTab === 'assets' && <AssetsTab characterId={id} />}
      </div>
    </div>
  )
}

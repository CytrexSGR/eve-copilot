import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { useSettings } from '@/contexts/SettingsContext'
import { useCharacters } from '@/hooks/useCharacters'
import { Palette, Database, User } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Theme selector component
 */
function ThemeSelector() {
  const { theme, setTheme } = useSettings()

  const themes = [
    { value: 'dark' as const, label: 'Dark', description: 'EVE Online inspired dark theme' },
    { value: 'light' as const, label: 'Light', description: 'Light theme (coming soon)', disabled: true },
    { value: 'system' as const, label: 'System', description: 'Follow system preference', disabled: true },
  ]

  return (
    <div className="space-y-3">
      {themes.map((t) => (
        <button
          key={t.value}
          onClick={() => !t.disabled && setTheme(t.value)}
          disabled={t.disabled}
          className={cn(
            'w-full text-left p-4 rounded-lg border transition-colors',
            theme === t.value
              ? 'border-primary bg-primary/10'
              : 'border-border hover:bg-secondary/30',
            t.disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium">{t.label}</span>
                {theme === t.value && (
                  <Badge variant="default" className="text-xs">
                    Active
                  </Badge>
                )}
                {t.disabled && (
                  <Badge variant="outline" className="text-xs">
                    Coming Soon
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground mt-1">{t.description}</p>
            </div>
            <div
              className={cn(
                'w-4 h-4 rounded-full border-2',
                theme === t.value ? 'border-primary bg-primary' : 'border-border'
              )}
            />
          </div>
        </button>
      ))}
    </div>
  )
}

/**
 * Default character selector
 */
function DefaultCharacterSelector() {
  const { defaultCharacterId, setDefaultCharacterId } = useSettings()
  const { data } = useCharacters()
  const characters = data?.characters ?? []

  return (
    <div className="space-y-3">
      <button
        onClick={() => setDefaultCharacterId(null)}
        className={cn(
          'w-full text-left p-4 rounded-lg border transition-colors',
          defaultCharacterId === null
            ? 'border-primary bg-primary/10'
            : 'border-border hover:bg-secondary/30'
        )}
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium">No Default</span>
              {defaultCharacterId === null && (
                <Badge variant="default" className="text-xs">
                  Active
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Always show all characters
            </p>
          </div>
          <div
            className={cn(
              'w-4 h-4 rounded-full border-2',
              defaultCharacterId === null ? 'border-primary bg-primary' : 'border-border'
            )}
          />
        </div>
      </button>

      {characters.map((char) => (
        <button
          key={char.character_id}
          onClick={() => setDefaultCharacterId(char.character_id)}
          className={cn(
            'w-full text-left p-4 rounded-lg border transition-colors',
            defaultCharacterId === char.character_id
              ? 'border-primary bg-primary/10'
              : 'border-border hover:bg-secondary/30'
          )}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img
                src={`https://images.evetech.net/characters/${char.character_id}/portrait?size=32`}
                alt={char.character_name}
                className="w-8 h-8 rounded-full"
              />
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{char.character_name}</span>
                  {defaultCharacterId === char.character_id && (
                    <Badge variant="default" className="text-xs">
                      Default
                    </Badge>
                  )}
                </div>
              </div>
            </div>
            <div
              className={cn(
                'w-4 h-4 rounded-full border-2',
                defaultCharacterId === char.character_id
                  ? 'border-primary bg-primary'
                  : 'border-border'
              )}
            />
          </div>
        </button>
      ))}
    </div>
  )
}

/**
 * Refresh interval selector
 */
function RefreshIntervalSelector() {
  const { refreshInterval, setRefreshInterval, autoRefresh, setAutoRefresh } = useSettings()

  const intervals = [
    { value: 1, label: '1 minute', description: 'Very frequent updates (high API usage)' },
    { value: 5, label: '5 minutes', description: 'Balanced refresh rate (recommended)' },
    { value: 10, label: '10 minutes', description: 'Less frequent updates' },
    { value: 30, label: '30 minutes', description: 'Minimal API usage' },
  ]

  return (
    <div className="space-y-4">
      {/* Auto-refresh toggle */}
      <button
        onClick={() => setAutoRefresh(!autoRefresh)}
        className={cn(
          'w-full text-left p-4 rounded-lg border transition-colors',
          autoRefresh
            ? 'border-primary bg-primary/10'
            : 'border-border hover:bg-secondary/30'
        )}
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium">Auto-refresh</span>
              {autoRefresh && (
                <Badge variant="success" className="text-xs">
                  Enabled
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Automatically refresh data in the background
            </p>
          </div>
          <div
            className={cn(
              'w-12 h-6 rounded-full transition-colors relative',
              autoRefresh ? 'bg-primary' : 'bg-border'
            )}
          >
            <div
              className={cn(
                'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
                autoRefresh ? 'translate-x-7' : 'translate-x-1'
              )}
            />
          </div>
        </div>
      </button>

      {/* Interval selector */}
      <div className={cn('space-y-3', !autoRefresh && 'opacity-50 pointer-events-none')}>
        <p className="text-sm font-medium">Refresh Interval</p>
        {intervals.map((interval) => (
          <button
            key={interval.value}
            onClick={() => setRefreshInterval(interval.value)}
            disabled={!autoRefresh}
            className={cn(
              'w-full text-left p-4 rounded-lg border transition-colors',
              refreshInterval === interval.value
                ? 'border-primary bg-primary/10'
                : 'border-border hover:bg-secondary/30'
            )}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{interval.label}</span>
                  {refreshInterval === interval.value && (
                    <Badge variant="default" className="text-xs">
                      Active
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground mt-1">{interval.description}</p>
              </div>
              <div
                className={cn(
                  'w-4 h-4 rounded-full border-2',
                  refreshInterval === interval.value
                    ? 'border-primary bg-primary'
                    : 'border-border'
                )}
              />
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

/**
 * Main Settings page
 */
export function Settings() {
  return (
    <div>
      <Header
        title="Settings"
        subtitle="Configure your EVE Copilot experience"
      />

      <div className="p-6">
        <Tabs defaultValue="general" className="space-y-6">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="general">
              <Palette className="h-4 w-4 mr-2" />
              General
            </TabsTrigger>
            <TabsTrigger value="data">
              <Database className="h-4 w-4 mr-2" />
              Data
            </TabsTrigger>
          </TabsList>

          {/* General Settings */}
          <TabsContent value="general" className="space-y-6">
            {/* Theme Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="h-5 w-5" />
                  Appearance
                </CardTitle>
                <CardDescription>
                  Customize the look and feel of the application
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ThemeSelector />
              </CardContent>
            </Card>

            {/* Default Character */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Default Character
                </CardTitle>
                <CardDescription>
                  Set a default character for single-character views
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DefaultCharacterSelector />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Data Settings */}
          <TabsContent value="data" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  Data Refresh
                </CardTitle>
                <CardDescription>
                  Control how often data is refreshed from EVE servers
                </CardDescription>
              </CardHeader>
              <CardContent>
                <RefreshIntervalSelector />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

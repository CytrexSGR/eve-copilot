import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CharacterSelector } from '@/components/CharacterSelector'
import { cn } from '@/lib/utils'

interface HeaderProps {
  title: string
  subtitle?: string
  onRefresh?: () => void
  isRefreshing?: boolean
}

export function Header({ title, subtitle, onRefresh, isRefreshing }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/95 backdrop-blur px-6">
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        {subtitle && (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>

      <div className="flex items-center gap-4">
        {onRefresh && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
          </Button>
        )}
        <CharacterSelector />
      </div>
    </header>
  )
}

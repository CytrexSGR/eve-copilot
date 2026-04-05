import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  Users,
  Package,
  Factory,
  Globe2,
  GraduationCap,
  TrendingUp,
  Mail,
  Settings,
  LayoutDashboard,
  Calculator,
  Sparkles,
  Bot,
  FlaskConical,
  Rocket,
  CreditCard,
  Wrench,
} from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

interface NavItem {
  title: string
  href: string
  icon: React.ElementType
  disabled?: boolean
}

const navItems: NavItem[] = [
  { title: 'Dashboard', href: '/', icon: LayoutDashboard },
  { title: 'Characters', href: '/characters', icon: Users },
  { title: 'Assets', href: '/assets', icon: Package },
  { title: 'Industry', href: '/industry', icon: Factory },
  { title: 'Blueprints', href: '/blueprints', icon: Calculator },
  { title: 'Opportunities', href: '/opportunities', icon: Sparkles },
  { title: 'Reactions', href: '/reactions', icon: FlaskConical },
  { title: 'Planetary', href: '/pi', icon: Globe2 },
  { title: 'Fittings', href: '/fittings', icon: Wrench },
  { title: 'Skills', href: '/skills', icon: GraduationCap },
  { title: 'Market', href: '/market', icon: TrendingUp },
  { title: 'Capital Ops', href: '/capital', icon: Rocket },
  { title: 'AI Copilot', href: '/copilot', icon: Bot },
  { title: 'Subscriptions', href: '/admin/subscriptions', icon: CreditCard },
  { title: 'Mail', href: '/mail', icon: Mail, disabled: true },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-16 border-r border-border bg-card flex flex-col">
      {/* Logo */}
      <div className="flex h-16 items-center justify-center border-b border-border">
        <Link to="/" className="text-2xl font-bold text-primary">
          E
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4">
        <ul className="space-y-2 px-2">
          {navItems.map((item) => {
            const isActive = location.pathname === item.href
            const Icon = item.icon

            return (
              <li key={item.href}>
                <Tooltip delayDuration={0}>
                  <TooltipTrigger asChild>
                    <Link
                      to={item.disabled ? '#' : item.href}
                      className={cn(
                        'flex h-10 w-10 items-center justify-center rounded-lg transition-colors',
                        isActive
                          ? 'bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                        item.disabled && 'opacity-50 cursor-not-allowed'
                      )}
                      onClick={(e) => item.disabled && e.preventDefault()}
                    >
                      <Icon className="h-5 w-5" />
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    {item.title}
                    {item.disabled && ' (Coming Soon)'}
                  </TooltipContent>
                </Tooltip>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Settings */}
      <div className="border-t border-border p-2">
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <Link
              to="/settings"
              className="flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              <Settings className="h-5 w-5" />
            </Link>
          </TooltipTrigger>
          <TooltipContent side="right">Settings</TooltipContent>
        </Tooltip>
      </div>
    </aside>
  )
}

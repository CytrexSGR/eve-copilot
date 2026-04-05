import { Outlet } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Sidebar } from './Sidebar'

export function Layout() {
  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background">
        <Sidebar />
        <main className="pl-16">
          <Outlet />
        </main>
      </div>
    </TooltipProvider>
  )
}

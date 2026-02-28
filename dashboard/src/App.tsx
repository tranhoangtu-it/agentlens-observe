// App root — hash-based routing: #/ = list, #/traces/:id = detail, #/compare/:left/:right = compare
// Sidebar navigation layout with logo + nav items

import { useState, useEffect } from 'react'
import { TracesListPage } from './pages/traces-list-page'
import { TraceDetailPage } from './pages/trace-detail-page'
import { TraceComparePage } from './pages/trace-compare-page'
import { cn } from './lib/utils'
import { Activity, Cpu } from 'lucide-react'

type Route =
  | { name: 'list' }
  | { name: 'detail'; id: string }
  | { name: 'compare'; leftId: string; rightId: string }

function parseHash(hash: string): Route {
  const path = hash.replace(/^#\/?/, '')
  const compareMatch = path.match(/^compare\/([^/]+)\/(.+)$/)
  if (compareMatch) return { name: 'compare', leftId: compareMatch[1], rightId: compareMatch[2] }
  const detailMatch = path.match(/^traces\/(.+)$/)
  if (detailMatch) return { name: 'detail', id: detailMatch[1] }
  return { name: 'list' }
}

function setHash(path: string) {
  window.location.hash = `#/${path}`
}

// Sidebar nav item
function NavItem({
  icon: Icon,
  label,
  active,
  onClick,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors text-left',
        active
          ? 'bg-sidebar-accent text-sidebar-accent-foreground'
          : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground',
      )}
    >
      <Icon size={15} className="shrink-0" />
      {label}
    </button>
  )
}

export default function App() {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash))

  useEffect(() => {
    const onHashChange = () => setRoute(parseHash(window.location.hash))
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  function navigateToTrace(id: string) {
    setHash(`traces/${id}`)
  }

  function navigateToCompare(leftId: string, rightId: string) {
    setHash(`compare/${encodeURIComponent(leftId)}/${encodeURIComponent(rightId)}`)
  }

  function navigateToList() {
    setHash('')
  }

  return (
    <div className="h-screen bg-background text-foreground flex overflow-hidden">
      {/* Sidebar */}
      <aside className="w-52 shrink-0 bg-sidebar border-r border-sidebar-border flex flex-col">
        {/* Logo */}
        <div className="px-4 py-4 border-b border-sidebar-border">
          <button
            onClick={navigateToList}
            className="flex items-center gap-2.5 hover:opacity-80 transition-opacity"
          >
            <div className="w-7 h-7 rounded-md bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0">
              <Cpu size={14} className="text-primary" />
            </div>
            <span className="font-bold text-sm tracking-tight text-foreground">AgentLens</span>
          </button>
          <p className="text-xs text-muted-foreground mt-1 pl-9">Observability</p>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 space-y-1">
          <NavItem
            icon={Activity}
            label="Traces"
            active={true}
            onClick={navigateToList}
          />
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-sidebar-border">
          <p className="text-xs text-muted-foreground/60">v0.1</p>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Breadcrumb header */}
        <header className="shrink-0 border-b border-border px-5 py-2.5 flex items-center gap-2 text-sm">
          <button
            onClick={navigateToList}
            className={cn(
              'transition-colors',
              route.name === 'list'
                ? 'text-foreground font-medium'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            Traces
          </button>
          {route.name === 'detail' && (
            <>
              <span className="text-border">/</span>
              <span className="text-foreground font-medium font-mono text-xs truncate max-w-xs">
                {route.id}
              </span>
            </>
          )}
          {route.name === 'compare' && (
            <>
              <span className="text-border">/</span>
              <span className="text-foreground font-medium text-xs">Compare</span>
              <span className="text-border">/</span>
              <span className="text-muted-foreground font-mono text-xs truncate max-w-[160px]">{route.leftId}</span>
              <span className="text-border">vs</span>
              <span className="text-muted-foreground font-mono text-xs truncate max-w-[160px]">{route.rightId}</span>
            </>
          )}
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-hidden flex flex-col">
          {route.name === 'list' && (
            <TracesListPage onSelect={navigateToTrace} onCompare={navigateToCompare} />
          )}
          {route.name === 'detail' && (
            <TraceDetailPage traceId={route.id} onBack={navigateToList} />
          )}
          {route.name === 'compare' && (
            <TraceComparePage
              leftId={route.leftId}
              rightId={route.rightId}
              onBack={navigateToList}
            />
          )}
        </main>
      </div>
    </div>
  )
}

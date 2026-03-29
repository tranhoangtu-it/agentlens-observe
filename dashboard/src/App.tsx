// App root — hash-based routing with auth guard
// Sidebar navigation layout with logo + nav items + user menu

import { useState, useEffect, lazy, Suspense } from 'react'
import { TracesListPage } from './pages/traces-list-page'
import { TraceDetailPage } from './pages/trace-detail-page'
import { TraceReplayPage } from './pages/trace-replay-page'
import { LoginPage } from './pages/login-page'
import { ApiKeysPage } from './pages/api-keys-page'
import { cn } from './lib/utils'
import { Activity, Bell, Settings, Cpu, Key, LogOut, Sliders } from 'lucide-react'
import { AlertsListPage } from './pages/alerts-list-page'
import { AlertRulesPage } from './pages/alert-rules-page'
import { fetchAlertsSummary } from './lib/alert-api-client'
import { AuthProvider, useAuth } from './lib/auth-context'
import { SettingsPage } from './pages/settings-page'

// Lazy load compare page — rarely used, large dependency (diff utils)
const TraceComparePage = lazy(() =>
  import('./pages/trace-compare-page').then((m) => ({ default: m.TraceComparePage })),
)

type Route =
  | { name: 'list' }
  | { name: 'detail'; id: string }
  | { name: 'replay'; id: string }
  | { name: 'compare'; leftId: string; rightId: string }
  | { name: 'alerts' }
  | { name: 'alert-rules' }
  | { name: 'api-keys' }
  | { name: 'settings' }
  | { name: 'login' }

function parseHash(hash: string): Route {
  const path = hash.replace(/^#\/?/, '')
  if (path === 'login') return { name: 'login' }
  if (path === 'alerts') return { name: 'alerts' }
  if (path === 'alert-rules') return { name: 'alert-rules' }
  if (path === 'api-keys') return { name: 'api-keys' }
  if (path === 'settings') return { name: 'settings' }
  const compareMatch = path.match(/^compare\/([^/]+)\/(.+)$/)
  if (compareMatch) return { name: 'compare', leftId: compareMatch[1], rightId: compareMatch[2] }
  const replayMatch = path.match(/^traces\/([^/]+)\/replay$/)
  if (replayMatch) return { name: 'replay', id: decodeURIComponent(replayMatch[1]) }
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

function AuthenticatedApp() {
  const { user, logout } = useAuth()
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash))
  const [unresolvedCount, setUnresolvedCount] = useState(0)

  useEffect(() => {
    const onHashChange = () => setRoute(parseHash(window.location.hash))
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  // Poll unresolved alert count every 30s
  useEffect(() => {
    const poll = () => fetchAlertsSummary().then((r) => setUnresolvedCount(r.unresolved_count)).catch(() => {})
    poll()
    const timer = setInterval(poll, 30_000)
    return () => clearInterval(timer)
  }, [])

  function navigateToTrace(id: string) {
    setHash(`traces/${id}`)
  }

  function navigateToCompare(leftId: string, rightId: string) {
    setHash(`compare/${encodeURIComponent(leftId)}/${encodeURIComponent(rightId)}`)
  }

  function navigateToReplay(id: string) {
    setHash('traces/' + encodeURIComponent(id) + '/replay')
  }

  function navigateToDetail(id: string) {
    setHash(`traces/${encodeURIComponent(id)}`)
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
            active={route.name === 'list' || route.name === 'detail' || route.name === 'replay' || route.name === 'compare'}
            onClick={navigateToList}
          />
          <div className="relative">
            <NavItem
              icon={Bell}
              label="Alerts"
              active={route.name === 'alerts'}
              onClick={() => setHash('alerts')}
            />
            {unresolvedCount > 0 && (
              <span className="absolute top-1 right-2 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold px-1">
                {unresolvedCount > 99 ? '99+' : unresolvedCount}
              </span>
            )}
          </div>
          <NavItem
            icon={Settings}
            label="Rules"
            active={route.name === 'alert-rules'}
            onClick={() => setHash('alert-rules')}
          />
          <NavItem
            icon={Key}
            label="API Keys"
            active={route.name === 'api-keys'}
            onClick={() => setHash('api-keys')}
          />
          <NavItem
            icon={Sliders}
            label="Settings"
            active={route.name === 'settings'}
            onClick={() => setHash('settings')}
          />
        </nav>

        {/* User menu footer */}
        <div className="px-3 py-3 border-t border-sidebar-border space-y-2">
          <div className="px-1">
            <p className="text-xs text-foreground truncate">{user?.email}</p>
            <p className="text-xs text-muted-foreground/60">{user?.is_admin ? 'Admin' : 'User'}</p>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-xs text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground transition-colors"
          >
            <LogOut size={12} />
            Sign out
          </button>
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
          {route.name === 'replay' && (
            <>
              <span className="text-border">/</span>
              <button
                onClick={() => navigateToDetail(route.id)}
                className="text-muted-foreground hover:text-foreground transition-colors font-mono text-xs truncate max-w-xs"
              >
                {route.id}
              </button>
              <span className="text-border">/</span>
              <span className="text-foreground font-medium text-xs">Replay</span>
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
          {route.name === 'alerts' && (
            <span className="text-foreground font-medium">Alerts</span>
          )}
          {route.name === 'alert-rules' && (
            <span className="text-foreground font-medium">Alert Rules</span>
          )}
          {route.name === 'api-keys' && (
            <span className="text-foreground font-medium">API Keys</span>
          )}
          {route.name === 'settings' && (
            <span className="text-foreground font-medium">Settings</span>
          )}
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-hidden flex flex-col">
          {route.name === 'list' && (
            <TracesListPage onSelect={navigateToTrace} onCompare={navigateToCompare} />
          )}
          {route.name === 'detail' && (
            <TraceDetailPage traceId={route.id} onBack={navigateToList} onReplay={navigateToReplay} />
          )}
          {route.name === 'replay' && (
            <TraceReplayPage traceId={route.id} onBack={() => navigateToDetail(route.id)} />
          )}
          {route.name === 'compare' && (
            <Suspense fallback={<div className="flex items-center justify-center h-full text-muted-foreground text-sm">Loading compare...</div>}>
              <TraceComparePage
                leftId={route.leftId}
                rightId={route.rightId}
                onBack={navigateToList}
              />
            </Suspense>
          )}
          {route.name === 'alerts' && (
            <AlertsListPage onNavigateTrace={navigateToTrace} />
          )}
          {route.name === 'alert-rules' && (
            <AlertRulesPage />
          )}
          {route.name === 'api-keys' && (
            <ApiKeysPage />
          )}
          {route.name === 'settings' && (
            <SettingsPage />
          )}
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  )
}

function AppRouter() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="h-screen bg-background flex items-center justify-center text-muted-foreground text-sm">
        Loading...
      </div>
    )
  }

  if (!user) {
    return <LoginPage />
  }

  return <AuthenticatedApp />
}

// App root — hash-based routing: #/ = list, #/traces/:id = detail

import { useState, useEffect } from 'react'
import { TracesListPage } from './pages/traces-list-page'
import { TraceDetailPage } from './pages/trace-detail-page'

type Route =
  | { name: 'list' }
  | { name: 'detail'; id: string }

function parseHash(hash: string): Route {
  const path = hash.replace(/^#\/?/, '')
  const match = path.match(/^traces\/(.+)$/)
  if (match) return { name: 'detail', id: match[1] }
  return { name: 'list' }
}

function setHash(path: string) {
  window.location.hash = `#/${path}`
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

  function navigateToList() {
    setHash('')
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      {/* Global header */}
      <header className="shrink-0 border-b border-gray-800 px-6 py-3 flex items-center gap-3">
        <button
          onClick={navigateToList}
          className="text-blue-400 font-bold text-lg tracking-tight hover:text-blue-300 transition-colors"
        >
          AgentLens
        </button>
        <span className="text-gray-700 text-sm">|</span>
        <span className="text-gray-500 text-sm">AI agent observability</span>
      </header>

      {/* Page content */}
      <main className="flex-1 overflow-hidden flex flex-col">
        {route.name === 'list' && (
          <TracesListPage onSelect={navigateToTrace} />
        )}
        {route.name === 'detail' && (
          <TraceDetailPage traceId={route.id} onBack={navigateToList} />
        )}
      </main>
    </div>
  )
}

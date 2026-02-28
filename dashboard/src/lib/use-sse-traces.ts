// Custom hook for SSE connection to /api/traces/stream — auto-reconnects on disconnect

import { useState, useEffect, useRef } from 'react'

export interface SSEEvent {
  type: string
  data: unknown
}

export interface UseSSETracesResult {
  latestEvent: SSEEvent | null
  isConnected: boolean
}

const SSE_URL = '/api/traces/stream'
const RECONNECT_DELAY_MS = 3000

export function useSSETraces(): UseSSETracesResult {
  const [latestEvent, setLatestEvent] = useState<SSEEvent | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const esRef = useRef<EventSource | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let active = true

    function connect() {
      if (!active) return
      const es = new EventSource(SSE_URL)
      esRef.current = es

      es.onopen = () => { if (active) setIsConnected(true) }

      // Named SSE events require addEventListener (onmessage only fires for unnamed)
      const handler = (e: MessageEvent) => {
        if (!active) return
        try {
          const data = JSON.parse(e.data as string)
          setLatestEvent({ type: e.type, data })
        } catch { /* ignore malformed */ }
      }
      es.addEventListener('trace_created', handler)

      es.onerror = () => {
        es.close()
        esRef.current = null
        if (active) {
          setIsConnected(false)
          timerRef.current = setTimeout(connect, RECONNECT_DELAY_MS)
        }
      }
    }

    connect()

    return () => {
      active = false
      esRef.current?.close()
      esRef.current = null
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  return { latestEvent, isConnected }
}

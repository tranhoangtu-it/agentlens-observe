// Replay state machine — cursor, play/pause, speed, step navigation
// All times are ms offsets from trace start (0..duration_ms)

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import type { Span } from './api-client'

export type ReplaySpeed = 1 | 2 | 5 | 10

export interface UseReplayControlsResult {
  cursor: number          // current offset ms
  isPlaying: boolean
  speed: ReplaySpeed
  duration: number        // total trace duration_ms
  play: () => void
  pause: () => void
  seek: (ms: number) => void
  stepForward: () => void
  stepBack: () => void
  setSpeed: (s: ReplaySpeed) => void
}

const TICK_MS = 16 // ~60fps

export function useReplayControls(spans: Span[], duration: number): UseReplayControlsResult {
  const [cursor, setCursor] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeedState] = useState<ReplaySpeed>(1)

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const cursorRef = useRef(0)     // shadow for interval closure
  const speedRef = useRef<ReplaySpeed>(1)

  // Sorted unique start offsets for step navigation
  const traceStart = useMemo(() => (spans.length ? Math.min(...spans.map((s) => s.start_ms)) : 0), [spans])
  const spanOffsets = useMemo(
    () => [...new Set(spans.map((s) => s.start_ms - traceStart))].sort((a, b) => a - b),
    [spans, traceStart],
  )

  // Keep refs in sync
  useEffect(() => { cursorRef.current = cursor }, [cursor])
  useEffect(() => { speedRef.current = speed }, [speed])

  const stopInterval = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const play = useCallback(() => {
    if (intervalRef.current !== null) return
    // Reset to start if at end
    if (cursorRef.current >= duration) {
      setCursor(0)
      cursorRef.current = 0
    }
    setIsPlaying(true)
    intervalRef.current = setInterval(() => {
      const next = cursorRef.current + TICK_MS * speedRef.current
      if (next >= duration) {
        cursorRef.current = duration
        setCursor(duration)
        stopInterval()
        setIsPlaying(false)
      } else {
        cursorRef.current = next
        setCursor(next)
      }
    }, TICK_MS)
  }, [duration, stopInterval])

  const pause = useCallback(() => {
    stopInterval()
    setIsPlaying(false)
  }, [stopInterval])

  const seek = useCallback((ms: number) => {
    const clamped = Math.max(0, Math.min(ms, duration))
    cursorRef.current = clamped
    setCursor(clamped)
  }, [duration])

  const stepForward = useCallback(() => {
    pause()
    const next = spanOffsets.find((o) => o > cursorRef.current)
    if (next !== undefined) { cursorRef.current = next; setCursor(next) }
    else { cursorRef.current = duration; setCursor(duration) }
  }, [pause, spanOffsets, duration])

  const stepBack = useCallback(() => {
    pause()
    const prev = [...spanOffsets].reverse().find((o) => o < cursorRef.current)
    if (prev !== undefined) { cursorRef.current = prev; setCursor(prev) }
    else { cursorRef.current = 0; setCursor(0) }
  }, [pause, spanOffsets])

  const setSpeed = useCallback((s: ReplaySpeed) => {
    speedRef.current = s
    setSpeedState(s)
  }, [])

  // Cleanup on unmount
  useEffect(() => () => stopInterval(), [stopInterval])

  return { cursor, isPlaying, speed, duration, play, pause, seek, stepForward, stepBack, setSpeed }
}

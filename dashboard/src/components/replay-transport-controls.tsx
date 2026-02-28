// Replay transport bar — Play/Pause, Prev/Next span step, Speed selector
// Pure display component — all state owned by parent via useReplayControls

import { memo } from 'react'
import { Play, Pause, SkipBack, SkipForward } from 'lucide-react'
import type { ReplaySpeed } from '../lib/use-replay-controls'

interface Props {
  isPlaying: boolean
  speed: ReplaySpeed
  onPlay: () => void
  onPause: () => void
  onStepBack: () => void
  onStepForward: () => void
  onSpeedChange: (s: ReplaySpeed) => void
}

const SPEEDS: ReplaySpeed[] = [1, 2, 5, 10]

export const ReplayTransportControls = memo(function ReplayTransportControls({
  isPlaying, speed, onPlay, onPause, onStepBack, onStepForward, onSpeedChange,
}: Props) {
  return (
    <div className="flex items-center gap-2">
      <button
        onClick={onStepBack}
        className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        title="Previous span"
        aria-label="Step back"
      >
        <SkipBack size={16} />
      </button>

      <button
        onClick={isPlaying ? onPause : onPlay}
        className="p-1.5 rounded bg-primary/10 border border-primary/30 text-primary hover:bg-primary/20 transition-colors"
        aria-label={isPlaying ? 'Pause' : 'Play'}
      >
        {isPlaying ? <Pause size={16} /> : <Play size={16} />}
      </button>

      <button
        onClick={onStepForward}
        className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        title="Next span"
        aria-label="Step forward"
      >
        <SkipForward size={16} />
      </button>

      {/* Speed selector */}
      <div className="flex items-center gap-1 ml-1 border border-border rounded px-1.5 py-0.5">
        {SPEEDS.map((s) => (
          <button
            key={s}
            onClick={() => onSpeedChange(s)}
            className={[
              'text-xs px-1.5 py-0.5 rounded transition-colors',
              s === speed
                ? 'bg-primary text-primary-foreground font-semibold'
                : 'text-muted-foreground hover:text-foreground',
            ].join(' ')}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  )
})

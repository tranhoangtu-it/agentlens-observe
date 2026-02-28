// Cost summary bar chart — cost per span grouped by model using Recharts
// Improved: card-style tooltip, gradient fills, total cost summary

import { memo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  CartesianGrid,
} from 'recharts'
import type { Span } from '../lib/api-client'

interface Props {
  spans: Span[]
}

interface ChartEntry {
  name: string
  cost: number
}

function aggregateByModel(spans: Span[]): ChartEntry[] {
  const map = new Map<string, number>()
  for (const s of spans) {
    if (s.cost_usd <= 0) continue
    const key = s.cost_model ?? s.name
    map.set(key, (map.get(key) ?? 0) + s.cost_usd)
  }
  return Array.from(map.entries())
    .map(([name, cost]) => ({ name, cost: Math.round(cost * 1e6) / 1e6 }))
    .sort((a, b) => b.cost - a.cost)
}

// Palette: [gradient-id-suffix, dark, light]
const BAR_PALETTE: [string, string, string][] = [
  ['blue',   '#3b82f6', '#60a5fa'],
  ['purple', '#a855f7', '#c084fc'],
  ['green',  '#22c55e', '#4ade80'],
  ['orange', '#f97316', '#fb923c'],
  ['pink',   '#ec4899', '#f472b6'],
]

// Inject SVG gradient defs rendered once inside the chart via customized prop
function GradientDefs() {
  return (
    <defs>
      {BAR_PALETTE.map(([id, dark, light]) => (
        <linearGradient key={id} id={`bar-grad-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={light} stopOpacity={0.9} />
          <stop offset="100%" stopColor={dark} stopOpacity={0.75} />
        </linearGradient>
      ))}
    </defs>
  )
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean
  payload?: { value: number }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-card border border-border rounded-md px-3 py-2 shadow-lg text-xs">
      <p className="text-muted-foreground mb-1">{label}</p>
      <p className="font-semibold text-foreground">${payload[0].value.toFixed(6)}</p>
    </div>
  )
}

export const CostSummaryChart = memo(function CostSummaryChart({ spans }: Props) {
  const data = aggregateByModel(spans)

  if (data.length === 0) {
    return (
      <p className="text-xs text-muted-foreground text-center py-4">No cost data available.</p>
    )
  }

  const total = data.reduce((s, d) => s + d.cost, 0)

  return (
    <div>
      {/* Total cost summary */}
      <p className="text-xs text-muted-foreground mb-2">
        Total: <span className="text-foreground font-medium">${total.toFixed(6)}</span>
      </p>

      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 28 }}>
          <GradientDefs />
          <CartesianGrid vertical={false} stroke="#1e293b" strokeDasharray="3 3" />
          <XAxis
            dataKey="name"
            tick={{ fill: '#64748b', fontSize: 10 }}
            angle={-20}
            textAnchor="end"
            interval={0}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 10 }}
            tickFormatter={(v: number) => `$${v.toFixed(4)}`}
            width={64}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#ffffff08' }} />
          <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
            {data.map((_entry, i) => {
              const [id] = BAR_PALETTE[i % BAR_PALETTE.length]
              return <Cell key={i} fill={`url(#bar-grad-${id})`} />
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
})

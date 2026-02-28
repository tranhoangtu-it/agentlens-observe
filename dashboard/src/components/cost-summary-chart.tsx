// Cost summary bar chart — cost per span grouped by model using Recharts

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
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

const BAR_COLORS = ['#3b82f6', '#a855f7', '#22c55e', '#f97316', '#ec4899']

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { value: number }[] }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-xs text-gray-200">
      ${payload[0].value.toFixed(6)}
    </div>
  )
}

export function CostSummaryChart({ spans }: Props) {
  const data = aggregateByModel(spans)

  if (data.length === 0) {
    return (
      <p className="text-xs text-gray-500 text-center py-4">No cost data available.</p>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 32 }}>
        <XAxis
          dataKey="name"
          tick={{ fill: '#9ca3af', fontSize: 11 }}
          angle={-25}
          textAnchor="end"
          interval={0}
        />
        <YAxis
          tick={{ fill: '#9ca3af', fontSize: 11 }}
          tickFormatter={(v: number) => `$${v.toFixed(4)}`}
          width={64}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: '#ffffff10' }} />
        <Bar dataKey="cost" radius={[3, 3, 0, 0]}>
          {data.map((_entry, i) => (
            <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

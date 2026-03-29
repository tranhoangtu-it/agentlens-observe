// MCP-specific metadata panel — renders tool call, resource read, or prompt get details

import { memo } from 'react'
import { Card, CardContent } from './ui/card'

interface McpMetadata {
  mcp_server?: string
  tool_name?: string
  resource_uri?: string
  prompt_name?: string
  arguments?: unknown
}

interface Props {
  spanType: string
  metadata: McpMetadata
}

function McpMetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-3 py-1.5">
      <span className="text-[10px] text-muted-foreground uppercase tracking-wide w-16 shrink-0 pt-0.5">
        {label}
      </span>
      <span className="text-xs text-foreground/90 break-all font-mono">{value}</span>
    </div>
  )
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  'mcp.tool_call': { label: 'MCP Tool Call', color: 'text-cyan-400' },
  'mcp.resource_read': { label: 'MCP Resource Read', color: 'text-teal-400' },
  'mcp.prompt_get': { label: 'MCP Prompt Get', color: 'text-sky-400' },
}

export const McpToolCallPanel = memo(function McpToolCallPanel({ spanType, metadata }: Props) {
  const typeInfo = TYPE_LABELS[spanType] || { label: 'MCP', color: 'text-muted-foreground' }

  return (
    <div className="mt-3">
      <p className={`text-xs font-medium uppercase tracking-wide mb-1.5 ${typeInfo.color}`}>
        {typeInfo.label}
      </p>
      <Card>
        <CardContent className="p-3 space-y-0">
          {metadata.mcp_server && <McpMetaRow label="Server" value={metadata.mcp_server} />}
          {metadata.tool_name && <McpMetaRow label="Tool" value={metadata.tool_name} />}
          {metadata.resource_uri && <McpMetaRow label="URI" value={metadata.resource_uri} />}
          {metadata.prompt_name && <McpMetaRow label="Prompt" value={metadata.prompt_name} />}
          {metadata.arguments != null && (
            <div className="pt-1.5">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Arguments</p>
              <pre className="text-xs font-mono text-foreground/80 whitespace-pre-wrap max-h-32 overflow-y-auto bg-background rounded p-2">
                {typeof metadata.arguments === 'string'
                  ? metadata.arguments
                  : JSON.stringify(metadata.arguments, null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
})

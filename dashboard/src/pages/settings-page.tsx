// Settings page — configure LLM provider and API key for AI features

import { useEffect, useState } from 'react'
import { fetchSettings, updateSettings, type SettingsUpdateIn } from '../lib/settings-api-client'
import { Sliders, Check, AlertCircle } from 'lucide-react'

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'gemini', label: 'Google Gemini' },
]

const DEFAULT_MODELS: Record<string, string> = {
  openai: 'gpt-4o-mini',
  anthropic: 'claude-sonnet-4-20250514',
  gemini: 'gemini-2.0-flash',
}

export function SettingsPage() {
  const [provider, setProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('gpt-4o-mini')
  const [keyIsSet, setKeyIsSet] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchSettings()
      .then((s) => {
        setProvider(s.llm_provider)
        setModel(s.llm_model)
        setKeyIsSet(s.llm_api_key_set)
      })
      .catch(() => {})
  }, [])

  function handleProviderChange(newProvider: string) {
    setProvider(newProvider)
    setModel(DEFAULT_MODELS[newProvider] || '')
  }

  async function handleSave() {
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const data: SettingsUpdateIn = { llm_provider: provider, llm_model: model }
      if (apiKey) data.llm_api_key = apiKey
      const result = await updateSettings(data)
      setKeyIsSet(result.llm_api_key_set)
      setApiKey('')
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      setError('Failed to save settings.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-5 space-y-6 overflow-y-auto max-w-2xl">
      <div className="flex items-center gap-2">
        <Sliders size={16} className="text-muted-foreground" />
        <h1 className="text-sm font-semibold text-foreground">Settings</h1>
      </div>

      <div className="bg-card border border-border rounded-lg p-4 space-y-4">
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          LLM Configuration
        </h2>
        <p className="text-xs text-muted-foreground">
          Configure your LLM API key for AI-powered features like Failure Autopsy and Eval.
          Your key is encrypted and never exposed in API responses.
        </p>

        {/* Provider */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-foreground">Provider</label>
          <select
            value={provider}
            onChange={(e) => handleProviderChange(e.target.value)}
            className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </div>

        {/* API Key */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-foreground">API Key</label>
          <input
            type="password"
            placeholder={keyIsSet ? '••••••••  (key saved — enter new to replace)' : 'Enter your API key'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary font-mono"
          />
          {keyIsSet && !apiKey && (
            <p className="text-xs text-green-400 flex items-center gap-1">
              <Check size={10} /> Key is configured
            </p>
          )}
        </div>

        {/* Model */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-foreground">Model</label>
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="e.g. gpt-4o-mini"
            className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* Save */}
        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 bg-primary text-primary-foreground rounded-md px-4 py-1.5 text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          {saved && (
            <span className="text-xs text-green-400 flex items-center gap-1">
              <Check size={12} /> Saved
            </span>
          )}
          {error && (
            <span className="text-xs text-red-400 flex items-center gap-1">
              <AlertCircle size={12} /> {error}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

// API client for user LLM settings

import { fetchWithAuth } from './fetch-with-auth'

const BASE = '/api'

export interface UserSettings {
  llm_provider: string
  llm_api_key_set: boolean
  llm_model: string
}

export interface SettingsUpdateIn {
  llm_provider: string
  llm_api_key?: string
  llm_model: string
}

export async function fetchSettings(): Promise<UserSettings> {
  const res = await fetchWithAuth(`${BASE}/settings`)
  if (!res.ok) throw new Error(`fetchSettings failed: ${res.status}`)
  return res.json()
}

export async function updateSettings(data: SettingsUpdateIn): Promise<UserSettings> {
  const res = await fetchWithAuth(`${BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`updateSettings failed: ${res.status}`)
  return res.json()
}

/** API client. Types mirror the FastAPI contract in backend/app/api.py. */

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface AttackSpec {
  id: string
  name: string
  category: string
  severity: number
  genai_role: string
  mitre_atlas: string
  channels: string[]
  expected_signals: string[]
  hard_to_detect: boolean
  description: string
}

export interface Txn {
  transaction_id: string
  timestamp: string
  card_token: string
  merchant_id: string
  merchant_name: string
  mcc: string
  amount: number
  currency: string
  channel: string
  entry_mode: string
  merchant_country: string
  cross_border: boolean
  is_fraud: number
  attack_type: string
  risk_score: number
  risk_level: RiskLevel
  recommended_action: string
  p_model: number
  s_rules: number
  s_graph: number
  graph_evaluated: boolean
  injection_detected: boolean
  detected_signals: string[]
  n_signals: number
}

export interface EnvInfo {
  ready: boolean
  transactions: number
  baseline_transactions: number
  attack_transactions: number
  campaigns_launched: number
  risk_levels: Partial<Record<RiskLevel, number>>
  graph_stage_share: number
  train_seconds: number
}

export interface CampaignResult {
  scenario_id: string
  attack_type: string
  attack_name: string
  category: string
  genai_role: string
  mitre_atlas: string
  attack_strength: number
  severity: number
  hard_to_detect: boolean
  expected_detection_signals: string[]
  behavioral_changes: Record<string, unknown>
  n_transactions: number
  victim_cards: string[]
  detection: {
    transactions: number
    flagged_high_or_critical: number
    detection_rate: number
    mean_risk: number
    max_risk: number
    signals_fired: string[]
  }
}

export interface Explanation {
  transaction_id: string
  risk_score: number
  risk_level: RiskLevel
  recommended_action: string
  primary_driver: string
  component_contributions: Record<string, number>
  reason_codes: { signal: string; explanation: string; weight: number }[]
  all_signals: string[]
  counterfactual: string
  explanation_basis: string
  caveat: string
  transaction: Record<string, string | number | boolean>
  ground_truth: { is_fraud: number; attack_type: string | null }
}

export interface GraphData {
  nodes: { id: string; type: string; label: string; risk: number; degree: number }[]
  edges: { source: string; target: string; kind: string }[]
}

export interface AuditEvent {
  id: number
  ts: string
  kind: string
  actor: string
  detail: Record<string, unknown>
}

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`
    try {
      const b = await r.json()
      if (b?.detail) msg = typeof b.detail === 'string' ? b.detail : JSON.stringify(b.detail)
    } catch { /* body was not JSON */ }
    throw new Error(msg)
  }
  return r.json() as Promise<T>
}

const post = (body: unknown) =>
  ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const api = {
  health: () => j<{ status: string; ready: boolean; safety: string }>('/api/health'),

  taxonomy: () => j<{ count: number; categories: string[]; attacks: AttackSpec[] }>('/api/taxonomy'),

  boot: (p: { n_cards: number; n_merchants: number; days: number; seed: number }) =>
    j<{ environment: Record<string, number> }>('/api/environment/boot', post(p)),

  environment: () => j<EnvInfo>('/api/environment'),

  launch: (attack_type: string, strength: number) =>
    j<CampaignResult>('/api/attack/launch', post({ attack_type, strength })),

  campaigns: () => j<{ count: number; campaigns: CampaignResult[] }>('/api/campaigns'),

  transactions: (q: { limit?: number; offset?: number; min_risk?: number; level?: string } = {}) => {
    const s = new URLSearchParams()
    Object.entries(q).forEach(([k, v]) => v !== undefined && v !== '' && s.set(k, String(v)))
    return j<{ total: number; transactions: Txn[] }>(`/api/transactions?${s}`)
  },

  explain: (id: string) => j<Explanation>(`/api/transactions/${encodeURIComponent(id)}/explain`),

  graph: (min_risk = 0.3, limit = 300) =>
    j<GraphData>(`/api/graph?min_risk=${min_risk}&limit=${limit}`),

  metrics: () => j<Record<string, any>>('/api/metrics'),

  importance: (top = 15) =>
    j<{ scope: string; caveat: string; features: { feature: string; importance: number }[] }>(
      `/api/model/importance?top=${top}`),

  audit: (limit = 60) => j<{ count: number; events: AuditEvent[] }>(`/api/audit?limit=${limit}`),
}

export const RISK_COLOR: Record<RiskLevel, string> = {
  LOW: 'text-emerald-400',
  MEDIUM: 'text-amber-400',
  HIGH: 'text-orange-400',
  CRITICAL: 'text-red-400',
}

export const RISK_BG: Record<RiskLevel, string> = {
  LOW: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
  MEDIUM: 'bg-amber-500/10 border-amber-500/30 text-amber-300',
  HIGH: 'bg-orange-500/10 border-orange-500/30 text-orange-300',
  CRITICAL: 'bg-red-500/10 border-red-500/40 text-red-300',
}

export const money = (n: number, c = 'USD') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: c, maximumFractionDigits: 2 })
    .format(n)

export const pct = (n: number, d = 1) => `${(n * 100).toFixed(d)}%`

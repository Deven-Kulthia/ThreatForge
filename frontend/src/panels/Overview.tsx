import { useEffect, useState } from 'react'
import {
  Activity, ArrowUpRight, Boxes, Gauge, Layers, ShieldAlert, Swords, Timer,
} from 'lucide-react'
import {
  Bar as RBar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api, pct, type CampaignResult, type EnvInfo, type RiskLevel } from '../api'
import { Badge, Bar, Empty, Panel, Skeleton, Stat } from '../ui'

const LEVEL_ORDER: RiskLevel[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
const LEVEL_FILL: Record<RiskLevel, string> = {
  LOW: '#22c55e', MEDIUM: '#f59e0b', HIGH: '#fb923c', CRITICAL: '#ef4444',
}

export default function Overview({ env, nonce, onGoto }: {
  env: EnvInfo
  nonce: number
  onGoto: (t: 'simulator' | 'performance' | 'investigate') => void
}) {
  const [camps, setCamps] = useState<CampaignResult[] | null>(null)
  const [metrics, setMetrics] = useState<Record<string, any> | null>(null)
  const [taxonomy, setTaxonomy] = useState<{ count: number; categories: string[] } | null>(null)

  useEffect(() => {
    void api.campaigns().then(r => setCamps(r.campaigns)).catch(() => setCamps([]))
    void api.metrics().then(setMetrics).catch(() => setMetrics(null))
    void api.taxonomy().then(t => setTaxonomy({ count: t.count, categories: t.categories }))
      .catch(() => setTaxonomy(null))
  }, [nonce])

  const levels = LEVEL_ORDER.map(l => ({ level: l, count: env.risk_levels[l] ?? 0 }))
  const low = levels[0].count
  // Chart only the alert bands. Including LOW makes the three bands that actually
  // require action visually disappear — LOW is context, not a comparison.
  const alertBands = levels.slice(1)
  const alertMax = Math.max(...alertBands.map(b => b.count), 1)
  const flagged = (env.risk_levels.HIGH ?? 0) + (env.risk_levels.CRITICAL ?? 0)
  const disc = metrics?.discrimination
  const lat = metrics?.latency
  const zd = metrics?.zero_day

  return (
    <div className="space-y-4">
      {/* ---------- headline posture ---------- */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Transactions in scope" value={env.transactions.toLocaleString()}
              sub={`${env.baseline_transactions.toLocaleString()} legitimate baseline`}
              icon={<Activity size={13} />} />
        <Stat label="Attack traffic injected" value={env.attack_transactions.toLocaleString()}
              tone={env.attack_transactions > 0 ? 'warn' : 'default'}
              sub={`${env.campaigns_launched} campaign${env.campaigns_launched === 1 ? '' : 's'} launched`}
              icon={<Swords size={13} />} />
        <Stat label="High / critical alerts" value={flagged.toLocaleString()}
              tone={flagged > 0 ? 'bad' : 'good'}
              sub={env.transactions ? `${pct(flagged / env.transactions, 2)} of stream` : undefined}
              icon={<ShieldAlert size={13} />} />
        <Stat label="Attack vectors available" value={taxonomy?.count ?? '—'} tone="brand"
              sub={taxonomy ? `${taxonomy.categories.length} threat categories` : undefined}
              icon={<Layers size={13} />} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* ---------- risk distribution ---------- */}
        <Panel className="lg:col-span-2" title="Alert bands across the live stream"
          subtitle="Bands requiring action. Colour is paired with an explicit label — never colour alone."
          right={<Badge className="border-[#26314a] bg-[#162034] text-slate-400">
            graph stage on {pct(env.graph_stage_share, 0)} of traffic
          </Badge>}>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={alertBands} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="#1a2337" vertical={false} />
                <XAxis dataKey="level" tick={{ fill: '#64748b', fontSize: 11 }}
                       axisLine={{ stroke: '#26314a' }} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false}
                       allowDecimals={false} />
                <Tooltip cursor={{ fill: '#ffffff08' }}
                  contentStyle={{ background: '#111a2b', border: '1px solid #26314a',
                                  borderRadius: 8, fontSize: 12, color: '#f1f5f9' }}
                  formatter={(v: number) => [v.toLocaleString(), 'transactions']} />
                <RBar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={90}>
                  {alertBands.map(l => <Cell key={l.level} fill={LEVEL_FILL[l.level]} />)}
                </RBar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table className="mt-1 w-full">
            <caption className="sr-only">Transaction counts by risk band</caption>
            <tbody>
              {levels.map(l => (
                <tr key={l.level} className="border-t border-[#1a2337]">
                  <td className="py-1.5 text-[11.5px] text-slate-400">
                    <span className="mr-2 inline-block h-2 w-2 rounded-sm align-middle"
                          style={{ background: LEVEL_FILL[l.level] }} aria-hidden="true" />
                    {l.level}
                    {l.level === 'LOW' && (
                      <span className="ml-1.5 text-[10px] text-slate-600">(not charted)</span>
                    )}
                  </td>
                  <td className="tnum py-1.5 text-right text-[11.5px] text-slate-300">
                    {l.count.toLocaleString()}
                  </td>
                  <td className="w-1/2 pl-3">
                    {/* Bars are scaled to the largest ALERT band so the actionable
                        bands stay legible; LOW would otherwise flatten all of them. */}
                    <Bar value={l.level === 'LOW' ? alertMax : l.count} max={alertMax}
                         tone={l.level === 'LOW' ? 'good' : l.level === 'CRITICAL' ? 'bad' : 'warn'}
                         height={4} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-[10.5px] text-slate-600">
            {low.toLocaleString()} low-risk transactions pass without review.
            Bars scale to the largest alert band.
          </p>
        </Panel>

        {/* ---------- verified performance ---------- */}
        <Panel title="Verified detection performance"
          subtitle="From the last evaluation run — never hand-written"
          right={<button onClick={() => onGoto('performance')}
            className="inline-flex cursor-pointer items-center gap-1 text-[11px] text-sky-400 transition-colors duration-200 hover:text-sky-300">
            Details <ArrowUpRight size={11} aria-hidden="true" />
          </button>}>
          {!metrics ? (
            <Empty icon={<Gauge size={22} />}>
              No evaluation artifact yet. Run{' '}
              <code className="mono text-[11px] text-slate-400">python -m backend.app.evaluate</code>{' '}
              to generate reproducible metrics.
            </Empty>
          ) : (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2.5">
                <Stat label="PR-AUC" value={disc.pr_auc.toFixed(3)} tone="good"
                      sub={`95% CI ${disc.pr_auc_95ci[0].toFixed(3)}–${disc.pr_auc_95ci[1].toFixed(3)}`} />
                <Stat label="ROC-AUC" value={disc.roc_auc.toFixed(3)} />
              </div>
              <div className="grid grid-cols-2 gap-2.5">
                <Stat label="Decision p99" value={`${lat.decision_p99_ms}ms`} tone="info"
                      sub={`p50 ${lat.decision_p50_ms}ms`} icon={<Timer size={13} />} />
                <Stat label="Zero-day recall" value={zd.unseen_recall.toFixed(3)} tone="brand"
                      sub={`${zd.held_out_vectors.length} unseen vectors`} />
              </div>
              <p className="border-t border-[#1a2337] pt-2.5 text-[10.5px] leading-relaxed text-slate-500">
                PR-AUC is the headline under class imbalance; ROC-AUC is shown for
                comparability and is optimistic. Zero-day recall measures fraud typologies
                entirely absent from training.
              </p>
            </div>
          )}
        </Panel>
      </div>

      {/* ---------- closed loop ---------- */}
      <Panel title="The closed loop" subtitle="Attacks train the defence; defensive gaps generate new attacks">
        <div className="grid gap-3 md:grid-cols-3">
          {[
            { k: 'Identify', d: `${taxonomy?.count ?? 25} GenAI-era attack vectors, each mapped to MITRE ATLAS and annotated with the specific role generative AI plays.`, i: Layers, t: 'brand' as const },
            { k: 'Generate', d: 'Feasible-action attack agents constrained to what an attacker can really control — amount, timing, cadence, merchant, device, sequencing.', i: Swords, t: 'warn' as const },
            { k: 'Defend', d: 'Cascade of rules → gradient-boosted model → graph structure, arbitrated and calibrated, with exact additive reason codes.', i: Boxes, t: 'good' as const },
          ].map(({ k, d, i: Icon, t }) => (
            <div key={k} className="rounded-lg border border-[#26314a] bg-[#111a2b] p-3.5">
              <div className="flex items-center gap-2">
                <Icon size={14} className={t === 'brand' ? 'text-[#f79e1b]'
                  : t === 'warn' ? 'text-amber-400' : 'text-emerald-400'} aria-hidden="true" />
                <span className="text-[12.5px] font-semibold text-slate-200">{k}</span>
              </div>
              <p className="mt-1.5 text-[11.5px] leading-relaxed text-slate-400">{d}</p>
            </div>
          ))}
        </div>
      </Panel>

      {/* ---------- recent campaigns ---------- */}
      <Panel title="Recent red-team campaigns"
        subtitle="Each campaign carries full ground truth, so detection can be graded per-signal"
        right={<button onClick={() => onGoto('simulator')}
          className="inline-flex cursor-pointer items-center gap-1 text-[11px] text-sky-400 transition-colors duration-200 hover:text-sky-300">
          Launch attack <ArrowUpRight size={11} aria-hidden="true" />
        </button>}>
        {camps === null ? <Skeleton rows={3} />
          : camps.length === 0 ? (
            <Empty icon={<Swords size={22} />}>
              No campaigns launched yet. Open <span className="text-slate-400">Attack Simulator</span> to
              simulate one of {taxonomy?.count ?? 25} attack vectors against the live environment.
            </Empty>
          ) : (
            <div className="space-y-2">
              {camps.slice(-6).reverse().map(c => {
                const rate = c.detection.detection_rate
                const tone = rate >= 0.8 ? 'good' : rate >= 0.4 ? 'warn' : 'bad'
                return (
                  <div key={c.scenario_id}
                    className="row-in flex flex-wrap items-center gap-3 rounded-lg border border-[#1a2337] bg-[#111a2b] px-3.5 py-2.5">
                    <div className="min-w-[210px] flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[12.5px] font-medium text-slate-200">{c.attack_name}</span>
                        {c.hard_to_detect && (
                          <Badge className="border-purple-500/30 bg-purple-500/10 text-purple-300"
                                 title="Deliberately designed to overlap legitimate behaviour">
                            HARD BY DESIGN
                          </Badge>
                        )}
                      </div>
                      <div className="mt-0.5 text-[10.5px] text-slate-500">
                        {c.category} · strength {c.attack_strength.toFixed(2)} ·{' '}
                        {c.n_transactions} txns · sev {c.severity}/5
                      </div>
                    </div>
                    <div className="w-40">
                      <div className="mb-1 flex items-center justify-between text-[10.5px]">
                        <span className="text-slate-500">detected</span>
                        <span className={`tnum font-medium ${
                          tone === 'good' ? 'text-emerald-400'
                          : tone === 'warn' ? 'text-amber-400' : 'text-red-400'}`}>
                          {pct(rate, 0)}
                        </span>
                      </div>
                      <Bar value={rate} tone={tone} height={4} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
      </Panel>
    </div>
  )
}

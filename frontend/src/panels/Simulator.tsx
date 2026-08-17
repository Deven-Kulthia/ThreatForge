import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, Crosshair, Filter, Radar, Swords, Target, XCircle } from 'lucide-react'
import { api, pct, type AttackSpec, type CampaignResult } from '../api'
import { Badge, Bar, Button, ErrorNote, Panel, Skeleton, Spinner } from '../ui'

const SEV_TONE = ['', 'text-slate-400', 'text-sky-400', 'text-amber-400', 'text-orange-400', 'text-red-400']

export default function Simulator({ onLaunched }: { onLaunched: () => void }) {
  const [attacks, setAttacks] = useState<AttackSpec[] | null>(null)
  const [cats, setCats] = useState<string[]>([])
  const [cat, setCat] = useState<string>('all')
  const [sel, setSel] = useState<AttackSpec | null>(null)
  const [strength, setStrength] = useState(0.6)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<CampaignResult | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    void api.taxonomy().then(t => {
      setAttacks(t.attacks)
      setCats(t.categories)
      setSel(t.attacks[0] ?? null)
    }).catch(e => setErr(e instanceof Error ? e.message : 'Failed to load taxonomy'))
  }, [])

  const shown = useMemo(
    () => (attacks ?? []).filter(a => cat === 'all' || a.category === cat),
    [attacks, cat],
  )

  const launch = async () => {
    if (!sel) return
    setBusy(true); setErr(null); setResult(null)
    try {
      const r = await api.launch(sel.id, strength)
      setResult(r)
      onLaunched()
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Launch failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <Panel title="Red-team attack simulator"
        subtitle="Safe synthetic simulation. Attacks are modelled as observable behavioural change in a transaction stream — nothing lower-level, and no external target exists."
        right={<Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                      title="The simulator holds no network client and cannot reach any external system.">
          NETWORK-ISOLATED
        </Badge>}>
        <div className="flex flex-wrap items-center gap-2">
          <Filter size={13} className="text-slate-500" aria-hidden="true" />
          <button onClick={() => setCat('all')}
            className={`cursor-pointer rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors duration-200
              ${cat === 'all' ? 'bg-[#1c2942] text-slate-200' : 'text-slate-500 hover:text-slate-300'}`}>
            All ({attacks?.length ?? 0})
          </button>
          {cats.map(c => (
            <button key={c} onClick={() => setCat(c)}
              className={`cursor-pointer rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors duration-200
                ${cat === c ? 'bg-[#1c2942] text-slate-200' : 'text-slate-500 hover:text-slate-300'}`}>
              {c}
            </button>
          ))}
        </div>
      </Panel>

      {err && <ErrorNote onRetry={launch}>{err}</ErrorNote>}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_400px]">
        {/* ---------- vector list ---------- */}
        <Panel title={`Attack vectors — ${shown.length} shown`}
               subtitle="Select a vector to inspect its mechanics and expected detection signals" pad={false}>
          {attacks === null ? <div className="p-4"><Skeleton rows={7} /></div> : (
            <ul className="max-h-[560px] divide-y divide-[#1a2337] overflow-y-auto">
              {shown.map(a => {
                const active = sel?.id === a.id
                return (
                  <li key={a.id}>
                    <button onClick={() => { setSel(a); setResult(null) }}
                      aria-current={active ? 'true' : undefined}
                      className={`w-full cursor-pointer px-4 py-3 text-left transition-colors duration-200
                        ${active ? 'bg-[#162034] shadow-[inset_2px_0_0_#f79e1b]' : 'hover:bg-[#111a2b]'}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-[12.5px] font-medium text-slate-200">{a.name}</span>
                            {a.hard_to_detect && (
                              <Badge className="border-purple-500/30 bg-purple-500/10 text-purple-300">
                                HARD
                              </Badge>
                            )}
                          </div>
                          <div className="mt-0.5 truncate text-[10.5px] text-slate-500">
                            {a.category} · {a.channels.join(', ')}
                          </div>
                        </div>
                        <div className="shrink-0 text-right">
                          <div className={`tnum text-[12px] font-semibold ${SEV_TONE[a.severity]}`}>
                            {a.severity}/5
                          </div>
                          <div className="text-[9.5px] uppercase tracking-wider text-slate-600">sev</div>
                        </div>
                      </div>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </Panel>

        {/* ---------- detail + launch ---------- */}
        <div className="space-y-4">
          {sel && (
            <Panel title={sel.name} subtitle={sel.id}>
              <div className="space-y-3.5">
                <p className="text-[12px] leading-relaxed text-slate-300">{sel.description}</p>

                <div>
                  <Label>What GenAI changed</Label>
                  <p className="mt-1 text-[11.5px] leading-relaxed text-slate-400">{sel.genai_role}</p>
                </div>

                <div>
                  <Label>Framework alignment</Label>
                  <p className="mono mt-1 text-[11px] text-sky-300">{sel.mitre_atlas}</p>
                </div>

                <div>
                  <Label>Expected detection signals</Label>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {sel.expected_signals.map(s => (
                      <Badge key={s} className="border-[#26314a] bg-[#162034] text-slate-400">
                        {s}
                      </Badge>
                    ))}
                  </div>
                  <p className="mt-1.5 text-[10.5px] leading-relaxed text-slate-600">
                    Declared up front, so we can measure whether the defence caught this attack
                    for the right reason — not just that a score crossed a threshold.
                  </p>
                </div>

                <div className="border-t border-[#1a2337] pt-3.5">
                  <div className="flex items-center justify-between">
                    <Label>Attack strength</Label>
                    <span className="tnum text-[12px] font-semibold text-[#f79e1b]">
                      {strength.toFixed(2)}
                    </span>
                  </div>
                  <input type="range" min={0.1} max={1} step={0.05} value={strength}
                    onChange={e => setStrength(Number(e.target.value))}
                    aria-label="Attack strength"
                    className="mt-2 w-full cursor-pointer accent-[#f79e1b]" />
                  <div className="mt-1 flex justify-between text-[10px] text-slate-600">
                    <span>subtle · fewer entities</span><span>aggressive · at scale</span>
                  </div>
                </div>

                <Button onClick={launch} disabled={busy}>
                  {busy ? <Spinner label="Simulating and scoring…" />
                        : <><Crosshair size={14} strokeWidth={2.2} aria-hidden="true" /> Launch campaign</>}
                </Button>
              </div>
            </Panel>
          )}

          {result && <ResultCard r={result} />}
        </div>
      </div>
    </div>
  )
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
      {children}
    </div>
  )
}

function ResultCard({ r }: { r: CampaignResult }) {
  const d = r.detection
  const rate = d.detection_rate
  const tone = rate >= 0.8 ? 'good' : rate >= 0.4 ? 'warn' : 'bad'
  const expected = new Set(r.expected_detection_signals)
  const fired = new Set(d.signals_fired)
  const matched = [...expected].filter(s => fired.has(s))

  return (
    <Panel className="row-in" title="Campaign result"
      subtitle={r.scenario_id}
      right={<Badge className={
        tone === 'good' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
        : tone === 'warn' ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
        : 'border-red-500/30 bg-red-500/10 text-red-300'}>
        {pct(rate, 0)} DETECTED
      </Badge>}>
      <div className="space-y-3.5">
        <div className="grid grid-cols-3 gap-2.5">
          {[
            ['Injected', d.transactions.toLocaleString()],
            ['Flagged', d.flagged_high_or_critical.toLocaleString()],
            ['Max risk', d.max_risk.toFixed(3)],
          ].map(([l, v]) => (
            <div key={l} className="rounded-lg border border-[#26314a] bg-[#111a2b] px-3 py-2">
              <div className="text-[9.5px] font-semibold uppercase tracking-wider text-slate-500">{l}</div>
              <div className="tnum mt-0.5 text-[16px] font-semibold text-slate-100">{v}</div>
            </div>
          ))}
        </div>

        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <Label>Detection rate</Label>
            <span className="tnum text-[11.5px] text-slate-400">
              mean risk {d.mean_risk.toFixed(3)}
            </span>
          </div>
          <Bar value={rate} tone={tone} />
        </div>

        <div className="border-t border-[#1a2337] pt-3">
          <div className="flex items-center gap-1.5">
            <Target size={12} className="text-slate-500" aria-hidden="true" />
            <Label>Signal attribution — {matched.length}/{expected.size} expected signals fired</Label>
          </div>
          <ul className="mt-2 space-y-1">
            {[...expected].map(s => {
              const hit = fired.has(s)
              return (
                <li key={s} className="flex items-center gap-2 text-[11.5px]">
                  {hit
                    ? <CheckCircle2 size={13} className="shrink-0 text-emerald-400" aria-hidden="true" />
                    : <XCircle size={13} className="shrink-0 text-slate-600" aria-hidden="true" />}
                  <span className={hit ? 'text-slate-300' : 'text-slate-600'}>{s}</span>
                  {!hit && (
                    <span className="ml-auto text-[10px] text-slate-600">not fired</span>
                  )}
                </li>
              )
            })}
          </ul>
          <p className="mt-2 text-[10.5px] leading-relaxed text-slate-600">
            Signals that never fire are reported rather than hidden — some are outside the
            authorization schema entirely (dispute lifecycle, session telemetry) and are
            documented as such.
          </p>
        </div>

        {d.signals_fired.length > 0 && (
          <div className="border-t border-[#1a2337] pt-3">
            <div className="flex items-center gap-1.5">
              <Radar size={12} className="text-slate-500" aria-hidden="true" />
              <Label>All signals fired on this campaign ({d.signals_fired.length})</Label>
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {d.signals_fired.map(s => (
                <Badge key={s} className={expected.has(s)
                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                  : 'border-[#26314a] bg-[#162034] text-slate-400'}>
                  {s}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {Object.keys(r.behavioral_changes).length > 0 && (
          <div className="border-t border-[#1a2337] pt-3">
            <div className="flex items-center gap-1.5">
              <Swords size={12} className="text-slate-500" aria-hidden="true" />
              <Label>Behavioural changes introduced</Label>
            </div>
            <dl className="mono mt-1.5 space-y-0.5 text-[11px]">
              {Object.entries(r.behavioral_changes).map(([k, v]) => (
                <div key={k} className="flex gap-2">
                  <dt className="shrink-0 text-slate-500">{k}:</dt>
                  <dd className="text-slate-300">{String(v)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
    </Panel>
  )
}

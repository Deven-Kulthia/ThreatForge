import { useEffect, useState } from 'react'
import { Gauge, Timer, TrendingUp, Zap } from 'lucide-react'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api, pct } from '../api'
import { Badge, Bar, Empty, Panel, Skeleton, Stat, Td, Th } from '../ui'

const TIP = {
  contentStyle: { background: '#111a2b', border: '1px solid #26314a', borderRadius: 8,
                  fontSize: 12, color: '#f1f5f9' },
}

export default function Performance({ nonce }: { nonce: number }) {
  const [m, setM] = useState<Record<string, any> | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    void api.metrics().then(setM).catch(e => setErr(e instanceof Error ? e.message : 'No metrics'))
  }, [nonce])

  if (err) return (
    <Panel title="Evaluation metrics">
      <Empty icon={<Gauge size={22} />}>
        No evaluation artifact found. Run{' '}
        <code className="mono text-[11px] text-slate-400">python -m backend.app.evaluate</code>{' '}
        to generate reproducible metrics — every number here comes from that run, never from prose.
      </Empty>
    </Panel>
  )
  if (!m) return <Panel title="Evaluation metrics"><Skeleton rows={10} /></Panel>

  const d = m.dataset, sp = m.split, disc = m.discrimination
  const f1 = m.operating_point_best_f1, cap = m.operating_point_capacity_constrained
  const pm = m.operating_point_prevalence_matched, mo = m.money_and_customer_impact
  const cal = m.calibration, lat = m.latency, zd = m.zero_day, cov = m.coverage

  const perAttack = Object.entries(m.per_attack as Record<string, any>)
    .sort((a, b) => a[1].recall_at_alert_rate - b[1].recall_at_alert_rate)

  return (
    <div className="space-y-4">
      <Panel title="Evaluation" subtitle={`Generated ${String(m.generated_at_utc).slice(0, 19)}Z · reproduce with: python -m backend.app.evaluate`}
        right={<Badge className="border-sky-500/30 bg-sky-500/10 text-sky-300">
          {d.transactions.toLocaleString()} TXNS · {pct(d.fraud_rate, 2)} FRAUD
        </Badge>}>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label="PR-AUC" value={disc.pr_auc.toFixed(4)} tone="good"
                sub={`95% CI ${disc.pr_auc_95ci[0].toFixed(3)}–${disc.pr_auc_95ci[1].toFixed(3)}`}
                icon={<TrendingUp size={13} />} />
          <Stat label="ROC-AUC" value={disc.roc_auc.toFixed(4)}
                sub="optimistic under imbalance — shown for comparability" />
          <Stat label="Decision p99" value={`${lat.decision_p99_ms} ms`} tone="info"
                sub={`p50 ${lat.decision_p50_ms} ms · p95 ${lat.decision_p95_ms} ms`}
                icon={<Timer size={13} />} />
          <Stat label="Zero-day recall" value={zd.unseen_recall.toFixed(3)} tone="brand"
                sub={`${zd.held_out_vectors.length} vectors absent from training`}
                icon={<Zap size={13} />} />
        </div>
        <p className="mt-3 border-t border-[#1a2337] pt-3 text-[11px] leading-relaxed text-slate-500">
          <span className="font-medium text-slate-400">Split:</span> {sp.method} — train{' '}
          {sp.train.toLocaleString()}, test {sp.test.toLocaleString()}, with{' '}
          {pct(sp.delay_fraction, 0)} of the timeline discarded between them to reflect late
          label arrival. Random splits would leak future information.
        </p>
      </Panel>

      {/* ---------- operating points ---------- */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Best-F1 operating point" subtitle={`threshold ${f1.threshold.toFixed(3)}`}>
          <div className="space-y-2.5">
            {[['Precision', f1.precision], ['Recall', f1.recall], ['F1', f1.f1]].map(([l, v]) => (
              <div key={String(l)}>
                <div className="mb-1 flex justify-between text-[11.5px]">
                  <span className="text-slate-400">{l}</span>
                  <span className="tnum font-medium text-slate-100">{(v as number).toFixed(3)}</span>
                </div>
                <Bar value={v as number} tone="good" height={4} />
              </div>
            ))}
            <dl className="tnum grid grid-cols-2 gap-x-3 gap-y-1 border-t border-[#1a2337] pt-2.5 text-[11px]">
              {Object.entries(f1.confusion).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <dt className="uppercase text-slate-500">{k}</dt>
                  <dd className="text-slate-300">{(v as number).toLocaleString()}</dd>
                </div>
              ))}
            </dl>
            <div className="flex justify-between border-t border-[#1a2337] pt-2 text-[11px]">
              <span className="text-slate-500">False positive rate</span>
              <span className="tnum text-emerald-400">{f1.false_positive_rate.toFixed(5)}</span>
            </div>
          </div>
        </Panel>

        <Panel title="Capacity-constrained" subtitle={`${pct(cap.alert_rate, 0)} analyst review budget`}>
          <div className="space-y-2.5">
            <Stat label="Recall" value={cap.recall.toFixed(3)} tone="warn"
                  sub={`ceiling ${cap.recall_ceiling.toFixed(3)} — budget-bound, not model-bound`} />
            <Stat label="Precision" value={cap.precision.toFixed(3)} tone="good"
                  sub={`${cap.alerts.toLocaleString()} alerts issued`} />
            <p className="rounded-lg border border-amber-500/20 bg-amber-500/[0.06] px-2.5 py-2 text-[10.5px] leading-relaxed text-amber-100/75">
              {cap.ceiling_note}
            </p>
          </div>
        </Panel>

        <Panel title="Prevalence-matched" subtitle={`${pct(pm.alert_rate, 2)} budget — not budget-capped`}>
          <div className="space-y-2.5">
            <Stat label="Recall" value={pm.recall.toFixed(3)} tone="good" />
            <Stat label="Precision" value={pm.precision.toFixed(3)} tone="good" />
            <div className="space-y-1.5 border-t border-[#1a2337] pt-2.5 text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-500">Value detection rate</span>
                <span className="tnum text-emerald-400">{mo.value_detection_rate.toFixed(3)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Insult rate</span>
                <span className="tnum text-slate-300">{mo.insult_rate.toFixed(5)}</span>
              </div>
            </div>
          </div>
        </Panel>
      </div>

      {/* ---------- calibration ---------- */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Calibration" subtitle={`Brier ${cal.brier.toFixed(5)} · ECE ${cal.ece_10bin.toFixed(5)} · ${cal.method}`}>
          <div className="h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={cal.reliability} margin={{ top: 6, right: 10, left: -22, bottom: 0 }}>
                <CartesianGrid stroke="#1a2337" />
                <XAxis dataKey="predicted" type="number" domain={[0, 1]}
                       tick={{ fill: '#64748b', fontSize: 10 }} axisLine={{ stroke: '#26314a' }}
                       tickLine={false} label={{ value: 'predicted', position: 'insideBottom',
                       offset: -2, fill: '#64748b', fontSize: 10 }} />
                <YAxis type="number" domain={[0, 1]} tick={{ fill: '#64748b', fontSize: 10 }}
                       axisLine={false} tickLine={false} />
                <Tooltip {...TIP} formatter={(v: number) => v.toFixed(3)} />
                {/* Perfect-calibration reference: predicted == observed. */}
                <Line dataKey="predicted" stroke="#475569" strokeDasharray="4 4" dot={false}
                      name="perfect" isAnimationActive={false} />
                <Line dataKey="observed" stroke="#22c55e" strokeWidth={2}
                      dot={{ r: 3, fill: '#22c55e' }} name="observed" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-[10.5px] leading-relaxed text-slate-500">
            Green tracking the dashed line means a score of 0.9 really does mean ~90% fraud
            probability — which is what makes a cost-based block threshold defensible.
          </p>
        </Panel>

        <Panel title="Zero-day generalisation"
          subtitle={`${zd.held_out_vectors.length} attack vectors removed from training entirely`}>
          <div className="mb-3 grid grid-cols-2 gap-2.5">
            <Stat label="Unseen recall" value={zd.unseen_recall.toFixed(3)} tone="brand"
                  sub={`${zd.unseen_transactions.toLocaleString()} txns`} />
            <Stat label="Threshold" value={zd.threshold_from_seen_traffic.toFixed(3)}
                  sub="calibrated on seen traffic only" />
          </div>
          <div className="max-h-[170px] overflow-auto">
            <table className="w-full border-collapse">
              <thead><tr><Th>Held-out vector</Th><Th align="right">Recall</Th><Th align="center">Hard</Th></tr></thead>
              <tbody>
                {Object.entries(zd.per_vector as Record<string, any>)
                  .sort((a, b) => a[1].recall_at_seen_threshold - b[1].recall_at_seen_threshold)
                  .map(([k, v]) => (
                    <tr key={k} className="border-b border-[#131c2e]">
                      <Td className="mono text-[10.5px] text-slate-300">{k}</Td>
                      <Td align="right" className="tnum text-slate-200">
                        {v.recall_at_seen_threshold.toFixed(3)}
                      </Td>
                      <Td align="center">
                        {v.hard_to_detect
                          ? <Badge className="border-purple-500/30 bg-purple-500/10 text-purple-300">HARD</Badge>
                          : <span className="text-slate-700">—</span>}
                      </Td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[10.5px] leading-relaxed text-slate-500">{zd.interpretation}.</p>
        </Panel>
      </div>

      {/* ---------- per-attack ---------- */}
      <Panel title="Per-attack recall" subtitle="At the capacity-constrained operating point, worst first — the hard cases are meant to be hard" pad={false}>
        <div className="max-h-[420px] overflow-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Attack vector</Th><Th>Category</Th><Th align="right">n</Th>
                <Th align="right">Recall</Th><Th align="right">Mean risk</Th>
                <Th align="center">Hard</Th><Th align="center">Sev</Th>
              </tr>
            </thead>
            <tbody>
              {perAttack.map(([k, v]) => (
                <tr key={k} className="border-b border-[#131c2e] hover:bg-[#111a2b]">
                  <Td className="mono text-[10.5px] text-slate-300">{k}</Td>
                  <Td className="text-slate-500">{v.category}</Td>
                  <Td align="right" className="tnum text-slate-400">{v.n}</Td>
                  <Td align="right">
                    <div className="flex items-center justify-end gap-2">
                      <span className={`tnum font-medium ${
                        v.recall_at_alert_rate >= 0.6 ? 'text-emerald-400'
                        : v.recall_at_alert_rate >= 0.25 ? 'text-amber-400' : 'text-red-400'}`}>
                        {v.recall_at_alert_rate.toFixed(3)}
                      </span>
                      <div className="w-16"><Bar value={v.recall_at_alert_rate}
                        tone={v.recall_at_alert_rate >= 0.6 ? 'good'
                          : v.recall_at_alert_rate >= 0.25 ? 'warn' : 'bad'} height={3} /></div>
                    </div>
                  </Td>
                  <Td align="right" className="tnum text-slate-400">{v.mean_risk.toFixed(3)}</Td>
                  <Td align="center">
                    {v.hard_to_detect
                      ? <Badge className="border-purple-500/30 bg-purple-500/10 text-purple-300">HARD</Badge>
                      : <span className="text-slate-700">—</span>}
                  </Td>
                  <Td align="center" className="tnum text-slate-400">{v.severity}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* ---------- coverage + honesty ---------- */}
      <Panel title="Signal coverage and stated limitations">
        <div className="grid gap-3 sm:grid-cols-4">
          <Stat label="Attack vectors" value={cov.attack_vectors_simulated} />
          <Stat label="Categories" value={cov.categories} />
          <Stat label="Rule signals" value={cov.rule_signals_implemented} />
          <Stat label="Signals covered"
                value={`${cov.expected_signals_covered}/${cov.expected_signals_distinct}`} />
        </div>
        <div className="mt-3 border-t border-[#1a2337] pt-3">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Signals we deliberately do not implement
          </div>
          <ul className="mt-2 space-y-1.5">
            {Object.entries(cov.signals_not_implemented as Record<string, string>).map(([k, v]) => (
              <li key={k} className="flex flex-wrap gap-2 text-[11px]">
                <code className="mono text-slate-400">{k}</code>
                <span className="text-slate-600">— {v}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="mt-3 rounded-lg border border-[#26314a] bg-[#111a2b] px-3 py-2.5 text-[10.5px] leading-relaxed text-slate-400">
          {m.prevalence_note}
        </p>
      </Panel>
    </div>
  )
}

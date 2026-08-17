import { useEffect, useState } from 'react'
import { AlertOctagon, BadgeCheck, Ban, Brain, Lightbulb, ScanSearch, ShieldQuestion } from 'lucide-react'
import { api, RISK_BG, money, type Explanation, type RiskLevel, type Txn } from '../api'
import { Badge, Bar, Empty, ErrorNote, Panel, Skeleton, Td, Th } from '../ui'

const DRIVER_LABEL: Record<string, string> = {
  contrib_model_score: 'Statistical model',
  contrib_rule_signals: 'Rule signals',
  contrib_graph_structure: 'Graph structure',
  contrib_ring_membership: 'Ring membership',
  contrib_injection_flag: 'Injection flag',
  model_score: 'Statistical model',
  rule_signals: 'Rule signals',
  graph_structure: 'Graph structure',
  ring_membership: 'Ring membership',
  injection_flag: 'Injection flag',
}

export default function Investigate({ nonce }: { nonce: number }) {
  const [rows, setRows] = useState<Txn[] | null>(null)
  const [sel, setSel] = useState<string | null>(null)
  const [exp, setExp] = useState<Explanation | null>(null)
  const [loadingExp, setLoadingExp] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    setSel(null); setExp(null)
    void api.transactions({ limit: 80, min_risk: 0.3 })
      .then(r => {
        setRows(r.transactions)
        if (r.transactions[0]) void pick(r.transactions[0].transaction_id)
      })
      .catch(e => setErr(e instanceof Error ? e.message : 'Failed to load alerts'))
  }, [nonce])

  const pick = async (id: string) => {
    setSel(id); setLoadingExp(true); setExp(null)
    try {
      setExp(await api.explain(id))
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Failed to explain transaction')
    } finally {
      setLoadingExp(false)
    }
  }

  return (
    <div className="space-y-4">
      {err && <ErrorNote>{err}</ErrorNote>}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_460px]">
        {/* ---------- alert queue ---------- */}
        <Panel title="Alert queue" subtitle="Transactions at or above review threshold, highest risk first" pad={false}>
          {rows === null ? <div className="p-4"><Skeleton rows={9} /></div>
            : rows.length === 0 ? (
              <Empty icon={<ShieldQuestion size={22} />}>
                Nothing above the review threshold. Launch a red-team campaign to generate alerts.
              </Empty>
            ) : (
              <div className="max-h-[620px] overflow-auto">
                <table className="w-full border-collapse">
                  <caption className="sr-only">Alert queue sorted by risk</caption>
                  <thead>
                    <tr>
                      <Th>Transaction</Th>
                      <Th>Merchant</Th>
                      <Th align="right">Amount</Th>
                      <Th align="right">Risk</Th>
                      <Th>Band</Th>
                      <Th align="center">Signals</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...rows].sort((a, b) => b.risk_score - a.risk_score).map(t => (
                      <tr key={t.transaction_id} onClick={() => void pick(t.transaction_id)}
                          tabIndex={0}
                          onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); void pick(t.transaction_id) } }}
                          className={`cursor-pointer border-b border-[#131c2e] transition-colors duration-150
                            ${sel === t.transaction_id ? 'bg-[#162034] shadow-[inset_2px_0_0_#f79e1b]' : 'hover:bg-[#111a2b]'}`}>
                        <Td className="mono text-slate-400">{t.transaction_id.slice(0, 16)}</Td>
                        <Td className="max-w-[180px]">
                          <div className="truncate text-slate-300" title={t.merchant_name}>
                            {t.merchant_name}
                          </div>
                        </Td>
                        <Td align="right" className="tnum whitespace-nowrap text-slate-200">
                          {money(t.amount, t.currency)}
                        </Td>
                        <Td align="right" className="tnum font-semibold text-slate-100">
                          {t.risk_score.toFixed(3)}
                        </Td>
                        <Td><Badge className={RISK_BG[t.risk_level as RiskLevel]}>{t.risk_level}</Badge></Td>
                        <Td align="center" className="tnum text-slate-400">{t.n_signals}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </Panel>

        {/* ---------- explainability ---------- */}
        <div className="space-y-4">
          {loadingExp ? (
            <Panel title="Explanation"><Skeleton rows={7} /></Panel>
          ) : !exp ? (
            <Panel title="Explanation">
              <Empty icon={<ScanSearch size={22} />}>
                Select an alert to see exactly why it scored as it did.
              </Empty>
            </Panel>
          ) : (
            <ExplanationCard exp={exp} />
          )}
        </div>
      </div>
    </div>
  )
}

function ExplanationCard({ exp }: { exp: Explanation }) {
  const contribs = Object.entries(exp.component_contributions)
    .sort(([, a], [, b]) => b - a)
  const maxAbs = Math.max(...contribs.map(([, v]) => Math.abs(v)), 0.001)
  const truth = exp.ground_truth

  return (
    <>
      <Panel title="Decision" subtitle={exp.transaction_id}
        right={<Badge className={RISK_BG[exp.risk_level]}>{exp.risk_level}</Badge>}>
        <div className="space-y-3.5">
          <div className="flex items-end justify-between gap-4">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Calibrated risk
              </div>
              <div className="tnum text-[34px] font-semibold leading-none text-slate-50">
                {exp.risk_score.toFixed(3)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Recommended action
              </div>
              <div className="mt-1 inline-flex items-center gap-1.5">
                {exp.recommended_action === 'BLOCK'
                  ? <Ban size={14} className="text-red-400" aria-hidden="true" />
                  : <BadgeCheck size={14} className="text-amber-400" aria-hidden="true" />}
                <span className="text-[14px] font-semibold text-slate-100">
                  {exp.recommended_action}
                </span>
              </div>
            </div>
          </div>
          <Bar value={exp.risk_score} tone={exp.risk_score > 0.85 ? 'bad'
            : exp.risk_score > 0.6 ? 'warn' : 'good'} />

          <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 border-t border-[#1a2337] pt-3 text-[11.5px]">
            {[
              ['Amount', money(Number(exp.transaction.amount), String(exp.transaction.currency))],
              ['Merchant', String(exp.transaction.merchant_name)],
              ['MCC', String(exp.transaction.mcc)],
              ['Channel', String(exp.transaction.channel)],
              ['Entry mode', String(exp.transaction.entry_mode)],
              ['3-D Secure', String(exp.transaction.three_ds_status)],
              ['AVS', String(exp.transaction.avs_result)],
              ['SCA exemption', String(exp.transaction.sca_exemption)],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2">
                <dt className="text-slate-500">{k}</dt>
                <dd className="truncate text-right text-slate-300" title={v}>{v}</dd>
              </div>
            ))}
          </dl>

          <div className="flex items-center justify-between rounded-lg border border-[#26314a] bg-[#111a2b] px-3 py-2">
            <span className="text-[10.5px] font-semibold uppercase tracking-wider text-slate-500">
              Ground truth (lab only)
            </span>
            {truth.is_fraud === 1
              ? <Badge className="border-amber-500/30 bg-amber-500/10 text-amber-300">
                  {truth.attack_type}
                </Badge>
              : <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                  LEGITIMATE
                </Badge>}
          </div>
        </div>
      </Panel>

      <Panel title="Why — exact score decomposition"
        subtitle="Additive contributions to the arbiter's log-odds. Not an estimate: this is the arithmetic that produced the score.">
        <div className="space-y-2.5">
          {contribs.map(([k, v]) => {
            const positive = v >= 0
            return (
              <div key={k}>
                <div className="mb-1 flex items-center justify-between text-[11.5px]">
                  <span className="text-slate-300">{DRIVER_LABEL[k] ?? k}</span>
                  <span className={`tnum font-medium ${positive ? 'text-red-400' : 'text-emerald-400'}`}>
                    {positive ? '+' : ''}{v.toFixed(3)}
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#1a2337]">
                  <div className={`h-full rounded-full transition-[width] duration-500
                    ${positive ? 'bg-red-500' : 'bg-emerald-500'}`}
                    style={{ width: `${(Math.abs(v) / maxAbs) * 100}%` }} />
                </div>
              </div>
            )
          })}
        </div>
        <div className="mt-3 flex items-start gap-2 border-t border-[#1a2337] pt-3">
          <Brain size={13} className="mt-0.5 shrink-0 text-slate-600" aria-hidden="true" />
          <p className="text-[10.5px] leading-relaxed text-slate-500">{exp.caveat}</p>
        </div>
      </Panel>

      <Panel title="Reason codes" subtitle="Ranked by signal weight — analyst-facing language">
        <ul className="space-y-2">
          {exp.reason_codes.map(rc => (
            <li key={rc.signal}
                className="rounded-lg border border-[#1a2337] bg-[#111a2b] px-3 py-2.5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="mono text-[10.5px] text-sky-300">{rc.signal}</div>
                  <p className="mt-1 text-[11.5px] leading-relaxed text-slate-300">
                    {rc.explanation}
                  </p>
                </div>
                <span className="tnum shrink-0 text-[11px] font-medium text-slate-500">
                  w {rc.weight.toFixed(2)}
                </span>
              </div>
            </li>
          ))}
        </ul>

        {exp.all_signals.length > exp.reason_codes.length && (
          <div className="mt-3 border-t border-[#1a2337] pt-2.5">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              All {exp.all_signals.length} signals fired
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {exp.all_signals.map(s => (
                <Badge key={s} className="border-[#26314a] bg-[#162034] text-slate-400">{s}</Badge>
              ))}
            </div>
          </div>
        )}

        <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/[0.06] px-3 py-2.5">
          <Lightbulb size={13} className="mt-0.5 shrink-0 text-amber-400" aria-hidden="true" />
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wider text-amber-300/80">
              Counterfactual
            </div>
            <p className="mt-0.5 text-[11.5px] leading-relaxed text-amber-100/80">
              {exp.counterfactual}
            </p>
          </div>
        </div>

        {exp.all_signals.includes('injection_pattern_in_text') && (
          <div className="mt-2.5 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2.5">
            <AlertOctagon size={13} className="mt-0.5 shrink-0 text-red-400" aria-hidden="true" />
            <p className="text-[11.5px] leading-relaxed text-red-200">
              Merchant-supplied text on this transaction contained prompt-injection patterns.
              It was treated as untrusted data and never passed to a model as instructions
              (OWASP LLM01:2025).
            </p>
          </div>
        )}
      </Panel>
    </>
  )
}

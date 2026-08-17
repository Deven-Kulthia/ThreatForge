import { useEffect, useMemo, useRef, useState } from 'react'
import { Pause, Play, Radio, ShieldAlert } from 'lucide-react'
import { RISK_BG, money, pct, type RiskLevel, type Txn } from '../api'
import { Badge, Button, Empty, Panel, Skeleton, Td, Th } from '../ui'

/** Live authorization feed over WebSocket. Replays the scored synthetic environment. */
export default function Stream({ nonce }: { nonce: number }) {
  const [rows, setRows] = useState<Txn[]>([])
  const [live, setLive] = useState(true)
  const [done, setDone] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [onlyRisky, setOnlyRisky] = useState(false)
  const ws = useRef<WebSocket | null>(null)
  const paused = useRef(false)

  useEffect(() => { paused.current = !live }, [live])

  useEffect(() => {
    setRows([]); setDone(false); setErr(null)
    // StrictMode mounts effects twice in development. Without this flag the first
    // socket's intentional cleanup-close fires onerror and wrongly reports a failure.
    let closedByUs = false
    const sock = new WebSocket(`ws://${location.host}/ws/stream`)
    ws.current = sock

    sock.onmessage = ev => {
      const msg = JSON.parse(ev.data as string)
      if (msg.type === 'transaction') {
        if (paused.current) return
        const t = msg.data as Txn
        // Dedupe by transaction id: a reconnect (or StrictMode's second socket in dev)
        // replays the same window, and duplicate rows would break list identity.
        setRows(prev => prev.some(r => r.transaction_id === t.transaction_id)
          ? prev
          : [t, ...prev].slice(0, 220))
      } else if (msg.type === 'complete') {
        setDone(true)
      } else if (msg.type === 'error') {
        setErr(String(msg.message))
      }
    }
    sock.onerror = () => {
      if (!closedByUs) setErr('Stream connection failed — is the backend running?')
    }

    return () => { closedByUs = true; sock.close() }
  }, [nonce])

  const shown = useMemo(
    () => onlyRisky ? rows.filter(r => r.risk_level === 'HIGH' || r.risk_level === 'CRITICAL') : rows,
    [rows, onlyRisky],
  )

  const stats = useMemo(() => {
    const flagged = rows.filter(r => r.risk_level === 'HIGH' || r.risk_level === 'CRITICAL').length
    const fraud = rows.filter(r => r.is_fraud === 1).length
    return { flagged, fraud, total: rows.length }
  }, [rows])

  return (
    <div className="space-y-4">
      <Panel title="Live authorization stream"
        subtitle="Replay of the scored synthetic environment. Ground truth is shown alongside the score because this is a lab, not production."
        right={
          <div className="flex items-center gap-2">
            <Badge className={done
              ? 'border-slate-600/40 bg-slate-600/10 text-slate-400'
              : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'}>
              {!done && <span className="live-dot mr-1 inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />}
              {done ? 'REPLAY COMPLETE' : live ? 'STREAMING' : 'PAUSED'}
            </Badge>
            <Button size="sm" variant="ghost" onClick={() => setLive(l => !l)}
              title={live ? 'Pause the feed' : 'Resume the feed'}>
              {live ? <><Pause size={12} aria-hidden="true" /> Pause</>
                    : <><Play size={12} aria-hidden="true" /> Resume</>}
            </Button>
          </div>
        }>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            ['Received', stats.total.toLocaleString(), 'text-slate-100'],
            ['Flagged high/critical', stats.flagged.toLocaleString(), 'text-red-400'],
            ['Ground-truth fraud', stats.fraud.toLocaleString(), 'text-amber-400'],
            ['Flag rate', stats.total ? pct(stats.flagged / stats.total, 1) : '—', 'text-sky-400'],
          ].map(([l, v, c]) => (
            <div key={l} className="rounded-lg border border-[#26314a] bg-[#111a2b] px-3 py-2.5">
              <div className="text-[9.5px] font-semibold uppercase tracking-wider text-slate-500">{l}</div>
              <div className={`tnum mt-0.5 text-[18px] font-semibold ${c}`}>{v}</div>
            </div>
          ))}
        </div>

        <label className="mt-3 flex cursor-pointer items-center gap-2 text-[11.5px] text-slate-400">
          <input type="checkbox" checked={onlyRisky} onChange={e => setOnlyRisky(e.target.checked)}
                 className="cursor-pointer accent-[#f79e1b]" />
          Show only high &amp; critical
        </label>
      </Panel>

      <Panel title={`Authorization feed${onlyRisky ? ' — filtered to high/critical' : ''}`} pad={false}>
        {err ? (
          <div className="p-4"><Empty icon={<Radio size={22} />}>{err}</Empty></div>
        ) : rows.length === 0 ? (
          <div className="p-4"><Skeleton rows={8} /></div>
        ) : shown.length === 0 ? (
          <Empty icon={<ShieldAlert size={22} />}>
            No high or critical transactions in the current window. Launch an attack campaign
            from <span className="text-slate-400">Red Team</span> to see the defence respond.
          </Empty>
        ) : (
          <div className="max-h-[600px] overflow-auto">
            <table className="w-full border-collapse">
              <caption className="sr-only">Live scored authorization transactions</caption>
              <thead>
                <tr>
                  <Th>Time</Th>
                  <Th>Transaction</Th>
                  <Th>Merchant</Th>
                  <Th align="right">Amount</Th>
                  <Th>Channel</Th>
                  <Th align="right">Risk</Th>
                  <Th>Band</Th>
                  <Th>Action</Th>
                  <Th align="center">Truth</Th>
                </tr>
              </thead>
              <tbody>
                {shown.map(t => (
                  <tr key={t.transaction_id}
                      className="row-in border-b border-[#131c2e] transition-colors duration-150 hover:bg-[#111a2b]">
                    <Td className="mono whitespace-nowrap text-slate-500">
                      {new Date(t.timestamp).toISOString().slice(11, 19)}
                    </Td>
                    <Td className="mono text-slate-400">{t.transaction_id.slice(0, 14)}</Td>
                    <Td className="max-w-[190px]">
                      <div className="truncate text-slate-300" title={t.merchant_name}>
                        {t.merchant_name}
                      </div>
                      <div className="mono text-[10px] text-slate-600">MCC {t.mcc}</div>
                    </Td>
                    <Td align="right" className="tnum whitespace-nowrap text-slate-200">
                      {money(t.amount, t.currency)}
                    </Td>
                    <Td className="text-slate-500">{t.channel}</Td>
                    <Td align="right" className="tnum font-semibold text-slate-100">
                      {t.risk_score.toFixed(3)}
                    </Td>
                    <Td>
                      <Badge className={RISK_BG[t.risk_level as RiskLevel]}>{t.risk_level}</Badge>
                    </Td>
                    <Td className="mono text-[10.5px] text-slate-400">{t.recommended_action}</Td>
                    <Td align="center">
                      {t.is_fraud === 1 ? (
                        <Badge className="border-amber-500/30 bg-amber-500/10 text-amber-300"
                               title={t.attack_type}>
                          {t.attack_type.slice(0, 14)}
                        </Badge>
                      ) : (
                        <span className="text-[10.5px] text-slate-700">legit</span>
                      )}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  )
}

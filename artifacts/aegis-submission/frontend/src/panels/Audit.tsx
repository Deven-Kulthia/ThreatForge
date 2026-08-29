import { useEffect, useState } from 'react'
import { FileClock, Rocket, ScanEye, Swords } from 'lucide-react'
import { api, type AuditEvent } from '../api'
import { Badge, Empty, ErrorNote, Panel, Skeleton, Td, Th } from '../ui'

const KIND: Record<string, { label: string; cls: string; icon: typeof Rocket }> = {
  environment_boot: { label: 'ENVIRONMENT', cls: 'border-sky-500/30 bg-sky-500/10 text-sky-300', icon: Rocket },
  attack_simulated: { label: 'RED TEAM', cls: 'border-amber-500/30 bg-amber-500/10 text-amber-300', icon: Swords },
  explanation_viewed: { label: 'ANALYST', cls: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300', icon: ScanEye },
}

export default function Audit({ nonce }: { nonce: number }) {
  const [events, setEvents] = useState<AuditEvent[] | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const load = () => {
    setEvents(null)
    void api.audit(80).then(r => setEvents(r.events))
      .catch(e => setErr(e instanceof Error ? e.message : 'Failed to load audit trail'))
  }
  useEffect(load, [nonce])

  return (
    <div className="space-y-4">
      {err && <ErrorNote onRetry={load}>{err}</ErrorNote>}

      <Panel title="Audit trail"
        subtitle="Append-only local record of every environment change, simulated campaign and analyst action. Model governance expects decisions to be reconstructable after the fact."
        right={<Badge className="border-[#26314a] bg-[#162034] text-slate-400">
          SQLite · stdlib · local only
        </Badge>}>
        <div className="flex flex-wrap gap-2">
          {Object.entries(KIND).map(([k, v]) => {
            const Icon = v.icon
            const n = events?.filter(e => e.kind === k).length ?? 0
            return (
              <Badge key={k} className={v.cls}>
                <Icon size={10} aria-hidden="true" /> {v.label} <span className="tnum">{n}</span>
              </Badge>
            )
          })}
        </div>
      </Panel>

      <Panel pad={false}>
        {events === null ? <div className="p-4"><Skeleton rows={8} /></div>
          : events.length === 0 ? (
            <Empty icon={<FileClock size={22} />}>No audit events recorded yet.</Empty>
          ) : (
            <div className="max-h-[620px] overflow-auto">
              <table className="w-full border-collapse">
                <caption className="sr-only">Audit event log, newest first</caption>
                <thead>
                  <tr>
                    <Th align="right">#</Th><Th>Timestamp (UTC)</Th><Th>Event</Th>
                    <Th>Actor</Th><Th>Detail</Th>
                  </tr>
                </thead>
                <tbody>
                  {events.map(e => {
                    const k = KIND[e.kind]
                    return (
                      <tr key={e.id} className="border-b border-[#131c2e] hover:bg-[#111a2b]">
                        <Td align="right" className="tnum text-slate-600">{e.id}</Td>
                        <Td className="mono whitespace-nowrap text-slate-500">
                          {e.ts.slice(0, 19).replace('T', ' ')}
                        </Td>
                        <Td>
                          {k ? <Badge className={k.cls}>{k.label}</Badge>
                             : <span className="mono text-[10.5px] text-slate-400">{e.kind}</span>}
                        </Td>
                        <Td className="text-slate-400">{e.actor}</Td>
                        <Td className="mono max-w-[520px] text-[10.5px] text-slate-500">
                          <div className="truncate" title={JSON.stringify(e.detail)}>
                            {Object.entries(e.detail).map(([k2, v]) => `${k2}=${String(v)}`).join('  ')}
                          </div>
                        </Td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
      </Panel>
    </div>
  )
}

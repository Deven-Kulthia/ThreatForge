import { useCallback, useEffect, useState } from 'react'
import {
  Activity, AlertTriangle, BarChart3, FileClock, Network, Play, Search, ShieldCheck, Swords,
} from 'lucide-react'
import { api, type EnvInfo } from './api'
import { Badge, Button, ErrorNote, Spinner, SyntheticTag } from './ui'
import Overview from './panels/Overview'
import Simulator from './panels/Simulator'
import Stream from './panels/Stream'
import Investigate from './panels/Investigate'
import NetworkGraph from './panels/NetworkGraph'
import Performance from './panels/Performance'
import Audit from './panels/Audit'

type TabId = 'overview' | 'simulator' | 'stream' | 'investigate' | 'graph' | 'performance' | 'audit'

// `side` groups the tabs into the brief's own red-team / blue-team framing: "you take on both
// sides of the problem". Both halves are first-class here — the red team declares what should
// catch each attack, the blue team reports back which declared signals it missed.
type Side = 'red' | 'blue' | null

const SIDE_LABEL: Record<'red' | 'blue', { text: string; cls: string }> = {
  red: { text: 'Red team', cls: 'text-rose-400/80' },
  blue: { text: 'Blue team', cls: 'text-sky-400/80' },
}

const TABS: { id: TabId; label: string; icon: typeof Activity; hint: string; side: Side }[] = [
  { id: 'overview', label: 'Overview', icon: ShieldCheck, hint: 'Executive posture', side: null },
  { id: 'simulator', label: 'Attack Simulator', icon: Swords, hint: 'Red team — generate attacks', side: 'red' },
  { id: 'stream', label: 'Live Stream', icon: Activity, hint: 'Blue team — authorization feed', side: 'blue' },
  { id: 'investigate', label: 'Investigate', icon: Search, hint: 'Blue team — alerts & explainability', side: 'blue' },
  { id: 'graph', label: 'Fraud Network', icon: Network, hint: 'Blue team — entity graph', side: 'blue' },
  { id: 'performance', label: 'Performance', icon: BarChart3, hint: 'Blue team — evaluation metrics', side: 'blue' },
  { id: 'audit', label: 'Audit Trail', icon: FileClock, hint: 'Append-only log', side: null },
]

export default function App() {
  const [tab, setTab] = useState<TabId>('overview')
  const [env, setEnv] = useState<EnvInfo | null>(null)
  const [booting, setBooting] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [nonce, setNonce] = useState(0)   // bumped whenever the environment changes

  const refresh = useCallback(async () => {
    try {
      // Ask health first: it always answers and reports readiness, so we never fire a
      // request we expect to 503. Keeps the console clean for anyone inspecting the demo.
      const h = await api.health()
      if (!h.ready) { setEnv(null); return }
      setEnv(await api.environment())
      setErr(null)
    } catch {
      setEnv(null)
    }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  const boot = async () => {
    setBooting(true)
    setErr(null)
    try {
      await api.boot({ n_cards: 700, n_merchants: 140, days: 30, seed: 42 })
      await refresh()
      setNonce(n => n + 1)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Failed to initialise environment')
    } finally {
      setBooting(false)
    }
  }

  const onChanged = useCallback(async () => {
    await refresh()
    setNonce(n => n + 1)
  }, [refresh])

  return (
    <div className="flex min-h-dvh flex-col bg-[#060910]">
      {/* ---------- top bar ---------- */}
      <header className="sticky top-0 z-30 border-b border-[#26314a] bg-[#0b1220]/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center gap-4 px-5 py-3">
          <div className="flex items-center gap-2.5">
            {/* Mastercard-adjacent identity mark, kept abstract — brand colour used for
                identity only, never for status. */}
            <span className="relative flex h-7 w-11 items-center" aria-hidden="true">
              <span className="absolute left-0 h-7 w-7 rounded-full bg-[#eb001b]" />
              <span className="absolute left-4 h-7 w-7 rounded-full bg-[#f79e1b] mix-blend-screen" />
            </span>
            <div className="leading-tight">
              <div className="text-[15px] font-semibold tracking-tight text-slate-50">Aegis</div>
              <div className="text-[10.5px] text-slate-500">AI Defence Lab · Payment Security</div>
            </div>
          </div>

          <div className="ml-2 hidden h-8 w-px bg-[#26314a] lg:block" />

          <p className="hidden max-w-md text-[11px] leading-snug text-slate-500 lg:block">
            Closed-loop <span className="text-rose-400/90">red team</span> /{' '}
            <span className="text-sky-400/90">blue team</span> system:{' '}
            <span className="text-slate-400">identify</span> →{' '}
            <span className="text-slate-400">generate</span> →{' '}
            <span className="text-slate-400">defend</span>
          </p>

          <div className="ml-auto flex items-center gap-2.5">
            <SyntheticTag />
            {env?.ready ? (
              <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                <span className="live-dot mr-0.5 inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
                ENVIRONMENT LIVE
              </Badge>
            ) : (
              <Badge className="border-slate-600/40 bg-slate-600/10 text-slate-400">OFFLINE</Badge>
            )}
          </div>
        </div>

        {/* ---------- tabs, grouped by red team / blue team ---------- */}
        <nav aria-label="Sections"
             className="mx-auto flex max-w-[1600px] items-center gap-1 overflow-x-auto px-4 pb-2">
          {TABS.map((t, i) => {
            const Icon = t.icon
            const active = tab === t.id
            const opensGroup = t.side !== null && TABS[i - 1]?.side !== t.side
            const closesGroup = t.side !== null && TABS[i + 1]?.side !== t.side
            return (
              <div key={t.id} className="flex shrink-0 items-center gap-1">
                {opensGroup && (
                  <span className="ml-2 flex shrink-0 items-center gap-1.5 pl-2
                                   border-l border-slate-700/60">
                    <span aria-hidden="true"
                          className={`size-1.5 rounded-full ${t.side === 'red' ? 'bg-rose-500' : 'bg-sky-500'}`} />
                    <span className={`text-[10px] font-semibold uppercase tracking-wider
                                     ${SIDE_LABEL[t.side as 'red' | 'blue'].cls}`}>
                      {SIDE_LABEL[t.side as 'red' | 'blue'].text}
                    </span>
                  </span>
                )}
                <button onClick={() => setTab(t.id)} title={t.hint}
                  aria-current={active ? 'page' : undefined}
                  className={`inline-flex shrink-0 cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5
                    text-[12px] font-medium transition-colors duration-200
                    ${active
                      ? 'bg-[#1c2942] text-slate-100 shadow-[inset_0_0_0_1px_#2f3f60]'
                      : 'text-slate-500 hover:bg-[#111a2b] hover:text-slate-300'}`}>
                  <Icon size={14} strokeWidth={2} aria-hidden="true" />
                  {t.label}
                </button>
                {closesGroup && <span aria-hidden="true" className="mr-1 h-5 w-px bg-slate-700/60" />}
              </div>
            )
          })}
        </nav>
      </header>

      {/* ---------- body ---------- */}
      <main className="mx-auto w-full max-w-[1600px] flex-1 px-5 py-5">
        {err && <div className="mb-4"><ErrorNote onRetry={boot}>{err}</ErrorNote></div>}

        {!env?.ready ? (
          <BootScreen booting={booting} onBoot={boot} />
        ) : (
          <div key={tab} className="fade-up">
            {tab === 'overview' && <Overview env={env} nonce={nonce} onGoto={setTab} />}
            {tab === 'simulator' && <Simulator onLaunched={onChanged} />}
            {tab === 'stream' && <Stream nonce={nonce} />}
            {tab === 'investigate' && <Investigate nonce={nonce} />}
            {tab === 'graph' && <NetworkGraph nonce={nonce} />}
            {tab === 'performance' && <Performance nonce={nonce} />}
            {tab === 'audit' && <Audit nonce={nonce} />}
          </div>
        )}
      </main>

      <footer className="border-t border-[#1a2337] px-5 py-3">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-4 gap-y-1 text-[10.5px] text-slate-600">
          <span>Mastercard Innovation Challenge 2026 · AI Defence Lab for Payment Security</span>
          <span className="text-slate-700">|</span>
          <span>100% synthetic data — no real cardholder data, PII or production payment data</span>
          <span className="text-slate-700">|</span>
          <span>Simulator is network-isolated by construction</span>
        </div>
      </footer>
    </div>
  )
}

function BootScreen({ booting, onBoot }: { booting: boolean; onBoot: () => void }) {
  return (
    <div className="mx-auto max-w-2xl pt-10 text-center fade-up">
      <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-[#26314a] bg-[#111a2b]">
        <ShieldCheck size={26} className="text-[#f79e1b]" strokeWidth={1.8} aria-hidden="true" />
      </div>
      <h1 className="text-[22px] font-semibold tracking-tight text-slate-100">
        Initialise the synthetic payment environment
      </h1>
      <p className="mx-auto mt-2.5 max-w-lg text-[13px] leading-relaxed text-slate-400">
        Generates a synthetic cardholder and merchant population, produces legitimate
        authorization traffic, then trains the defence on its own simulated attacks —
        the first turn of the closed loop.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-3 text-left sm:grid-cols-4">
        {[
          ['700', 'cardholders'], ['140', 'merchants'],
          ['30 days', 'of traffic'], ['25', 'attack vectors'],
        ].map(([v, l]) => (
          <div key={l} className="rounded-lg border border-[#26314a] bg-[#0b1220] px-3 py-2.5">
            <div className="tnum text-[17px] font-semibold text-slate-100">{v}</div>
            <div className="text-[10.5px] text-slate-500">{l}</div>
          </div>
        ))}
      </div>

      <div className="mt-7 flex items-center justify-center gap-3">
        <Button onClick={onBoot} disabled={booting}>
          {booting ? <Spinner label="Generating and training…" />
                   : <><Play size={14} strokeWidth={2.4} aria-hidden="true" /> Start environment</>}
        </Button>
      </div>

      {booting && (
        <p className="mt-3 text-[11px] text-slate-500">
          Training the cascade on 25 simulated attack campaigns — typically 5–15 seconds.
        </p>
      )}

      <div className="mx-auto mt-8 flex max-w-lg items-start gap-2.5 rounded-lg border border-sky-500/20 bg-sky-500/[0.06] px-3.5 py-3 text-left">
        <AlertTriangle size={15} className="mt-0.5 shrink-0 text-sky-400" aria-hidden="true" />
        <p className="text-[11.5px] leading-relaxed text-sky-200/80">
          Every record is synthetic and labelled as such. Card identifiers are synthetic
          network-style tokens, never PANs. The attack simulator has no network client and
          cannot reach any external system.
        </p>
      </div>
    </div>
  )
}

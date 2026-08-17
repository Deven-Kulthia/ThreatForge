/** Shared UI primitives, aligned to the generated design system.
 *  Small on purpose — the panels carry the substance. */
import type { ReactNode } from 'react'

export function Panel({ title, subtitle, right, children, className = '', pad = true }: {
  title?: string; subtitle?: string; right?: ReactNode
  children: ReactNode; className?: string; pad?: boolean
}) {
  return (
    <section className={`rounded-xl border border-[#26314a] bg-[#0b1220] ${className}`}>
      {(title || right) && (
        <header className="flex items-start justify-between gap-3 border-b border-[#1a2337] px-4 py-3">
          <div className="min-w-0">
            {title && (
              <h2 className="truncate text-[12.5px] font-semibold tracking-[0.01em] text-slate-200">
                {title}
              </h2>
            )}
            {subtitle && <p className="mt-0.5 text-[11px] leading-snug text-slate-500">{subtitle}</p>}
          </div>
          {right && <div className="shrink-0">{right}</div>}
        </header>
      )}
      <div className={pad ? 'p-4' : ''}>{children}</div>
    </section>
  )
}

const TONE = {
  default: 'text-slate-100',
  good: 'text-emerald-400',
  warn: 'text-amber-400',
  high: 'text-orange-400',
  bad: 'text-red-400',
  brand: 'text-[#f79e1b]',
  info: 'text-sky-400',
} as const

export function Stat({ label, value, sub, tone = 'default', icon }: {
  label: string; value: ReactNode; sub?: string
  tone?: keyof typeof TONE; icon?: ReactNode
}) {
  return (
    <div className="rounded-lg border border-[#26314a] bg-[#111a2b] px-3.5 py-3">
      <div className="flex items-center justify-between gap-2">
        <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
          {label}
        </div>
        {icon && <span className="text-slate-600">{icon}</span>}
      </div>
      <div className={`tnum mt-1.5 text-[26px] font-semibold leading-none ${TONE[tone]}`}>
        {value}
      </div>
      {sub && <div className="mt-1.5 text-[11px] leading-snug text-slate-500">{sub}</div>}
    </div>
  )
}

export function Badge({ children, className = '', title }: {
  children: ReactNode; className?: string; title?: string
}) {
  return (
    <span title={title}
      className={`inline-flex items-center gap-1 rounded border px-1.5 py-[3px] text-[10px] font-medium leading-none ${className}`}>
      {children}
    </span>
  )
}

export function Bar({ value, max = 1, tone = 'brand', height = 6 }: {
  value: number; max?: number; tone?: 'brand' | 'good' | 'warn' | 'bad' | 'info'; height?: number
}) {
  const tones = {
    brand: 'bg-[#f79e1b]', good: 'bg-emerald-500', warn: 'bg-amber-500',
    bad: 'bg-red-500', info: 'bg-sky-400',
  }
  const p = Math.min(100, Math.max(0, (value / max) * 100))
  return (
    <div className="w-full overflow-hidden rounded-full bg-[#1a2337]" style={{ height }}
         role="img" aria-label={`${p.toFixed(0)} percent`}>
      <div className={`h-full rounded-full ${tones[tone]} transition-[width] duration-500 ease-out`}
           style={{ width: `${p}%` }} />
    </div>
  )
}

export function SyntheticTag({ compact = false }: { compact?: boolean }) {
  return (
    <Badge className="border-sky-500/30 bg-sky-500/10 text-sky-300"
           title="All data in this system is synthetic. No real cardholder data, PII or production payment data is used.">
      {compact ? 'SYNTHETIC' : 'SYNTHETIC DATA'}
    </Badge>
  )
}

export function Empty({ children, icon }: { children: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 py-12 text-center">
      {icon && <span className="text-slate-700">{icon}</span>}
      <div className="max-w-sm text-[12px] leading-relaxed text-slate-500">{children}</div>
    </div>
  )
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-[12px] text-slate-400" role="status" aria-live="polite">
      <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#26314a] border-t-[#f79e1b]" />
      {label}
    </div>
  )
}

export function ErrorNote({ children, onRetry }: { children: ReactNode; onRetry?: () => void }) {
  return (
    <div role="alert"
      className="flex items-start justify-between gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2.5">
      <div className="text-[12px] leading-relaxed text-red-300">{children}</div>
      {onRetry && (
        <button onClick={onRetry}
          className="shrink-0 cursor-pointer rounded border border-red-500/40 px-2 py-1 text-[11px] font-medium text-red-200 transition-colors duration-200 hover:bg-red-500/20">
          Retry
        </button>
      )}
    </div>
  )
}

/** Skeleton placeholder — preferred over a long spinner for >1s loads. */
export function Skeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="relative h-7 overflow-hidden rounded bg-[#111a2b] sweep" />
      ))}
    </div>
  )
}

export function Button({ children, onClick, disabled, variant = 'primary', size = 'md', title, type }: {
  children: ReactNode; onClick?: () => void; disabled?: boolean
  variant?: 'primary' | 'ghost' | 'danger'; size?: 'sm' | 'md'
  title?: string; type?: 'button' | 'submit'
}) {
  const variants = {
    primary: 'bg-[#f79e1b] text-[#1a1204] hover:bg-[#ffb03d] border-transparent font-semibold',
    ghost: 'bg-[#162034] text-slate-200 hover:bg-[#1c2942] border-[#26314a]',
    danger: 'bg-red-500/15 text-red-300 hover:bg-red-500/25 border-red-500/40',
  }
  const sizes = { sm: 'px-2.5 py-1.5 text-[11.5px]', md: 'px-3.5 py-2 text-[12.5px]' }
  return (
    <button type={type ?? 'button'} onClick={onClick} disabled={disabled} title={title}
      className={`inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-lg border
        transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-40
        ${variants[variant]} ${sizes[size]}`}>
      {children}
    </button>
  )
}

/** Sortable, keyboard-reachable table header cell. */
export function Th({ children, className = '', align = 'left' }: {
  children: ReactNode; className?: string; align?: 'left' | 'right' | 'center'
}) {
  const a = { left: 'text-left', right: 'text-right', center: 'text-center' }[align]
  return (
    <th scope="col"
      className={`sticky top-0 z-10 border-b border-[#26314a] bg-[#0b1220] px-3 py-2
        text-[10px] font-semibold uppercase tracking-[0.07em] text-slate-500 ${a} ${className}`}>
      {children}
    </th>
  )
}

export function Td({ children, className = '', align = 'left' }: {
  children: ReactNode; className?: string; align?: 'left' | 'right' | 'center'
}) {
  const a = { left: 'text-left', right: 'text-right', center: 'text-center' }[align]
  return <td className={`px-3 py-2 text-[12px] ${a} ${className}`}>{children}</td>
}

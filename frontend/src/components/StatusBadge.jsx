const STYLES = {
  pending: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  completed: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  indexed: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  failed: 'bg-red-50 text-red-700 ring-red-600/20',
}

const NEUTRAL = 'bg-slate-50 text-slate-600 ring-slate-500/20'

/** Renders a task or document status. Unknown values degrade to a neutral chip. */
export default function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${STYLES[status] ?? NEUTRAL}`}
    >
      {status}
    </span>
  )
}

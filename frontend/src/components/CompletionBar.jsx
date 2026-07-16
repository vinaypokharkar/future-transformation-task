import { formatPercent } from '../utils/format'

/**
 * Completed vs pending as a proportional bar. Hand-rolled rather than pulling in
 * a charting library for a single two-segment ratio.
 */
export default function CompletionBar({ completed, pending }) {
  const total = completed + pending
  const completedPercent = total === 0 ? 0 : (completed / total) * 100

  if (total === 0) {
    return <p className="text-sm text-slate-500">No tasks yet — nothing to chart.</p>
  }

  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100">
        <div className="bg-emerald-500 transition-all" style={{ width: `${completedPercent}%` }} />
        <div className="flex-1 bg-amber-400" />
      </div>

      <dl className="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" aria-hidden="true" />
          <dt className="text-slate-500">Completed</dt>
          <dd className="font-semibold tabular-nums text-slate-900">{completed}</dd>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400" aria-hidden="true" />
          <dt className="text-slate-500">Pending</dt>
          <dd className="font-semibold tabular-nums text-slate-900">{pending}</dd>
        </div>
        <div className="flex items-center gap-2">
          <dt className="text-slate-500">Completion rate</dt>
          <dd className="font-semibold tabular-nums text-slate-900">{formatPercent(completed / total)}</dd>
        </div>
      </dl>
    </div>
  )
}

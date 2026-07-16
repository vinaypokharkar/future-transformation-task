export default function ProgressBar({ value, label }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
        <span className="truncate">{label}</span>
        <span className="tabular-nums">{value}%</span>
      </div>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200"
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-full rounded-full bg-indigo-600 transition-all duration-200" style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}

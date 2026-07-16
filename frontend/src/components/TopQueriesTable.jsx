export default function TopQueriesTable({ queries }) {
  const maxCount = Math.max(...queries.map((entry) => entry.count), 1)

  return (
    <table className="min-w-full text-sm">
      <thead>
        <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
          <th className="pb-2">Query</th>
          <th className="pb-2 text-right">Searches</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100">
        {queries.map((entry) => (
          <tr key={entry.query}>
            <td className="py-2.5 pr-4">
              <p className="truncate text-slate-900">{entry.query}</p>
              <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-indigo-500" style={{ width: `${(entry.count / maxCount) * 100}%` }} />
              </div>
            </td>
            <td className="py-2.5 text-right align-top font-semibold tabular-nums text-slate-900">{entry.count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

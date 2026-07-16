import HighlightedText from './HighlightedText'
import { formatScore } from '../utils/format'

export default function SearchResultCard({ result, query, rank }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <header className="mb-3 flex items-start justify-between gap-4">
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-medium tabular-nums text-slate-400">#{rank}</span>
          <h3 className="text-sm font-semibold text-slate-900">{result.document_title}</h3>
        </div>
        <span
          className="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium tabular-nums text-indigo-700 ring-1 ring-inset ring-indigo-600/20"
          title="Cosine similarity between the query and this chunk"
        >
          {formatScore(result.score)}
        </span>
      </header>

      <p className="text-sm leading-relaxed text-slate-700">
        <HighlightedText text={result.chunk_text} query={query} />
      </p>
    </article>
  )
}

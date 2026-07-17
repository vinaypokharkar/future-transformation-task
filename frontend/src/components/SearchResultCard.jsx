import HighlightedText from './HighlightedText'
import { formatScore } from '../utils/format'

// A lexical hit scores below the similarity floor by definition: the embedding
// model never saw the term, which is why the string match found it and the
// vector search did not. Without this label that low score reads as a bug, so
// every result says how it was found.
const MATCH_TYPES = {
  semantic: {
    label: 'semantic',
    title: 'Found by meaning — the embedding matched, not the words',
    className: 'bg-indigo-50 text-indigo-700 ring-indigo-600/20',
  },
  lexical: {
    label: 'lexical',
    title:
      'Found by exact text. The embedding model does not know this term, so its score sits below the similarity floor',
    className: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  },
  both: {
    label: 'both',
    title: 'Found by meaning and by exact text',
    className: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  },
}

export default function SearchResultCard({ result, query, rank }) {
  const match = MATCH_TYPES[result.match_type] ?? MATCH_TYPES.semantic

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <header className="mb-3 flex items-start justify-between gap-4">
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-medium tabular-nums text-slate-400">#{rank}</span>
          <h3 className="text-sm font-semibold text-slate-900">{result.document_title}</h3>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${match.className}`}
            title={match.title}
          >
            {match.label}
          </span>
          <span
            className="rounded-full bg-slate-50 px-2 py-0.5 text-xs font-medium tabular-nums text-slate-600 ring-1 ring-inset ring-slate-600/20"
            title="Cosine similarity between the query and this chunk"
          >
            {formatScore(result.score)}
          </span>
        </div>
      </header>

      <p className="text-sm leading-relaxed text-slate-700">
        <HighlightedText text={result.chunk_text} query={query} />
      </p>
    </article>
  )
}

import { useMemo } from 'react'

// Highlighting these would mark up most of the sentence and hide the signal.
const STOP_WORDS = new Set([
  'the', 'and', 'for', 'are', 'but', 'not', 'you', 'with', 'that', 'this',
  'have', 'has', 'from', 'they', 'what', 'when', 'how', 'can', 'does', 'did',
  'was', 'were', 'will', 'would', 'there', 'their', 'about', 'into', 'your',
])

/**
 * Marks query terms inside a result chunk.
 *
 * Note this is a lexical overlay on a semantic result: a good paraphrase match
 * may share no words with the chunk and legitimately highlight nothing. The
 * ranking comes from the embedding score, not from these highlights.
 */
export default function HighlightedText({ text, query }) {
  const terms = useMemo(() => {
    // Tokens are letters/digits only, so they are regex-safe by construction.
    const tokens = (query ?? '').toLowerCase().match(/[\p{L}\p{N}]+/gu) ?? []
    return [...new Set(tokens)].filter((token) => token.length > 2 && !STOP_WORDS.has(token))
  }, [query])

  const segments = useMemo(() => {
    if (terms.length === 0) return [text]
    return text.split(new RegExp(`(${terms.join('|')})`, 'giu'))
  }, [text, terms])

  if (terms.length === 0) return text

  return segments.map((segment, index) =>
    terms.includes(segment.toLowerCase()) ? (
      <mark key={index} className="rounded bg-yellow-200 px-0.5 text-slate-900">
        {segment}
      </mark>
    ) : (
      segment
    ),
  )
}

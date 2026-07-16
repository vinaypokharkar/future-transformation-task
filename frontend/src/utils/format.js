export function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export function formatFileSize(bytes) {
  if (typeof bytes !== 'number' || bytes < 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** The API sends completion_rate as a 0–1 fraction. */
export function formatPercent(fraction) {
  if (typeof fraction !== 'number') return '—'
  return `${Math.round(fraction * 100)}%`
}

/** Cosine similarity, shown to 3 dp so close results stay distinguishable. */
export function formatScore(score) {
  if (typeof score !== 'number') return '—'
  return score.toFixed(3)
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Button from '../components/Button'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import PageHeader from '../components/PageHeader'
import SearchResultCard from '../components/SearchResultCard'
import { LoadingState } from '../components/Spinner'
import { search } from '../api/search'
import { getErrorMessage } from '../api/client'

export default function SearchPage() {
  const [draft, setDraft] = useState('')
  // Kept separate from the input so results only change on submit, never per keystroke.
  const [submittedQuery, setSubmittedQuery] = useState('')

  const searchQuery = useQuery({
    queryKey: ['search', submittedQuery],
    queryFn: () => search(submittedQuery),
    enabled: submittedQuery.length > 0,
  })

  const handleSubmit = (event) => {
    event.preventDefault()
    setSubmittedQuery(draft.trim())
  }

  const results = searchQuery.data ?? []

  return (
    <>
      <PageHeader
        title="Semantic search"
        description="Meaning-based search over the knowledge base — paraphrases work, exact keywords are not required."
      />

      <form onSubmit={handleSubmit} className="mb-6 flex gap-2">
        <input
          type="search"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="e.g. how long do I have to claim expenses back?"
          aria-label="Search query"
          className="block w-full rounded-md border-0 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600"
        />
        <Button type="submit" disabled={!draft.trim() || searchQuery.isFetching} className="px-5">
          {searchQuery.isFetching ? 'Searching…' : 'Search'}
        </Button>
      </form>

      {!submittedQuery ? (
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <EmptyState
            title="Search the knowledge base"
            description="Ask a question in your own words. Results are ranked by cosine similarity against document chunks, so a close paraphrase still matches."
          />
        </div>
      ) : searchQuery.isLoading ? (
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <LoadingState label="Searching…" />
        </div>
      ) : searchQuery.isError ? (
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <ErrorState
            title="Search failed"
            message={getErrorMessage(searchQuery.error)}
            onRetry={() => searchQuery.refetch()}
          />
        </div>
      ) : results.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <EmptyState
            title="No relevant results"
            description="Nothing in the knowledge base scored above the similarity floor for this query. Returning nothing beats returning confident nonsense."
          />
        </div>
      ) : (
        <>
          <p className="mb-3 text-sm text-slate-500">
            {results.length} {results.length === 1 ? 'result' : 'results'} for “{submittedQuery}”
          </p>
          <div className="space-y-3">
            {results.map((result, index) => (
              <SearchResultCard
                key={`${result.document_id}-${index}`}
                result={result}
                query={submittedQuery}
                rank={index + 1}
              />
            ))}
          </div>
        </>
      )}
    </>
  )
}

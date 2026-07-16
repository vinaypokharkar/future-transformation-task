import Card from '../components/Card'
import CompletionBar from '../components/CompletionBar'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import PageHeader from '../components/PageHeader'
import { LoadingState } from '../components/Spinner'
import StatCard from '../components/StatCard'
import TopQueriesTable from '../components/TopQueriesTable'
import { getErrorMessage } from '../api/client'
import { useAnalyticsQuery } from '../hooks/useAnalytics'
import { formatPercent } from '../utils/format'

export default function AnalyticsPage() {
  const analyticsQuery = useAnalyticsQuery()

  if (analyticsQuery.isLoading) {
    return (
      <>
        <PageHeader title="Analytics" />
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <LoadingState label="Loading analytics…" />
        </div>
      </>
    )
  }

  if (analyticsQuery.isError) {
    return (
      <>
        <PageHeader title="Analytics" />
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <ErrorState
            title="Could not load analytics"
            message={getErrorMessage(analyticsQuery.error)}
            onRetry={() => analyticsQuery.refetch()}
          />
        </div>
      </>
    )
  }

  const { tasks, documents, search, activity } = analyticsQuery.data

  return (
    <>
      <PageHeader title="Analytics" description="Derived from activity logs and live table counts — nothing hardcoded." />

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total tasks" value={tasks.total} hint={`${formatPercent(tasks.completion_rate)} completed`} />
        <StatCard label="Documents" value={documents.total} hint={`${documents.indexed} indexed`} />
        <StatCard label="Indexed chunks" value={documents.total_chunks} hint="Searchable vectors" />
        <StatCard label="Searches" value={search.total_searches} hint={`${activity.logins_last_7_days} logins in 7 days`} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Completed vs pending">
          <CompletionBar completed={tasks.completed} pending={tasks.pending} />
        </Card>

        <Card title="Most searched queries">
          {search.top_queries.length === 0 ? (
            <EmptyState title="No searches logged yet" description="Run a search and it will appear here." />
          ) : (
            <TopQueriesTable queries={search.top_queries} />
          )}
        </Card>
      </div>
    </>
  )
}

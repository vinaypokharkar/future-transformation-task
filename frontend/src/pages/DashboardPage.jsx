import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Card from '../components/Card'
import CompletionBar from '../components/CompletionBar'
import ErrorState from '../components/ErrorState'
import PageHeader from '../components/PageHeader'
import { LoadingState } from '../components/Spinner'
import StatCard from '../components/StatCard'
import { listTasks } from '../api/tasks'
import { getErrorMessage } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { useAuth } from '../auth/AuthContext'
import { useAnalyticsQuery } from '../hooks/useAnalytics'
import { formatPercent } from '../utils/format'

export default function DashboardPage() {
  const { user, isAdmin } = useAuth()

  return (
    <>
      <PageHeader
        title={`Welcome back, ${user.email}`}
        description={isAdmin ? 'System-wide overview.' : 'Where your tasks stand right now.'}
      />
      {isAdmin ? <AdminSummary /> : <UserSummary />}
    </>
  )
}

function AdminSummary() {
  const analyticsQuery = useAnalyticsQuery()

  if (analyticsQuery.isLoading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <LoadingState label="Loading overview…" />
      </div>
    )
  }

  if (analyticsQuery.isError) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <ErrorState
          title="Could not load the overview"
          message={getErrorMessage(analyticsQuery.error)}
          onRetry={() => analyticsQuery.refetch()}
        />
      </div>
    )
  }

  const { tasks, documents, search } = analyticsQuery.data

  return (
    <>
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total tasks" value={tasks.total} hint={`${tasks.pending} still pending`} />
        <StatCard label="Documents" value={documents.total} hint={`${documents.indexed} indexed`} />
        <StatCard label="Indexed chunks" value={documents.total_chunks} hint="Searchable vectors" />
        <StatCard label="Searches" value={search.total_searches} hint="All time" />
      </div>

      <Card title="Task progress" action={<CardLink to="/analytics">Full analytics</CardLink>}>
        <CompletionBar completed={tasks.completed} pending={tasks.pending} />
      </Card>
    </>
  )
}

function UserSummary() {
  // The server scopes this to the caller's own tasks regardless of params.
  const tasksQuery = useQuery({
    queryKey: queryKeys.tasks({}),
    queryFn: () => listTasks(),
  })

  if (tasksQuery.isLoading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <LoadingState label="Loading your tasks…" />
      </div>
    )
  }

  if (tasksQuery.isError) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <ErrorState
          title="Could not load your tasks"
          message={getErrorMessage(tasksQuery.error)}
          onRetry={() => tasksQuery.refetch()}
        />
      </div>
    )
  }

  const tasks = tasksQuery.data ?? []
  const completed = tasks.filter((task) => task.status === 'completed').length
  const pending = tasks.length - completed

  return (
    <>
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Assigned to you" value={tasks.length} />
        <StatCard label="Pending" value={pending} hint="Waiting on you" />
        <StatCard
          label="Completed"
          value={completed}
          hint={tasks.length > 0 ? `${formatPercent(completed / tasks.length)} done` : undefined}
        />
      </div>

      <Card title="Your progress" action={<CardLink to="/tasks">View tasks</CardLink>}>
        <CompletionBar completed={completed} pending={pending} />
      </Card>
    </>
  )
}

function CardLink({ to, children }) {
  return (
    <Link to={to} className="text-sm font-medium text-indigo-600 hover:text-indigo-500">
      {children}
    </Link>
  )
}

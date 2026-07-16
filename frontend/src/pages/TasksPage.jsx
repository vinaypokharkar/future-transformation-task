import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Button from '../components/Button'
import Card from '../components/Card'
import CreateTaskForm from '../components/CreateTaskForm'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import Modal from '../components/Modal'
import PageHeader from '../components/PageHeader'
import TaskFilterBar from '../components/TaskFilterBar'
import TaskTable from '../components/TaskTable'
import { createTask, listTasks, updateTaskStatus } from '../api/tasks'
import { getErrorMessage } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { useAuth } from '../auth/AuthContext'
import { useDocumentsQuery } from '../hooks/useDocuments'
import { useUsersQuery } from '../hooks/useUsers'

const NO_FILTERS = { status: '', assigned_to: '' }

export default function TasksPage() {
  const { user, isAdmin } = useAuth()
  const queryClient = useQueryClient()

  const [filters, setFilters] = useState(NO_FILTERS)
  const [isCreateOpen, setCreateOpen] = useState(false)

  // Filter state is part of the query key, so changing a dropdown refetches
  // GET /tasks with real query params rather than filtering client-side.
  const tasksQuery = useQuery({
    queryKey: queryKeys.tasks(filters),
    queryFn: () => listTasks(filters),
  })

  const usersQuery = useUsersQuery({ enabled: isAdmin })
  // Only the admin create-task modal needs documents; regular users never see it.
  const documentsQuery = useDocumentsQuery({}, { enabled: isAdmin })

  const invalidateTaskViews = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.allTasks() })
    // Task counts feed the analytics page and the dashboard.
    queryClient.invalidateQueries({ queryKey: queryKeys.analytics() })
  }

  const statusMutation = useMutation({
    mutationFn: ({ task, status }) => updateTaskStatus(task.id, status),
    onSuccess: invalidateTaskViews,
  })

  const createMutation = useMutation({
    mutationFn: createTask,
    onSuccess: () => {
      invalidateTaskViews()
      setCreateOpen(false)
    },
  })

  const tasks = tasksQuery.data ?? []
  const isFiltered = Boolean(filters.status || filters.assigned_to)

  return (
    <>
      <PageHeader
        title="Tasks"
        description={isAdmin ? 'All tasks across the team.' : 'Tasks assigned to you.'}
        action={
          isAdmin && (
            <Button
              onClick={() => {
                createMutation.reset()
                setCreateOpen(true)
              }}
            >
              New task
            </Button>
          )
        }
      />

      <div className="mb-5 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <TaskFilterBar
          filters={filters}
          onChange={setFilters}
          assignees={usersQuery.data ?? []}
          showAssigneeFilter={isAdmin}
        />
      </div>

      {statusMutation.isError && (
        <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {getErrorMessage(statusMutation.error, 'Could not update the task status.')}
        </p>
      )}

      <Card bodyClassName="">
        {tasksQuery.isLoading ? (
          <TaskTableSkeleton />
        ) : tasksQuery.isError ? (
          <ErrorState
            title="Could not load tasks"
            message={getErrorMessage(tasksQuery.error)}
            onRetry={() => tasksQuery.refetch()}
          />
        ) : tasks.length === 0 ? (
          <EmptyState
            title={isFiltered ? 'No tasks match these filters' : 'No tasks yet'}
            description={
              isFiltered
                ? 'Try clearing the filters to see everything available to you.'
                : isAdmin
                  ? 'Create the first task and assign it to someone.'
                  : 'Nothing is assigned to you right now.'
            }
            action={
              isFiltered ? (
                <Button variant="secondary" onClick={() => setFilters(NO_FILTERS)}>
                  Clear filters
                </Button>
              ) : null
            }
          />
        ) : (
          <TaskTable
            tasks={tasks}
            currentUserId={user.id}
            // Status is per-assignee, so the toggle only appears for the
            // viewer's own row. An admin who is not on the task has nothing to
            // toggle — my_status is null — and correcting someone else's status
            // is an explicit action, not a button that silently targets them.
            canToggle={(task) => task.my_status != null}
            onToggleStatus={(task, status) => statusMutation.mutate({ task, status })}
            togglingTaskId={statusMutation.isPending ? statusMutation.variables?.task.id : null}
          />
        )}
      </Card>

      <Modal open={isCreateOpen} title="Create task" onClose={() => setCreateOpen(false)}>
        <CreateTaskForm
          users={usersQuery.data ?? []}
          documents={documentsQuery.data ?? []}
          isSubmitting={createMutation.isPending}
          error={createMutation.isError ? getErrorMessage(createMutation.error, 'Could not create the task.') : null}
          onSubmit={(payload) => createMutation.mutate(payload)}
          onCancel={() => setCreateOpen(false)}
        />
      </Modal>
    </>
  )
}

function TaskTableSkeleton() {
  return (
    <div className="divide-y divide-slate-100" role="status" aria-label="Loading tasks">
      {[0, 1, 2].map((row) => (
        <div key={row} className="flex items-center gap-4 px-5 py-4">
          <div className="h-4 flex-1 animate-pulse rounded bg-slate-100" />
          <div className="h-4 w-20 animate-pulse rounded bg-slate-100" />
          <div className="h-4 w-28 animate-pulse rounded bg-slate-100" />
        </div>
      ))}
    </div>
  )
}

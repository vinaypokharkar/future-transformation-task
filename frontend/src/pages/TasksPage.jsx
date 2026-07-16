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
    // userId is omitted when you tick your own row, so the server updates the
    // caller's assignment. An admin ticking someone else's sends it explicitly.
    mutationFn: ({ task, assignee, status }) =>
      updateTaskStatus(task.id, status, assignee.user_id === user.id ? undefined : assignee.user_id),
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
            // You may always tick your own row; an admin may tick anybody's.
            // This mirrors the server rule rather than replacing it — a
            // non-admin who forges the request still gets a 404.
            canToggleAssignee={(_task, assignee) => isAdmin || assignee.user_id === user.id}
            onToggleAssignee={(task, assignee, status) =>
              statusMutation.mutate({ task, assignee, status })
            }
            // Keyed by task AND assignee: two people on one task each have
            // their own control, and a task-level key would spin both.
            togglingKey={
              statusMutation.isPending
                ? `${statusMutation.variables?.task.id}:${statusMutation.variables?.assignee.user_id}`
                : null
            }
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

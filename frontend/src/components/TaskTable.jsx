import Button from './Button'
import Spinner from './Spinner'
import StatusBadge from './StatusBadge'
import { formatDate } from '../utils/format'

/**
 * Presentational. `canToggle` decides whether the current viewer may flip their
 * own status on a given task.
 *
 * Two statuses are on show and they are not the same thing: each assignee's own
 * state, and the task's rollup (complete only when everybody is done). Showing
 * just the rollup would make a half-finished shared task look untouched.
 */
export default function TaskTable({ tasks, currentUserId, canToggle = () => false, onToggleStatus, togglingTaskId }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <th className="px-5 py-3">Task</th>
            <th className="px-5 py-3">Task status</th>
            <th className="px-5 py-3">Assignees</th>
            <th className="px-5 py-3">Due</th>
            <th className="px-5 py-3 text-right">Your status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {tasks.map((task) => {
            const isToggling = togglingTaskId === task.id
            const nextStatus = task.my_status === 'pending' ? 'completed' : 'pending'
            const shared = task.assignee_count > 1

            return (
              <tr key={task.id} className="align-top hover:bg-slate-50">
                <td className="px-5 py-3">
                  <p className="font-medium text-slate-900">{task.title}</p>
                  {task.description && <p className="mt-0.5 max-w-md text-slate-500">{task.description}</p>}
                </td>

                <td className="px-5 py-3">
                  <StatusBadge status={task.status} />
                  {shared && (
                    <p className="mt-1 text-xs text-slate-500">
                      {task.completed_count} of {task.assignee_count} done
                    </p>
                  )}
                </td>

                <td className="px-5 py-3">
                  <ul className="space-y-1">
                    {task.assignees.map((assignee) => {
                      const isYou = assignee.user_id === currentUserId
                      return (
                        <li key={assignee.user_id} className="flex items-center gap-2">
                          <span
                            className={`inline-block h-1.5 w-1.5 rounded-full ${
                              assignee.status === 'completed' ? 'bg-emerald-500' : 'bg-amber-400'
                            }`}
                            aria-hidden="true"
                          />
                          <span className={isYou ? 'font-medium text-slate-900' : 'text-slate-600'}>
                            {assignee.full_name || assignee.email}
                            {isYou && <span className="ml-1 text-xs text-slate-400">(you)</span>}
                          </span>
                        </li>
                      )
                    })}
                  </ul>
                </td>

                <td className="px-5 py-3 text-slate-600">{formatDate(task.due_date)}</td>

                <td className="px-5 py-3 text-right">
                  {/* my_status is null for an admin who is not assigned: there is
                      no "your status" to show, because they have no stake. */}
                  {task.my_status == null ? (
                    <span className="text-xs text-slate-400">not assigned</span>
                  ) : canToggle(task) ? (
                    <Button
                      variant={task.my_status === 'pending' ? 'primary' : 'secondary'}
                      disabled={isToggling}
                      onClick={() => onToggleStatus(task, nextStatus)}
                    >
                      {isToggling && <Spinner className="h-3.5 w-3.5" />}
                      {task.my_status === 'pending' ? 'Mark complete' : 'Reopen'}
                    </Button>
                  ) : (
                    <StatusBadge status={task.my_status} />
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

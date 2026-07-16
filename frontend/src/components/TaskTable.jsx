import Spinner from './Spinner'
import StatusBadge from './StatusBadge'
import { formatDate } from '../utils/format'

/**
 * Presentational. `canToggleAssignee(task, assignee)` decides whether the
 * viewer may flip a given person's status.
 *
 * The assignees column is a checklist, not a label. Status is per-assignee, so
 * each person gets their own control: you can always tick your own row, and an
 * admin can tick anybody's. Rows you may not change still render as checkboxes
 * so progress is visible — just disabled.
 *
 * Two statuses are on show and they are not the same thing: each assignee's own
 * state, and the task rollup (complete only when everybody is done). Showing
 * only the rollup would make a half-finished shared task look untouched.
 */
export default function TaskTable({
  tasks,
  currentUserId,
  canToggleAssignee = () => false,
  onToggleAssignee,
  togglingKey,
}) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <th className="px-5 py-3">Task</th>
            <th className="px-5 py-3">Task status</th>
            <th className="px-5 py-3">Assignees &mdash; tick to mark complete</th>
            <th className="px-5 py-3">Due</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {tasks.map((task) => {
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
                  <ul className="space-y-1.5">
                    {task.assignees.map((assignee) => {
                      const isYou = assignee.user_id === currentUserId
                      const editable = canToggleAssignee(task, assignee)
                      const done = assignee.status === 'completed'
                      const busy = togglingKey === `${task.id}:${assignee.user_id}`

                      return (
                        <li key={assignee.user_id}>
                          <label
                            className={`flex items-center gap-2.5 ${
                              editable ? 'cursor-pointer' : 'cursor-default'
                            }`}
                            title={
                              editable
                                ? `Mark ${isYou ? 'yourself' : assignee.full_name || assignee.email} ${
                                    done ? 'pending' : 'complete'
                                  }`
                                : 'Only an admin can change someone else’s status'
                            }
                          >
                            {busy ? (
                              <Spinner className="h-4 w-4" />
                            ) : (
                              <input
                                type="checkbox"
                                className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
                                checked={done}
                                disabled={!editable}
                                onChange={() =>
                                  onToggleAssignee(task, assignee, done ? 'pending' : 'completed')
                                }
                              />
                            )}
                            <span
                              className={
                                done
                                  ? 'text-slate-400 line-through'
                                  : isYou
                                    ? 'font-medium text-slate-900'
                                    : 'text-slate-600'
                              }
                            >
                              {assignee.full_name || assignee.email}
                            </span>
                            {isYou && <span className="text-xs text-slate-400">(you)</span>}
                          </label>
                        </li>
                      )
                    })}
                  </ul>
                </td>

                <td className="px-5 py-3 text-slate-600">{formatDate(task.due_date)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

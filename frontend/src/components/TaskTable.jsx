import Button from './Button'
import Spinner from './Spinner'
import StatusBadge from './StatusBadge'
import { formatDate } from '../utils/format'

/**
 * Presentational. `usersById` resolves assignee IDs to names; `canToggle`
 * decides whether the current viewer may flip a given task's status.
 */
export default function TaskTable({ tasks, usersById = {}, canToggle = () => false, onToggleStatus, togglingTaskId }) {
  const assigneeLabel = (id) => {
    const user = usersById[id]
    return user ? user.full_name || user.email : `User #${id}`
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <th className="px-5 py-3">Task</th>
            <th className="px-5 py-3">Status</th>
            <th className="px-5 py-3">Assignee</th>
            <th className="px-5 py-3">Due</th>
            <th className="px-5 py-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {tasks.map((task) => {
            const isToggling = togglingTaskId === task.id
            const nextStatus = task.status === 'pending' ? 'completed' : 'pending'

            return (
              <tr key={task.id} className="align-top hover:bg-slate-50">
                <td className="px-5 py-3">
                  <p className="font-medium text-slate-900">{task.title}</p>
                  {task.description && <p className="mt-0.5 max-w-md text-slate-500">{task.description}</p>}
                </td>
                <td className="px-5 py-3">
                  <StatusBadge status={task.status} />
                </td>
                <td className="px-5 py-3 text-slate-600">{assigneeLabel(task.assigned_to)}</td>
                <td className="px-5 py-3 text-slate-600">{formatDate(task.due_date)}</td>
                <td className="px-5 py-3 text-right">
                  {canToggle(task) ? (
                    <Button
                      variant={task.status === 'pending' ? 'primary' : 'secondary'}
                      disabled={isToggling}
                      onClick={() => onToggleStatus(task, nextStatus)}
                    >
                      {isToggling && <Spinner className="h-3.5 w-3.5" />}
                      {task.status === 'pending' ? 'Mark complete' : 'Reopen'}
                    </Button>
                  ) : (
                    <span className="text-xs text-slate-400">—</span>
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

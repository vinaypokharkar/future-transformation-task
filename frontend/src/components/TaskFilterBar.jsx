import Button from './Button'
import { SelectField } from './Field'

const STATUS_OPTIONS = [
  { value: 'pending', label: 'Pending' },
  { value: 'completed', label: 'Completed' },
]

/**
 * Presentational. The parent owns filter state and turns it into real query
 * params on GET /tasks — this component only reports changes.
 */
export default function TaskFilterBar({ filters, onChange, assignees = [], showAssigneeFilter = false }) {
  const isFiltered = Boolean(filters.status || filters.assigned_to)

  const assigneeOptions = assignees.map((user) => ({
    value: String(user.id),
    label: user.full_name || user.email,
  }))

  return (
    <div className="flex flex-wrap items-end gap-3">
      <SelectField
        id="filter-status"
        label="Status"
        className="w-44"
        placeholder="All statuses"
        options={STATUS_OPTIONS}
        value={filters.status}
        onChange={(event) => onChange({ ...filters, status: event.target.value })}
      />

      {showAssigneeFilter && (
        <SelectField
          id="filter-assignee"
          label="Assignee"
          className="w-56"
          placeholder="All assignees"
          options={assigneeOptions}
          value={filters.assigned_to}
          onChange={(event) => onChange({ ...filters, assigned_to: event.target.value })}
        />
      )}

      {isFiltered && (
        <Button variant="secondary" onClick={() => onChange({ status: '', assigned_to: '' })}>
          Clear filters
        </Button>
      )}
    </div>
  )
}

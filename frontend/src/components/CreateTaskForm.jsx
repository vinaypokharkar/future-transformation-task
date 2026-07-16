import { useState } from 'react'
import Button from './Button'
import { SelectField, TextAreaField, TextField } from './Field'

const EMPTY_FORM = { title: '', description: '', document_id: '', due_date: '' }

/**
 * Presentational. The parent owns the mutation; this only collects and reports.
 */
export default function CreateTaskForm({ users = [], documents = [], onSubmit, onCancel, isSubmitting, error }) {
  const [form, setForm] = useState(EMPTY_FORM)
  // Checkboxes rather than a multi-select: a <select multiple> hides the fact
  // that more than one person can be picked, and requires ctrl-click to use.
  const [assigneeIds, setAssigneeIds] = useState([])

  const setField = (name) => (event) => setForm((prev) => ({ ...prev, [name]: event.target.value }))

  const toggleAssignee = (id) =>
    setAssigneeIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))

  const handleSubmit = (event) => {
    event.preventDefault()
    onSubmit({
      title: form.title.trim(),
      description: form.description.trim(),
      assignee_ids: assigneeIds,
      // IDs travel as strings through <select>; the API expects numbers.
      document_id: form.document_id ? Number(form.document_id) : '',
      due_date: form.due_date,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <TextField
        id="task-title"
        label="Title"
        required
        maxLength={255}
        value={form.title}
        onChange={setField('title')}
        placeholder="Review the expenses policy"
      />

      <TextAreaField
        id="task-description"
        label="Description"
        value={form.description}
        onChange={setField('description')}
        placeholder="What needs doing, and what does done look like?"
      />

      <fieldset>
        <legend className="mb-1.5 block text-sm font-medium text-slate-700">
          Assign to{' '}
          <span className="font-normal text-slate-500">
            ({assigneeIds.length} selected — each person completes it separately)
          </span>
        </legend>
        <div className="max-h-44 space-y-1 overflow-y-auto rounded-md border border-slate-200 p-2">
          {users.length === 0 && <p className="px-1 py-2 text-sm text-slate-500">No users available.</p>}
          {users.map((user) => (
            <label
              key={user.id}
              className="flex cursor-pointer items-center gap-2.5 rounded px-2 py-1.5 text-sm hover:bg-slate-50"
            >
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                checked={assigneeIds.includes(user.id)}
                onChange={() => toggleAssignee(user.id)}
              />
              <span className="text-slate-900">{user.full_name || user.email}</span>
              <span className="text-xs capitalize text-slate-400">{user.role}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <SelectField
          id="task-document"
          label="Related document (optional)"
          placeholder="None"
          options={documents.map((document) => ({ value: String(document.id), label: document.title }))}
          value={form.document_id}
          onChange={setField('document_id')}
        />
        <TextField id="task-due" label="Due date (optional)" type="date" value={form.due_date} onChange={setField('due_date')} />
      </div>

      {error && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}

      <div className="flex justify-end gap-2 pt-1">
        <Button variant="secondary" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting || !form.title.trim() || assigneeIds.length === 0}>
          {isSubmitting ? 'Creating…' : `Create task${assigneeIds.length > 1 ? ` for ${assigneeIds.length} people` : ''}`}
        </Button>
      </div>
    </form>
  )
}

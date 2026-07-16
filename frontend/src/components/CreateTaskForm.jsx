import { useState } from 'react'
import Button from './Button'
import { SelectField, TextAreaField, TextField } from './Field'

const EMPTY_FORM = { title: '', description: '', assigned_to: '', document_id: '', due_date: '' }

/**
 * Presentational. The parent owns the mutation; this only collects and reports.
 */
export default function CreateTaskForm({ users = [], documents = [], onSubmit, onCancel, isSubmitting, error }) {
  const [form, setForm] = useState(EMPTY_FORM)

  const setField = (name) => (event) => setForm((prev) => ({ ...prev, [name]: event.target.value }))

  const handleSubmit = (event) => {
    event.preventDefault()
    onSubmit({
      title: form.title.trim(),
      description: form.description.trim(),
      // IDs travel as strings through <select>; the API expects numbers.
      assigned_to: Number(form.assigned_to),
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

      <SelectField
        id="task-assignee"
        label="Assign to"
        required
        placeholder="Select a user…"
        options={users.map((user) => ({ value: String(user.id), label: user.full_name || user.email }))}
        value={form.assigned_to}
        onChange={setField('assigned_to')}
      />

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
        <Button type="submit" disabled={isSubmitting || !form.title.trim() || !form.assigned_to}>
          {isSubmitting ? 'Creating…' : 'Create task'}
        </Button>
      </div>
    </form>
  )
}

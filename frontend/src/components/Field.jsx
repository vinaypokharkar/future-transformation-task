const CONTROL_CLASS =
  'block w-full rounded-md border-0 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 disabled:bg-slate-50 disabled:text-slate-500'

function Label({ htmlFor, children }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block text-sm font-medium text-slate-700">
      {children}
    </label>
  )
}

export function TextField({ id, label, className = '', ...props }) {
  return (
    <div className={className}>
      {label && <Label htmlFor={id}>{label}</Label>}
      <input id={id} className={CONTROL_CLASS} {...props} />
    </div>
  )
}

export function TextAreaField({ id, label, className = '', rows = 3, ...props }) {
  return (
    <div className={className}>
      {label && <Label htmlFor={id}>{label}</Label>}
      <textarea id={id} rows={rows} className={CONTROL_CLASS} {...props} />
    </div>
  )
}

export function SelectField({ id, label, options, placeholder, className = '', ...props }) {
  return (
    <div className={className}>
      {label && <Label htmlFor={id}>{label}</Label>}
      <select id={id} className={CONTROL_CLASS} {...props}>
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

import { useEffect, useRef, useState } from 'react'

/**
 * A dropdown that opens to a list of checkboxes, for picking several options.
 *
 * Not a native <select multiple>: it hides that multiple selection is even
 * possible, needs ctrl-click to use, and renders differently on every platform.
 * A closed trigger that summarises the selection is what people expect.
 *
 * Presentational — the parent owns `value` and `onChange`.
 */
export default function MultiSelectField({
  id,
  label,
  options = [],
  value = [],
  onChange,
  placeholder = 'Select…',
  hint,
  emptyMessage = 'No options available.',
}) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)

  // Close on an outside click or Escape. Without this the panel stays open
  // behind whatever the user clicks next, and there is no keyboard way out.
  useEffect(() => {
    if (!open) return undefined

    const onPointerDown = (event) => {
      if (!containerRef.current?.contains(event.target)) setOpen(false)
    }

    const onKeyDown = (event) => {
      if (event.key !== 'Escape') return
      setOpen(false)
      // Escape must close the top layer only. Modal listens for Escape on
      // document too, so without this both fire and one keypress closes the
      // dropdown *and* the whole form — discarding everything typed.
      //
      // Capture phase is what makes stopPropagation work here: both listeners
      // sit on document, so stopping during the bubble phase would be too late
      // to prevent a sibling. Capture runs first and halts the rest.
      event.stopPropagation()
    }

    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown, true)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown, true)
    }
  }, [open])

  const toggle = (optionValue) => {
    const next = value.includes(optionValue)
      ? value.filter((v) => v !== optionValue)
      : [...value, optionValue]
    onChange(next)
  }

  const selected = options.filter((o) => value.includes(o.value))

  // Name a couple of people, but fall back to a count rather than overflowing
  // the trigger once the list gets long.
  const summary =
    selected.length === 0
      ? placeholder
      : selected.length <= 2
        ? selected.map((o) => o.label).join(', ')
        : `${selected.length} selected`

  return (
    <div ref={containerRef} className="relative">
      <label id={`${id}-label`} className="mb-1.5 block text-sm font-medium text-slate-700">
        {label}
        {hint && <span className="ml-1 font-normal text-slate-500">{hint}</span>}
      </label>

      <button
        type="button"
        id={id}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-labelledby={`${id}-label`}
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between rounded-md border border-slate-300 bg-white px-3 py-2 text-left text-sm text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      >
        <span className={selected.length === 0 ? 'text-slate-400' : undefined}>{summary}</span>
        <span className="ml-2 flex items-center gap-2">
          {selected.length > 0 && (
            <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
              {selected.length}
            </span>
          )}
          <svg
            className={`h-4 w-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
              clipRule="evenodd"
            />
          </svg>
        </span>
      </button>

      {open && (
        <div
          role="listbox"
          aria-multiselectable="true"
          aria-labelledby={`${id}-label`}
          className="absolute z-20 mt-1 max-h-56 w-full overflow-y-auto rounded-md border border-slate-200 bg-white py-1 shadow-lg"
        >
          {options.length === 0 && <p className="px-3 py-2 text-sm text-slate-500">{emptyMessage}</p>}

          {options.map((option) => {
            const checked = value.includes(option.value)
            return (
              <label
                key={option.value}
                role="option"
                aria-selected={checked}
                className="flex cursor-pointer items-center gap-2.5 px-3 py-2 text-sm hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  checked={checked}
                  onChange={() => toggle(option.value)}
                />
                <span className="flex-1 text-slate-900">{option.label}</span>
                {option.meta && <span className="text-xs capitalize text-slate-400">{option.meta}</span>}
              </label>
            )
          })}
        </div>
      )}
    </div>
  )
}

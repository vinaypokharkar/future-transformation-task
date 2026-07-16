import { useRef, useState } from 'react'

const ACCEPTED_EXTENSIONS = ['.txt', '.pdf']

/**
 * Presentational drag-and-drop target. Reports a chosen file to the parent,
 * which owns the upload mutation.
 */
export default function Dropzone({ onFileSelected, disabled = false }) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef(null)

  const handleFiles = (fileList) => {
    const file = fileList?.[0]
    if (file) onFileSelected(file)
  }

  const handleDrop = (event) => {
    event.preventDefault()
    setIsDragging(false)
    if (disabled) return
    handleFiles(event.dataTransfer.files)
  }

  const handleDragOver = (event) => {
    // Without preventDefault the browser navigates to the dropped file instead.
    event.preventDefault()
    if (!disabled) setIsDragging(true)
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={() => setIsDragging(false)}
      className={`rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
        isDragging ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 bg-slate-50'
      } ${disabled ? 'opacity-60' : ''}`}
    >
      <p className="text-sm font-medium text-slate-700">Drag and drop a document here</p>
      <p className="mt-1 text-xs text-slate-500">.txt or .pdf — text-based PDFs only (scanned pages cannot be indexed)</p>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(',')}
        className="hidden"
        disabled={disabled}
        onChange={(event) => {
          handleFiles(event.target.files)
          // Reset so re-selecting the same file still fires onChange.
          event.target.value = ''
        }}
      />

      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className="mt-4 rounded-md bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-inset ring-slate-300 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Browse files
      </button>
    </div>
  )
}

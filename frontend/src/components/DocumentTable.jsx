import Button from './Button'
import StatusBadge from './StatusBadge'
import { formatDate, formatFileSize } from '../utils/format'

export default function DocumentTable({ documents, canDelete = false, onDelete, deletingDocumentId }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <th className="px-5 py-3">Document</th>
            <th className="px-5 py-3">Type</th>
            <th className="px-5 py-3">Size</th>
            <th className="px-5 py-3">Index status</th>
            <th className="px-5 py-3">Chunks</th>
            <th className="px-5 py-3">Uploaded</th>
            {canDelete && <th className="px-5 py-3 text-right">Action</th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {documents.map((document) => (
            <tr key={document.id} className="hover:bg-slate-50">
              <td className="px-5 py-3">
                <p className="font-medium text-slate-900">{document.title}</p>
                <p className="mt-0.5 text-xs text-slate-500">{document.original_filename}</p>
              </td>
              <td className="px-5 py-3">
                <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs uppercase text-slate-600">
                  {document.file_type}
                </span>
              </td>
              <td className="px-5 py-3 text-slate-600">{formatFileSize(document.file_size)}</td>
              <td className="px-5 py-3">
                <StatusBadge status={document.status} />
              </td>
              <td className="px-5 py-3 tabular-nums text-slate-600">{document.chunk_count}</td>
              <td className="px-5 py-3 text-slate-600">{formatDate(document.created_at)}</td>
              {canDelete && (
                <td className="px-5 py-3 text-right">
                  <Button
                    variant="danger"
                    disabled={deletingDocumentId === document.id}
                    onClick={() => onDelete(document)}
                  >
                    {deletingDocumentId === document.id ? 'Deleting…' : 'Delete'}
                  </Button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

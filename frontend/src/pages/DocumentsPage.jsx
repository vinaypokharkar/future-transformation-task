import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import Card from '../components/Card'
import DocumentTable from '../components/DocumentTable'
import Dropzone from '../components/Dropzone'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import PageHeader from '../components/PageHeader'
import ProgressBar from '../components/ProgressBar'
import { LoadingState } from '../components/Spinner'
import { deleteDocument, uploadDocument } from '../api/documents'
import { getErrorMessage } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { useAuth } from '../auth/AuthContext'
import { useDocumentsQuery } from '../hooks/useDocuments'
import RoleGate from '../auth/RoleGate'

const ALLOWED_EXTENSIONS = ['txt', 'pdf']
const MAX_FILE_BYTES = 10 * 1024 * 1024

/** Mirrors the server's own validation so an obvious mistake fails instantly. */
function validateFile(file) {
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return `Unsupported file type ".${extension}". Upload a .txt or .pdf file.`
  }
  if (file.size > MAX_FILE_BYTES) {
    return 'That file is larger than the 10 MB limit.'
  }
  return null
}

export default function DocumentsPage() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()

  const [progress, setProgress] = useState(0)
  const [uploadingName, setUploadingName] = useState(null)
  const [validationError, setValidationError] = useState(null)

  const documentsQuery = useDocumentsQuery()

  const uploadMutation = useMutation({
    mutationFn: (file) => uploadDocument(file, setProgress),
    onSuccess: () => {
      // Without this the new document never appears until a manual refresh.
      queryClient.invalidateQueries({ queryKey: queryKeys.allDocuments() })
      queryClient.invalidateQueries({ queryKey: queryKeys.analytics() })
    },
    onSettled: () => {
      setUploadingName(null)
      setProgress(0)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (document) => deleteDocument(document.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.allDocuments() })
      queryClient.invalidateQueries({ queryKey: queryKeys.analytics() })
    },
  })

  const handleFileSelected = (file) => {
    const error = validateFile(file)
    setValidationError(error)
    if (error) return

    uploadMutation.reset()
    setUploadingName(file.name)
    setProgress(0)
    uploadMutation.mutate(file)
  }

  const handleDelete = (document) => {
    if (window.confirm(`Delete "${document.title}"? Its indexed chunks will be removed too.`)) {
      deleteMutation.mutate(document)
    }
  }

  const documents = documentsQuery.data ?? []

  return (
    <>
      <PageHeader
        title="Documents"
        description="The knowledge base behind semantic search. Only indexed documents are searchable."
      />

      <RoleGate role="admin">
        <Card title="Upload a document" className="mb-6">
          <Dropzone onFileSelected={handleFileSelected} disabled={uploadMutation.isPending} />

          {uploadMutation.isPending && (
            <div className="mt-4">
              <ProgressBar value={progress} label={`Uploading ${uploadingName}`} />
              {progress === 100 && (
                <p className="mt-2 text-xs text-slate-500">
                  Upload complete — extracting text and building embeddings. This can take a few seconds.
                </p>
              )}
            </div>
          )}

          {validationError && (
            <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
              {validationError}
            </p>
          )}

          {uploadMutation.isError && (
            <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
              {getErrorMessage(uploadMutation.error, 'Upload failed.')}
            </p>
          )}

          {uploadMutation.isSuccess && (
            <p className="mt-4 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700" role="status">
              Uploaded “{uploadMutation.data.title}” — status:{' '}
              <span className="font-medium">{uploadMutation.data.status}</span>
              {uploadMutation.data.chunk_count > 0 && ` (${uploadMutation.data.chunk_count} chunks indexed)`}
            </p>
          )}
        </Card>
      </RoleGate>

      {deleteMutation.isError && (
        <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {getErrorMessage(deleteMutation.error, 'Could not delete the document.')}
        </p>
      )}

      <Card title={`Knowledge base (${documents.length})`} bodyClassName="">
        {documentsQuery.isLoading ? (
          <LoadingState label="Loading documents…" />
        ) : documentsQuery.isError ? (
          <ErrorState
            title="Could not load documents"
            message={getErrorMessage(documentsQuery.error)}
            onRetry={() => documentsQuery.refetch()}
          />
        ) : documents.length === 0 ? (
          <EmptyState
            title="No documents yet"
            description={
              isAdmin
                ? 'Upload a .txt or .pdf above to start building the knowledge base.'
                : 'An admin has not uploaded any documents yet. Search will return no results until they do.'
            }
          />
        ) : (
          <DocumentTable
            documents={documents}
            canDelete={isAdmin}
            onDelete={handleDelete}
            deletingDocumentId={deleteMutation.isPending ? deleteMutation.variables?.id : null}
          />
        )}
      </Card>
    </>
  )
}

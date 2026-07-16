import { useQuery } from '@tanstack/react-query'
import { listDocuments } from '../api/documents'
import { queryKeys } from '../api/queryKeys'

export function useDocumentsQuery(filters = {}, { enabled = true } = {}) {
  return useQuery({
    queryKey: queryKeys.documents(filters),
    queryFn: () => listDocuments(filters),
    enabled,
  })
}

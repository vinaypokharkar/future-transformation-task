import { useQuery } from '@tanstack/react-query'
import { fetchAnalytics } from '../api/analytics'
import { queryKeys } from '../api/queryKeys'

/** GET /analytics is admin-only — gate with `enabled` for regular users. */
export function useAnalyticsQuery({ enabled = true } = {}) {
  return useQuery({
    queryKey: queryKeys.analytics(),
    queryFn: fetchAnalytics,
    enabled,
  })
}

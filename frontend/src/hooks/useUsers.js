import { useQuery } from '@tanstack/react-query'
import { listUsers } from '../api/users'
import { queryKeys } from '../api/queryKeys'

/**
 * GET /users is admin-only, so callers must gate this with `enabled`
 * to avoid a guaranteed 403 for regular users.
 */
export function useUsersQuery({ enabled = true } = {}) {
  return useQuery({
    queryKey: queryKeys.users(),
    queryFn: listUsers,
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

/** Builds an id -> user lookup for resolving assignee names. */
export function toUsersById(users = []) {
  return Object.fromEntries(users.map((user) => [user.id, user]))
}

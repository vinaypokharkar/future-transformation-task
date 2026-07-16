/**
 * Centralised so an invalidation always matches the key a page fetched with.
 * Drifting key strings are the usual cause of "the UI shows stale data after a mutation".
 */
export const queryKeys = {
  tasks: (filters = {}) => ['tasks', filters],
  allTasks: () => ['tasks'],
  documents: (filters = {}) => ['documents', filters],
  allDocuments: () => ['documents'],
  users: () => ['users'],
  analytics: () => ['analytics'],
}

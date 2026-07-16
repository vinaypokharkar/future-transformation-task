import { useAuth } from './AuthContext'

/**
 * Hides admin-only UI. Presentation only — never a security boundary.
 */
export default function RoleGate({ role = 'admin', children, fallback = null }) {
  const { user } = useAuth()
  return user?.role === role ? children : fallback
}

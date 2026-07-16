import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import ErrorBoundary from './components/ErrorBoundary'
import ProtectedRoute from './auth/ProtectedRoute'
import { useAuth } from './auth/AuthContext'
import AnalyticsPage from './pages/AnalyticsPage'
import DashboardPage from './pages/DashboardPage'
import DocumentsPage from './pages/DocumentsPage'
import LoginPage from './pages/LoginPage'
import SearchPage from './pages/SearchPage'
import TasksPage from './pages/TasksPage'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/tasks', label: 'Tasks' },
  { to: '/documents', label: 'Documents' },
  { to: '/search', label: 'Search' },
]

const ADMIN_NAV_ITEMS = [{ to: '/analytics', label: 'Analytics' }]

/** Wraps authenticated pages in the shell. Admin-only nav is hidden for users,
 *  which is presentation only — the server enforces the actual boundary. */
function AuthenticatedLayout() {
  const { user, logout, isAdmin } = useAuth()
  const navItems = isAdmin ? [...NAV_ITEMS, ...ADMIN_NAV_ITEMS] : NAV_ITEMS

  return (
    <AppLayout user={user} navItems={navItems} onLogout={logout}>
      <Outlet />
    </AppLayout>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<AuthenticatedLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/search" element={<SearchPage />} />
          </Route>
        </Route>

        {/* Nested so admin routes get the same shell while carrying the extra guard. */}
        <Route element={<ProtectedRoute requireAdmin />}>
          <Route element={<AuthenticatedLayout />}>
            <Route path="/analytics" element={<AnalyticsPage />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ErrorBoundary>
  )
}

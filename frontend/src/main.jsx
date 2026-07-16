import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.jsx'
import { AuthProvider } from './auth/AuthContext'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // A 401 means the session is gone; the axios interceptor is already
      // tearing it down, so retrying only delays the redirect.
      retry: (failureCount, error) =>
        error?.response?.status !== 401 && failureCount < 2,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
})

// AuthProvider depends on both useNavigate and useQueryClient, so Router and
// QueryClientProvider must sit above it.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  </StrictMode>,
)

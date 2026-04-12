import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export function ProtectedRoute() {
  const token = useAuthStore((s) => s.token)
  const loc = useLocation()

  if (!token) {
    return <Navigate to="/" replace state={{ from: `${loc.pathname}${loc.search}` }} />
  }
  return <Outlet />
}

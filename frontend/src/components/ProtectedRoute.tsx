import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export function ProtectedRoute() {
  const token = useAuthStore((s) => s.token)
  const loc = useLocation()

  if (!token) {
    // Оформление заказа без входа: иначе Navigate на тот же /order/* не монтирует Outlet → белый экран.
    if (loc.pathname.startsWith('/order')) {
      return <Outlet />
    }
    return <Navigate to="/order/tariff" replace state={{ from: `${loc.pathname}${loc.search}` }} />
  }
  return <Outlet />
}

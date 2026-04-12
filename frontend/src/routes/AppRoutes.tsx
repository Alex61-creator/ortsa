import { Navigate, Route, Routes } from 'react-router-dom'
import { MainLayout } from '@/layouts/MainLayout'
import { DashboardLayout } from '@/layouts/DashboardLayout'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { LandingPage } from '@/pages/LandingPage'
import { AuthCallbackPage } from '@/pages/AuthCallbackPage'
import { ProfilePage } from '@/pages/dashboard/ProfilePage'
import { NatalDataPage } from '@/pages/dashboard/NatalDataPage'
import { OrdersPage } from '@/pages/dashboard/OrdersPage'
import { OrderTariffPage } from '@/pages/order/OrderTariffPage'
import { OrderDataPage } from '@/pages/order/OrderDataPage'
import { OrderConfirmPage } from '@/pages/order/OrderConfirmPage'
import { OrderStatusPage } from '@/pages/order/OrderStatusPage'
import { ReportDownloadPage } from '@/pages/ReportDownloadPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<LandingPage />} />
      </Route>
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<DashboardLayout />}>
          <Route index element={<Navigate to="profile" replace />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="natal" element={<NatalDataPage />} />
          <Route path="orders" element={<OrdersPage />} />
        </Route>
        <Route path="/order" element={<MainLayout />}>
          <Route index element={<Navigate to="tariff" replace />} />
          <Route path="tariff" element={<OrderTariffPage />} />
          <Route path="data" element={<OrderDataPage />} />
          <Route path="confirm" element={<OrderConfirmPage />} />
          <Route path="status/:orderId" element={<OrderStatusPage />} />
        </Route>
        <Route path="/reports/:orderId" element={<MainLayout />}>
          <Route index element={<ReportDownloadPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

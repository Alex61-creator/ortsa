import { Navigate, Route, Routes } from 'react-router-dom'
import { AdminLayout } from '@/layouts/AdminLayout'
import { AccessDeniedPage } from '@/pages/AccessDeniedPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { AuthCallbackPage } from '@/pages/AuthCallbackPage'
import { LoginPage } from '@/pages/LoginPage'
import { OrdersPage } from '@/pages/OrdersPage'
import { TariffsPage } from '@/pages/TariffsPage'
import { UsersPage } from '@/pages/UsersPage'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { FunnelPage } from '@/pages/FunnelPage'
import { PaymentsPage } from '@/pages/PaymentsPage'
import { TasksPage } from '@/pages/TasksPage'
import { PromosPage } from '@/pages/PromosPage'
import { FlagsPage } from '@/pages/FlagsPage'
import { HealthPage } from '@/pages/HealthPage'
import { ActionLogPage } from '@/pages/ActionLogPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { PromptsPage } from '@/pages/PromptsPage'
import { CampaignAnalyticsPage } from '@/pages/CampaignAnalyticsPage'
import { GrowthEconomicsPage } from '@/pages/GrowthEconomicsPage'
import { OneTimeSalesPage } from '@/pages/OneTimeSalesPage'
import { PromoAnalyticsPage } from '@/pages/PromoAnalyticsPage'
import { ReportOptionsAnalyticsPage } from '@/pages/ReportOptionsAnalyticsPage'
import { SubscriptionsPage } from '@/pages/SubscriptionsPage'
import { LlmSettingsPage } from '@/pages/LlmSettingsPage'
import { LlmAnalyticsPage } from '@/pages/LlmAnalyticsPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route path="/access-denied" element={<AccessDeniedPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AdminLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="funnel" element={<FunnelPage />} />
          <Route path="growth" element={<GrowthEconomicsPage />} />
          <Route path="campaigns" element={<CampaignAnalyticsPage />} />
          <Route path="one-time-sales" element={<OneTimeSalesPage />} />
          <Route path="report-options" element={<ReportOptionsAnalyticsPage />} />
          <Route path="promo-analytics" element={<PromoAnalyticsPage />} />
          <Route path="subscriptions" element={<SubscriptionsPage />} />
          <Route path="orders" element={<OrdersPage />} />
          <Route path="payments" element={<PaymentsPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="tasks" element={<TasksPage />} />
          <Route path="promos" element={<PromosPage />} />
          <Route path="prompts" element={<PromptsPage />} />
          <Route path="tariffs" element={<TariffsPage />} />
          <Route path="flags" element={<FlagsPage />} />
          <Route path="health" element={<HealthPage />} />
          <Route path="log" element={<ActionLogPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="llm-settings" element={<LlmSettingsPage />} />
          <Route path="llm-analytics" element={<LlmAnalyticsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

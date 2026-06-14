import { createBrowserRouter } from 'react-router-dom'
import { RootLayout } from '@/components/layout/RootLayout'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { ListPage } from '@/pages/ListPage'
import { ProductDetailPage } from '@/pages/ProductDetailPage'
import { VariantPickerPage } from '@/pages/VariantPickerPage'
import { NotificationsPage } from '@/pages/NotificationsPage'
import { HistoryPage } from '@/pages/HistoryPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      {
        path: '/login',
        element: <LoginPage />,
      },
      {
        element: <ProtectedRoute />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'list', element: <ListPage /> },
          { path: 'products/:id', element: <ProductDetailPage /> },
          { path: 'products/:id/variants', element: <VariantPickerPage /> },
          { path: 'notifications', element: <NotificationsPage /> },
          { path: 'history', element: <HistoryPage /> },
          { path: 'settings', element: <SettingsPage /> },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

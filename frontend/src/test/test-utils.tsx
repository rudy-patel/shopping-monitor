import { render, type RenderResult } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  MemoryRouter,
  RouterProvider,
  createMemoryRouter,
  type MemoryRouterProps,
  type Router,
} from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import { CurrencyProvider } from '@/contexts/CurrencyContext'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { router } from '@/routes'

interface RenderWithProvidersOptions {
  route?: string
  routerProps?: MemoryRouterProps
  authenticated?: boolean
}

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
}

export function ProviderStack({
  children,
  queryClient = createTestQueryClient(),
}: {
  children: React.ReactNode
  queryClient?: QueryClient
}) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ThemeProvider>
          <CurrencyProvider>{children}</CurrencyProvider>
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export function renderWithProviders(
  ui: React.ReactElement,
  { route = '/', routerProps, authenticated = false }: RenderWithProvidersOptions = {},
) {
  if (authenticated) {
    localStorage.setItem('shopping-monitor-dev-auth', 'true')
  }

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <ProviderStack>
        <MemoryRouter initialEntries={[route]} {...routerProps}>
          {children}
        </MemoryRouter>
      </ProviderStack>
    )
  }

  return render(ui, { wrapper: Wrapper })
}

export interface RenderAppResult extends RenderResult {
  router: Router
}

export function renderApp(
  initialRoute = '/',
  {
    authenticated = false,
    state,
  }: { authenticated?: boolean; state?: unknown } = {},
): RenderAppResult {
  if (authenticated) {
    localStorage.setItem('shopping-monitor-dev-auth', 'true')
  }

  const memoryRouter = createMemoryRouter(router.routes, {
    initialEntries: [{ pathname: initialRoute, state }],
  })

  const result = render(
    <ProviderStack>
      <RouterProvider router={memoryRouter} />
    </ProviderStack>,
  )

  return { ...result, router: memoryRouter }
}

export function clearAuthStorage() {
  localStorage.removeItem('shopping-monitor-dev-auth')
  localStorage.removeItem('theme')
  localStorage.removeItem('display-currency')
}

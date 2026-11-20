import { lazy, Suspense } from 'react'
import { createBrowserRouter, RouterProvider, Outlet } from 'react-router-dom'
import PublicLayout from '../components/layout/PublicLayout'

// Eager-load landing (above the fold)
import LandingPage from '../features/landing/LandingPage'

// Lazy-load heavier routes
const ApplyPage = lazy(() => import('../features/borrower/ApplyPage'))
const ResultPage = lazy(() => import('../features/borrower/ResultPage'))
const NotFoundPage = lazy(() => import('./NotFoundPage'))

function LoadingFallback() {
  return (
    <div style={{ padding: '4rem', textAlign: 'center', color: 'var(--sec)', fontSize: 14 }}>
      Loading…
    </div>
  )
}

const router = createBrowserRouter([
  {
    element: (
      <PublicLayout>
        <Suspense fallback={<LoadingFallback />}>
          <Outlet />
        </Suspense>
      </PublicLayout>
    ),
    children: [
      { index: true, element: <LandingPage /> },
      { path: 'apply', element: <ApplyPage /> },
      { path: 'applications/:id/result', element: <ResultPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export default function AppRouter() {
  return <RouterProvider router={router} />
}

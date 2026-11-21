import { lazy, Suspense } from 'react'
import { createBrowserRouter, RouterProvider, Outlet } from 'react-router-dom'
import PublicLayout from '../components/layout/PublicLayout'

// Eager-load landing (above the fold)
import LandingPage from '../features/landing/LandingPage'

// Lazy-load heavier routes
const ApplyPage = lazy(() => import('../features/borrower/ApplyPage'))
const ResultPage = lazy(() => import('../features/borrower/ResultPage'))
const BankQueuePage = lazy(() => import('../features/bank/Queue'))
const BankCaseViewPage = lazy(() => import('../features/bank/CaseView'))
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
      // Bank officer routes
      { path: 'bank/queue', element: <BankQueuePage /> },
      { path: 'bank/case/:applicationId', element: <BankCaseViewPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export default function AppRouter() {
  return <RouterProvider router={router} />
}

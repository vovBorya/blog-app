import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { SignInPage } from '../features/auth/pages/SignInPage.tsx'
import { SignUpPage } from '../features/auth/pages/SignUpPage.tsx'
import { PaymentPage } from '../features/payment/pages/PaymentPage.tsx'
import { CreatePostPage } from '../features/posts/pages/CreatePostPage.tsx'
import { PostListPage } from '../features/posts/pages/PostListPage.tsx'
import { AppLayout } from '../shared/ui/AppLayout.tsx'
import { GuestRoute } from '../shared/ui/GuestRoute.tsx'
import { ProtectedRoute } from '../shared/ui/ProtectedRoute.tsx'

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<PostListPage />} />
          <Route element={<GuestRoute />}>
            <Route path="sign-in" element={<SignInPage />} />
            <Route path="sign-up" element={<SignUpPage />} />
          </Route>
          <Route element={<ProtectedRoute />}>
            <Route path="posts/new" element={<CreatePostPage />} />
            <Route path="payment" element={<PaymentPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

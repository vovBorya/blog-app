import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { Providers } from './app/providers.tsx'
import { AppRouter } from './app/router.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Providers>
      <AppRouter />
    </Providers>
  </StrictMode>,
)

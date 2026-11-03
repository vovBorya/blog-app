import { ApolloProvider } from '@apollo/client/react'
import { CssBaseline, ThemeProvider } from '@mui/material'
import type { ReactNode } from 'react'
import { Provider } from 'react-redux'

import { SessionRestore } from '../features/auth/SessionRestore.tsx'
import { apolloClient } from '../shared/api/client.ts'
import { store } from './store.ts'
import { theme } from './theme.ts'

type ProvidersProps = {
  children: ReactNode
}

export function Providers({ children }: ProvidersProps) {
  return (
    <Provider store={store}>
      <ApolloProvider client={apolloClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <SessionRestore />
          {children}
        </ThemeProvider>
      </ApolloProvider>
    </Provider>
  )
}

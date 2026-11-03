import { Container } from '@mui/material'
import { Outlet } from 'react-router-dom'

import { AppHeader } from './AppHeader.tsx'

export function AppLayout() {
  return (
    <>
      <AppHeader />
      <Container sx={{ py: 4 }}>
        <Outlet />
      </Container>
    </>
  )
}

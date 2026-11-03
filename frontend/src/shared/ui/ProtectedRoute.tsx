import { Box, CircularProgress } from '@mui/material'
import { Navigate, Outlet } from 'react-router-dom'

import { useAppSelector } from '../../app/hooks.ts'

export function ProtectedRoute() {
  const status = useAppSelector((state) => state.auth.status)

  if (status === 'unknown') {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (status !== 'authenticated') {
    return <Navigate to="/sign-in" replace />
  }

  return <Outlet />
}

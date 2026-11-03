import { useMutation } from '@apollo/client/react'
import { AppBar, Button, Stack, Toolbar, Typography } from '@mui/material'
import { useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'

import { useAppDispatch, useAppSelector } from '../../app/hooks.ts'
import { DELETE_TOKEN_COOKIE_MUTATION } from '../../features/auth/api/operations.ts'
import { setAnonymous } from '../../features/auth/model/authSlice.ts'
import { apolloClient } from '../api/client.ts'

export function AppHeader() {
  const dispatch = useAppDispatch()
  const status = useAppSelector((state) => state.auth.status)
  const user = useAppSelector((state) => state.auth.user)
  const [signOutError, setSignOutError] = useState<string | null>(null)
  const [deleteTokenCookie, { loading }] = useMutation(DELETE_TOKEN_COOKIE_MUTATION)

  async function handleSignOut() {
    setSignOutError(null)
    try {
      await deleteTokenCookie()
      dispatch(setAnonymous())
      await apolloClient.clearStore()
    } catch {
      setSignOutError('Could not sign out. Try again.')
    }
  }

  return (
    <AppBar position="static">
      <Toolbar sx={{ gap: 1 }}>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Blog
        </Typography>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
          <Button color="inherit" component={RouterLink} to="/">
            Posts
          </Button>
          <Button color="inherit" component={RouterLink} to="/posts/new">
            Create
          </Button>
          <Button color="inherit" component={RouterLink} to="/payment">
            Payment
          </Button>
          {status === 'authenticated' && user ? (
            <>
              <Typography variant="body2">{user.username}</Typography>
              <Button color="inherit" onClick={() => void handleSignOut()} disabled={loading}>
                Sign out
              </Button>
            </>
          ) : null}
          {status === 'anonymous' ? (
            <>
              <Button color="inherit" component={RouterLink} to="/sign-in">
                Sign in
              </Button>
              <Button color="inherit" component={RouterLink} to="/sign-up">
                Sign up
              </Button>
            </>
          ) : null}
        </Stack>
        {signOutError ? (
          <Typography variant="caption" role="alert" sx={{ color: 'warning.light' }}>
            {signOutError}
          </Typography>
        ) : null}
      </Toolbar>
    </AppBar>
  )
}

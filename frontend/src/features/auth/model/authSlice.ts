import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'

export type SessionStatus = 'unknown' | 'authenticated' | 'anonymous'

export type AuthUser = {
  id: string
  email: string | null
  username: string
  firstName: string
  lastName: string
}

export type AuthUserInput = {
  id: string
  email: string | null
  username: string
  firstName?: string | null
  lastName?: string | null
}

type AuthState = {
  status: SessionStatus
  user: AuthUser | null
}

const initialState: AuthState = {
  status: 'unknown',
  user: null,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setAuthenticated(state, action: PayloadAction<AuthUserInput>) {
      const user = action.payload
      state.status = 'authenticated'
      state.user = {
        id: user.id,
        email: user.email ?? null,
        username: user.username,
        firstName: user.firstName ?? '',
        lastName: user.lastName ?? '',
      }
    },
    setAnonymous(state) {
      state.status = 'anonymous'
      state.user = null
    },
  },
})

export const { setAuthenticated, setAnonymous } = authSlice.actions
export const authReducer = authSlice.reducer

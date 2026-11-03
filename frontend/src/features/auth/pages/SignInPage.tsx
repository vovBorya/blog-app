import { useMutation } from '@apollo/client/react'
import { Alert, Button, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'

import { useAppDispatch } from '../../../app/hooks.ts'
import { SIGN_IN_MUTATION } from '../api/operations.ts'
import type { SignInData } from '../api/operations.ts'
import { isSupportedPhoneNumber } from '../phone.ts'
import { setAuthenticated } from '../model/authSlice.ts'

type SignInMode = 'email' | 'phone'

type SignInForm = {
  identifier: string
  password: string
}

export function SignInPage() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const [mode, setMode] = useState<SignInMode>('email')
  const [formError, setFormError] = useState<string | null>(null)
  const [signIn, { loading }] = useMutation<SignInData>(SIGN_IN_MUTATION)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignInForm>({
    defaultValues: { identifier: '', password: '' },
  })

  async function onSubmit(values: SignInForm) {
    setFormError(null)

    if (mode === 'phone') {
      if (!isSupportedPhoneNumber(values.identifier)) {
        setFormError('Enter a valid phone number.')
        return
      }
      setFormError('Phone sign-in is not available.')
      return
    }

    try {
      const result = await signIn({
        variables: {
          input: {
            email: values.identifier.trim(),
            password: values.password,
          },
        },
      })
      const payload = result.data?.signIn
      if (!payload?.success || !payload.user) {
        setFormError(payload?.errors?.join(' ') || 'Sign in failed.')
        return
      }
      dispatch(setAuthenticated(payload.user))
      void navigate('/')
    } catch {
      setFormError('Could not reach the server.')
    }
  }

  return (
    <Stack
      component="form"
      spacing={2}
      onSubmit={(event) => void handleSubmit(onSubmit)(event)}
      sx={{ maxWidth: 420, mx: 'auto' }}
    >
      <Typography variant="h4" component="h1">
        Sign in
      </Typography>
      <ToggleButtonGroup
        exclusive
        value={mode}
        onChange={(_event, value: SignInMode | null) => {
          if (value) {
            setMode(value)
            setFormError(null)
          }
        }}
        aria-label="Sign-in method"
      >
        <ToggleButton value="email">Email</ToggleButton>
        <ToggleButton value="phone">Phone</ToggleButton>
      </ToggleButtonGroup>
      {formError ? <Alert severity="error">{formError}</Alert> : null}
      <TextField
        label={mode === 'email' ? 'Email' : 'Phone number'}
        type={mode === 'email' ? 'email' : 'tel'}
        autoComplete={mode === 'email' ? 'email' : 'tel'}
        helperText={
          errors.identifier?.message ??
          (mode === 'phone' ? 'Include a country code, for example +14155552671.' : undefined)
        }
        error={Boolean(errors.identifier)}
        {...register('identifier', { required: 'This field is required.' })}
      />
      <TextField
        label="Password"
        type="password"
        autoComplete="current-password"
        helperText={errors.password?.message}
        error={Boolean(errors.password)}
        {...register('password', {
          required: mode === 'email' ? 'Password is required.' : false,
        })}
      />
      <Button type="submit" variant="contained" disabled={loading}>
        Sign in
      </Button>
    </Stack>
  )
}

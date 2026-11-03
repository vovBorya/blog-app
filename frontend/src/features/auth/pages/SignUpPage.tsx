import { useMutation } from '@apollo/client/react'
import { Alert, Button, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'

import { useAppDispatch } from '../../../app/hooks.ts'
import { SIGN_UP_MUTATION } from '../api/operations.ts'
import type { SignUpData } from '../api/operations.ts'
import { setAuthenticated } from '../model/authSlice.ts'

type SignUpForm = {
  email: string
  username: string
  password: string
  firstName: string
  lastName: string
}

export function SignUpPage() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const [formError, setFormError] = useState<string | null>(null)
  const [signUp, { loading }] = useMutation<SignUpData>(SIGN_UP_MUTATION)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignUpForm>({
    defaultValues: {
      email: '',
      username: '',
      password: '',
      firstName: '',
      lastName: '',
    },
  })

  async function onSubmit(values: SignUpForm) {
    setFormError(null)
    try {
      const result = await signUp({
        variables: {
          input: {
            email: values.email.trim(),
            username: values.username.trim(),
            password: values.password,
            firstName: values.firstName.trim(),
            lastName: values.lastName.trim(),
          },
        },
      })
      const payload = result.data?.signUp
      if (!payload?.success || !payload.user) {
        setFormError(payload?.errors?.join(' ') || 'Sign up failed.')
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
        Sign up
      </Typography>
      {formError ? <Alert severity="error">{formError}</Alert> : null}
      <TextField
        label="Email"
        type="email"
        autoComplete="email"
        error={Boolean(errors.email)}
        helperText={errors.email?.message}
        {...register('email', { required: 'Email is required.' })}
      />
      <TextField
        label="Username"
        autoComplete="username"
        error={Boolean(errors.username)}
        helperText={errors.username?.message}
        {...register('username', { required: 'Username is required.' })}
      />
      <TextField
        label="First name"
        autoComplete="given-name"
        {...register('firstName')}
      />
      <TextField
        label="Last name"
        autoComplete="family-name"
        {...register('lastName')}
      />
      <TextField
        label="Password"
        type="password"
        autoComplete="new-password"
        error={Boolean(errors.password)}
        helperText={errors.password?.message}
        {...register('password', { required: 'Password is required.' })}
      />
      <Button type="submit" variant="contained" disabled={loading}>
        Create account
      </Button>
    </Stack>
  )
}

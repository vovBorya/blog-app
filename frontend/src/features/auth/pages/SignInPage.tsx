import { useMutation } from '@apollo/client/react'
import { Alert, Button, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'

import { useAppDispatch } from '../../../app/hooks.ts'
import {
  COMPLETE_PHONE_SIGN_UP_MUTATION,
  REQUEST_PHONE_CODE_MUTATION,
  SIGN_IN_MUTATION,
  VERIFY_PHONE_CODE_MUTATION,
} from '../api/operations.ts'
import type {
  CompletePhoneSignUpData,
  RequestPhoneCodeData,
  SignInData,
  VerifyPhoneCodeData,
} from '../api/operations.ts'
import { setAuthenticated } from '../model/authSlice.ts'
import { isSupportedPhoneNumber } from '../phone.ts'

type SignInMode = 'email' | 'phone'
type PhoneStep = 'phone' | 'code' | 'username'

type SignInForm = {
  identifier: string
  password: string
}

type PhoneForm = {
  phone: string
}

type CodeForm = {
  code: string
}

type UsernameForm = {
  username: string
  firstName: string
  lastName: string
}

const RESEND_COOLDOWN_MS = 60_000

export function SignInPage() {
  const [mode, setMode] = useState<SignInMode>('email')
  const [formError, setFormError] = useState<string | null>(null)

  return (
    <Stack spacing={2} sx={{ maxWidth: 420, mx: 'auto' }}>
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
      {mode === 'email' ? (
        <EmailSignIn formError={formError} setFormError={setFormError} />
      ) : (
        <PhoneSignIn formError={formError} setFormError={setFormError} />
      )}
    </Stack>
  )
}

function EmailSignIn({
  formError,
  setFormError,
}: {
  formError: string | null
  setFormError: (message: string | null) => void
}) {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
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
    <Stack component="form" spacing={2} onSubmit={(event) => void handleSubmit(onSubmit)(event)}>
      {formError ? <Alert severity="error">{formError}</Alert> : null}
      <TextField
        label="Email"
        type="email"
        autoComplete="email"
        helperText={errors.identifier?.message}
        error={Boolean(errors.identifier)}
        {...register('identifier', { required: 'This field is required.' })}
      />
      <TextField
        label="Password"
        type="password"
        autoComplete="current-password"
        helperText={errors.password?.message}
        error={Boolean(errors.password)}
        {...register('password', { required: 'Password is required.' })}
      />
      <Button type="submit" variant="contained" disabled={loading}>
        Sign in
      </Button>
    </Stack>
  )
}

function PhoneSignIn({
  formError,
  setFormError,
}: {
  formError: string | null
  setFormError: (message: string | null) => void
}) {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const [step, setStep] = useState<PhoneStep>('phone')
  const [phone, setPhone] = useState('')
  const [signupToken, setSignupToken] = useState<string | null>(null)
  const [resendAt, setResendAt] = useState<number | null>(null)
  const [now, setNow] = useState(() => Date.now())
  const [requestPhoneCode, { loading: sending }] = useMutation<RequestPhoneCodeData>(
    REQUEST_PHONE_CODE_MUTATION,
  )
  const [verifyPhoneCode, { loading: verifying }] = useMutation<VerifyPhoneCodeData>(
    VERIFY_PHONE_CODE_MUTATION,
  )
  const [completePhoneSignUp, { loading: creating }] = useMutation<CompletePhoneSignUpData>(
    COMPLETE_PHONE_SIGN_UP_MUTATION,
  )
  const phoneForm = useForm<PhoneForm>({ defaultValues: { phone: '' } })
  const codeForm = useForm<CodeForm>({ defaultValues: { code: '' } })
  const usernameForm = useForm<UsernameForm>({
    defaultValues: { username: '', firstName: '', lastName: '' },
  })

  useEffect(() => {
    if (resendAt === null) {
      return
    }
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [resendAt])

  const cooldownSeconds = resendAt === null ? 0 : Math.max(0, Math.ceil((resendAt - now) / 1000))

  async function sendCode(rawPhone: string) {
    setFormError(null)
    const trimmed = rawPhone.trim()
    if (!isSupportedPhoneNumber(trimmed)) {
      setFormError('Enter a valid phone number.')
      return
    }
    try {
      const result = await requestPhoneCode({ variables: { phone: trimmed } })
      const payload = result.data?.requestPhoneCode
      if (!payload?.success) {
        setFormError(payload?.errors?.join(' ') || 'Could not send a verification code.')
        return
      }
      setPhone(trimmed)
      setStep('code')
      setResendAt(Date.now() + RESEND_COOLDOWN_MS)
    } catch {
      setFormError('Could not reach the server.')
    }
  }

  async function onVerify(values: CodeForm) {
    setFormError(null)
    try {
      const result = await verifyPhoneCode({
        variables: { phone, code: values.code.trim() },
      })
      const payload = result.data?.verifyPhoneCode
      if (!payload?.success) {
        setFormError(payload?.errors?.join(' ') || 'Invalid verification code.')
        return
      }
      if (payload.status === 'AUTHENTICATED' && payload.user) {
        dispatch(setAuthenticated(payload.user))
        void navigate('/')
        return
      }
      if (payload.status === 'NEEDS_USERNAME' && payload.signupToken) {
        setSignupToken(payload.signupToken)
        setStep('username')
        return
      }
      setFormError('Could not verify that code.')
    } catch {
      setFormError('Could not reach the server.')
    }
  }

  async function onCreateAccount(values: UsernameForm) {
    setFormError(null)
    if (!signupToken) {
      setFormError('Request a new verification code.')
      setStep('phone')
      return
    }
    try {
      const result = await completePhoneSignUp({
        variables: {
          input: {
            signupToken,
            username: values.username.trim(),
            firstName: values.firstName.trim(),
            lastName: values.lastName.trim(),
          },
        },
      })
      const payload = result.data?.completePhoneSignUp
      if (!payload?.success || !payload.user) {
        setFormError(payload?.errors?.join(' ') || 'Could not create the account.')
        return
      }
      dispatch(setAuthenticated(payload.user))
      void navigate('/')
    } catch {
      setFormError('Could not reach the server.')
    }
  }

  if (step === 'username') {
    return (
      <Stack
        component="form"
        spacing={2}
        onSubmit={(event) => void usernameForm.handleSubmit(onCreateAccount)(event)}
      >
        <Typography variant="body2">
          This number is new. Choose a username to finish creating your account.
        </Typography>
        {formError ? <Alert severity="error">{formError}</Alert> : null}
        <TextField
          label="Username"
          autoComplete="username"
          error={Boolean(usernameForm.formState.errors.username)}
          helperText={usernameForm.formState.errors.username?.message}
          {...usernameForm.register('username', { required: 'Username is required.' })}
        />
        <TextField label="First name" autoComplete="given-name" {...usernameForm.register('firstName')} />
        <TextField label="Last name" autoComplete="family-name" {...usernameForm.register('lastName')} />
        <Button type="submit" variant="contained" disabled={creating}>
          Create account
        </Button>
      </Stack>
    )
  }

  if (step === 'code') {
    return (
      <Stack component="form" spacing={2} onSubmit={(event) => void codeForm.handleSubmit(onVerify)(event)}>
        <Typography variant="body2">Enter the 6-digit code sent to {phone}.</Typography>
        {formError ? <Alert severity="error">{formError}</Alert> : null}
        <TextField
          label="Verification code"
          autoComplete="one-time-code"
          slotProps={{ htmlInput: { inputMode: 'numeric', maxLength: 6 } }}
          error={Boolean(codeForm.formState.errors.code)}
          helperText={codeForm.formState.errors.code?.message}
          {...codeForm.register('code', {
            required: 'Code is required.',
            pattern: { value: /^\d{6}$/, message: 'Enter the 6-digit code.' },
          })}
        />
        <Button type="submit" variant="contained" disabled={verifying}>
          Continue
        </Button>
        <Button
          type="button"
          variant="text"
          disabled={sending || cooldownSeconds > 0}
          onClick={() => void sendCode(phone)}
        >
          {cooldownSeconds > 0 ? `Resend code in ${cooldownSeconds}s` : 'Resend code'}
        </Button>
        <Button
          type="button"
          variant="text"
          onClick={() => {
            setStep('phone')
            setFormError(null)
          }}
        >
          Use a different number
        </Button>
      </Stack>
    )
  }

  return (
    <Stack
      component="form"
      spacing={2}
      onSubmit={(event) => void phoneForm.handleSubmit((values) => sendCode(values.phone))(event)}
    >
      {formError ? <Alert severity="error">{formError}</Alert> : null}
      <TextField
        label="Phone number"
        type="tel"
        autoComplete="tel"
        helperText={
          phoneForm.formState.errors.phone?.message ??
          'Include a country code, for example +14155552671.'
        }
        error={Boolean(phoneForm.formState.errors.phone)}
        {...phoneForm.register('phone', { required: 'This field is required.' })}
      />
      <Button type="submit" variant="contained" disabled={sending}>
        Send code
      </Button>
    </Stack>
  )
}

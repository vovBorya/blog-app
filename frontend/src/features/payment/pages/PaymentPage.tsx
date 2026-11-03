import { Alert, Button, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import { useForm } from 'react-hook-form'

type PaymentForm = {
  name: string
  cardNumber: string
  expiry: string
  cvc: string
  amount: string
}

type PaymentErrors = Partial<Record<keyof PaymentForm, string>>

function validatePayment(values: PaymentForm): PaymentErrors {
  const errors: PaymentErrors = {}
  if (!values.name.trim()) {
    errors.name = 'Name is required.'
  }

  const digits = values.cardNumber.replace(/[\s-]/g, '')
  if (!/^\d{13,19}$/.test(digits)) {
    errors.cardNumber = 'Enter a card number of 13 to 19 digits.'
  }

  const expiry = /^(\d{2})\/(\d{2})$/.exec(values.expiry.trim())
  if (!expiry) {
    errors.expiry = 'Use MM/YY.'
  } else {
    const month = Number(expiry[1])
    const year = 2000 + Number(expiry[2])
    const now = new Date()
    const expiryIndex = year * 12 + month
    const nowIndex = now.getFullYear() * 12 + (now.getMonth() + 1)
    if (month < 1 || month > 12 || expiryIndex < nowIndex) {
      errors.expiry = 'Enter a valid future expiry date.'
    }
  }

  if (!/^\d{3,4}$/.test(values.cvc.trim())) {
    errors.cvc = 'Enter a 3 or 4 digit CVC.'
  }

  const amount = Number(values.amount)
  if (!Number.isFinite(amount) || amount <= 0) {
    errors.amount = 'Enter an amount greater than zero.'
  }

  return errors
}

export function PaymentPage() {
  const [confirmed, setConfirmed] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<PaymentErrors>({})
  const { register, handleSubmit, reset } = useForm<PaymentForm>({
    defaultValues: { name: '', cardNumber: '', expiry: '', cvc: '', amount: '' },
  })

  function onSubmit(values: PaymentForm) {
    const errors = validatePayment(values)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) {
      setConfirmed(false)
      return
    }
    setConfirmed(true)
    reset()
  }

  return (
    <Stack
      component="form"
      spacing={2}
      onSubmit={(event) => void handleSubmit(onSubmit)(event)}
      sx={{ maxWidth: 420, mx: 'auto' }}
    >
      <Typography variant="h4" component="h1">
        Payment
      </Typography>
      <Typography color="text.secondary">
        This form checks the fields in the browser. It does not charge a card.
      </Typography>
      {confirmed ? (
        <Alert severity="success">Payment confirmed. No charge was made.</Alert>
      ) : null}
      <TextField
        label="Name on card"
        autoComplete="cc-name"
        error={Boolean(fieldErrors.name)}
        helperText={fieldErrors.name}
        {...register('name')}
      />
      <TextField
        label="Card number"
        autoComplete="cc-number"
        inputMode="numeric"
        error={Boolean(fieldErrors.cardNumber)}
        helperText={fieldErrors.cardNumber}
        {...register('cardNumber')}
      />
      <TextField
        label="Expiry"
        placeholder="MM/YY"
        autoComplete="cc-exp"
        error={Boolean(fieldErrors.expiry)}
        helperText={fieldErrors.expiry}
        {...register('expiry')}
      />
      <TextField
        label="CVC"
        autoComplete="cc-csc"
        inputMode="numeric"
        error={Boolean(fieldErrors.cvc)}
        helperText={fieldErrors.cvc}
        {...register('cvc')}
      />
      <TextField
        label="Amount"
        type="number"
        slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
        error={Boolean(fieldErrors.amount)}
        helperText={fieldErrors.amount}
        {...register('amount')}
      />
      <Button type="submit" variant="contained">
        Confirm payment
      </Button>
    </Stack>
  )
}

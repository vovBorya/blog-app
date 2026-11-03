import { isValidPhoneNumber } from 'libphonenumber-js'

export function isSupportedPhoneNumber(value: string): boolean {
  const trimmed = value.trim()
  if (isValidPhoneNumber(trimmed)) {
    return true
  }
  return isValidPhoneNumber(trimmed, 'US')
}

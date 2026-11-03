import { gql } from '@apollo/client'

export const ME_QUERY = gql`
  query Me {
    me {
      id
      email
      username
      firstName
      lastName
    }
  }
`

export const SIGN_IN_MUTATION = gql`
  mutation SignIn($input: SignInInput!) {
    signIn(input: $input) {
      success
      errors
      user {
        id
        email
        username
        firstName
        lastName
      }
    }
  }
`

export const SIGN_UP_MUTATION = gql`
  mutation SignUp($input: SignUpInput!) {
    signUp(input: $input) {
      success
      errors
      user {
        id
        email
        username
        firstName
        lastName
      }
    }
  }
`

export const REQUEST_PHONE_CODE_MUTATION = gql`
  mutation RequestPhoneCode($phone: String!) {
    requestPhoneCode(phone: $phone) {
      success
      errors
    }
  }
`

export const VERIFY_PHONE_CODE_MUTATION = gql`
  mutation VerifyPhoneCode($phone: String!, $code: String!) {
    verifyPhoneCode(phone: $phone, code: $code) {
      success
      errors
      status
      signupToken
      user {
        id
        email
        username
        firstName
        lastName
      }
    }
  }
`

export const COMPLETE_PHONE_SIGN_UP_MUTATION = gql`
  mutation CompletePhoneSignUp($input: CompletePhoneSignUpInput!) {
    completePhoneSignUp(input: $input) {
      success
      errors
      user {
        id
        email
        username
        firstName
        lastName
      }
    }
  }
`

export const DELETE_TOKEN_COOKIE_MUTATION = gql`
  mutation DeleteTokenCookie {
    deleteTokenCookie {
      deleted
    }
  }
`

export type AuthUserFields = {
  id: string
  email: string | null
  username: string
  firstName: string | null
  lastName: string | null
}

export type RequestPhoneCodeData = {
  requestPhoneCode: {
    success: boolean
    errors: string[] | null
  }
}

export type PhoneAuthStatus = 'AUTHENTICATED' | 'NEEDS_USERNAME'

export type VerifyPhoneCodeData = {
  verifyPhoneCode: {
    success: boolean
    errors: string[] | null
    status: PhoneAuthStatus | null
    signupToken: string | null
    user: AuthUserFields | null
  }
}

export type CompletePhoneSignUpData = {
  completePhoneSignUp: AuthPayload
}

export type AuthPayload = {
  success: boolean
  errors: string[] | null
  user: AuthUserFields | null
}

export type MeQueryData = {
  me: AuthUserFields | null
}

export type SignInData = {
  signIn: AuthPayload
}

export type SignUpData = {
  signUp: AuthPayload
}

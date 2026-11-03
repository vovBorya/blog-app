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

export const DELETE_TOKEN_COOKIE_MUTATION = gql`
  mutation DeleteTokenCookie {
    deleteTokenCookie {
      deleted
    }
  }
`

export type AuthUserFields = {
  id: string
  email: string
  username: string
  firstName: string | null
  lastName: string | null
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

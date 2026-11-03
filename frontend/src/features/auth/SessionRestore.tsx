import { useQuery } from '@apollo/client/react'
import { useEffect } from 'react'

import { useAppDispatch, useAppSelector } from '../../app/hooks.ts'
import { ME_QUERY } from './api/operations.ts'
import type { MeQueryData } from './api/operations.ts'
import { setAnonymous, setAuthenticated } from './model/authSlice.ts'

export function SessionRestore() {
  const dispatch = useAppDispatch()
  const status = useAppSelector((state) => state.auth.status)
  const { data, dataState, error } = useQuery<MeQueryData>(ME_QUERY, {
    fetchPolicy: 'network-only',
    errorPolicy: 'all',
  })

  useEffect(() => {
    if (dataState === 'empty' && !error) {
      return
    }

    if (data?.me) {
      if (status !== 'anonymous') {
        dispatch(setAuthenticated(data.me))
      }
      return
    }

    if (status === 'unknown') {
      dispatch(setAnonymous())
    }
  }, [data, dataState, dispatch, error, status])

  return null
}

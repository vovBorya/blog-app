import { useMutation } from '@apollo/client/react'
import { Alert, Button, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'

import {
  CREATE_AUTHOR_MUTATION,
  CREATE_POST_MUTATION,
  POST_PAGE_SIZE,
  PUBLISHED_POSTS_QUERY,
} from '../api/operations.ts'
import type { CreateAuthorData, CreatePostData } from '../api/operations.ts'

type CreatePostForm = {
  title: string
  content: string
  excerpt: string
  status: 'draft' | 'published'
}

const ALREADY_HAS_PROFILE = 'already have an author profile'

export function CreatePostPage() {
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)
  const [createAuthor, { loading: creatingAuthor }] = useMutation<CreateAuthorData>(
    CREATE_AUTHOR_MUTATION,
  )
  const [createPost, { loading: creatingPost }] = useMutation<CreatePostData>(CREATE_POST_MUTATION)
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<CreatePostForm>({
    defaultValues: { title: '', content: '', excerpt: '', status: 'published' },
  })

  async function onSubmit(values: CreatePostForm) {
    setFormError(null)
    try {
      const authorResult = await createAuthor({
        variables: { input: { bio: '' } },
      })
      const authorPayload = authorResult.data?.createAuthor
      const authorErrors = authorPayload?.errors ?? []
      const alreadyHasProfile = authorErrors.some((message) =>
        message.toLowerCase().includes(ALREADY_HAS_PROFILE),
      )
      if (!authorPayload?.success && !alreadyHasProfile) {
        setFormError(authorErrors.join(' ') || 'Could not prepare your author profile.')
        return
      }

      const postResult = await createPost({
        variables: {
          input: {
            title: values.title.trim(),
            content: values.content.trim(),
            excerpt: values.excerpt.trim(),
            status: values.status,
          },
        },
        refetchQueries: [
          { query: PUBLISHED_POSTS_QUERY, variables: { first: POST_PAGE_SIZE } },
        ],
      })
      const postPayload = postResult.data?.createPost
      if (!postPayload?.success) {
        setFormError(postPayload?.errors?.join(' ') || 'Could not create the post.')
        return
      }
      void navigate('/')
    } catch {
      setFormError('Could not reach the server.')
    }
  }

  const saving = creatingAuthor || creatingPost

  return (
    <Stack
      component="form"
      spacing={2}
      onSubmit={(event) => void handleSubmit(onSubmit)(event)}
      sx={{ maxWidth: 720, mx: 'auto' }}
    >
      <Typography variant="h4" component="h1">
        Create post
      </Typography>
      {formError ? <Alert severity="error">{formError}</Alert> : null}
      <TextField
        label="Title"
        error={Boolean(errors.title)}
        helperText={errors.title?.message}
        {...register('title', { required: 'Title is required.' })}
      />
      <TextField
        label="Excerpt"
        multiline
        minRows={2}
        {...register('excerpt')}
      />
      <TextField
        label="Content"
        multiline
        minRows={8}
        error={Boolean(errors.content)}
        helperText={errors.content?.message}
        {...register('content', { required: 'Content is required.' })}
      />
      <Controller
        name="status"
        control={control}
        render={({ field }) => (
          <TextField select label="Status" {...field}>
            <MenuItem value="published">Published</MenuItem>
            <MenuItem value="draft">Draft</MenuItem>
          </TextField>
        )}
      />
      <Button type="submit" variant="contained" disabled={saving}>
        Save post
      </Button>
    </Stack>
  )
}

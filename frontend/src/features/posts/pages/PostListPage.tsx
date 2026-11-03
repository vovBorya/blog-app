import { useQuery } from '@apollo/client/react'
import { Alert, Box, CircularProgress, Stack, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'

import { PostCard } from '../components/PostCard.tsx'
import { POST_PAGE_SIZE, PUBLISHED_POSTS_QUERY } from '../api/operations.ts'
import type { PublishedPostsData, PublishedPostsVars } from '../api/operations.ts'

export function PostListPage() {
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  const loadingMore = useRef(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const { data, loading, error, fetchMore } = useQuery<PublishedPostsData, PublishedPostsVars>(
    PUBLISHED_POSTS_QUERY,
    {
      variables: { first: POST_PAGE_SIZE },
      notifyOnNetworkStatusChange: true,
    },
  )

  const pageInfo = data?.publishedPosts.pageInfo
  const posts = (data?.publishedPosts.edges ?? [])
    .map((edge) => edge.node)
    .filter((node) => node !== null)

  useEffect(() => {
    const node = sentinelRef.current
    if (!node || !pageInfo?.hasNextPage || !pageInfo.endCursor) {
      return
    }

    const endCursor = pageInfo.endCursor
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting) || loadingMore.current) {
        return
      }

      loadingMore.current = true
      setLoadError(null)
      void fetchMore({
        variables: { first: POST_PAGE_SIZE, after: endCursor },
      })
        .catch(() => {
          setLoadError('Could not load more posts.')
        })
        .finally(() => {
          loadingMore.current = false
        })
    })

    observer.observe(node)
    return () => observer.disconnect()
  }, [fetchMore, pageInfo?.endCursor, pageInfo?.hasNextPage])

  if (loading && !data) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h4" component="h1">
        Recent posts
      </Typography>
      {error ? <Alert severity="error">Could not load posts.</Alert> : null}
      {loadError ? <Alert severity="error">{loadError}</Alert> : null}
      {posts.length === 0 && !error ? (
        <Typography color="text.secondary">No published posts yet.</Typography>
      ) : null}
      {posts.map((post) => (
        <PostCard key={post.id} post={post} />
      ))}
      <Box ref={sentinelRef} sx={{ display: 'flex', justifyContent: 'center', minHeight: 48 }}>
        {pageInfo?.hasNextPage ? <CircularProgress size={28} /> : null}
      </Box>
      {posts.length > 0 && pageInfo && !pageInfo.hasNextPage ? (
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center' }}>
          No more posts
        </Typography>
      ) : null}
    </Stack>
  )
}

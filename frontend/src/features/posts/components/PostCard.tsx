import { Card, CardContent, Typography } from '@mui/material'

import type { PostNode } from '../api/operations.ts'

type PostCardProps = {
  post: PostNode
}

export function PostCard({ post }: PostCardProps) {
  const published = post.publishedAt ? new Date(post.publishedAt).toLocaleDateString() : null
  const author = post.author?.user?.username ?? 'Unknown author'

  return (
    <Card>
      <CardContent>
        <Typography variant="h5" component="h2" gutterBottom>
          {post.title}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {author}
          {published ? ` · ${published}` : ''}
        </Typography>
        {post.excerpt ? <Typography variant="body1">{post.excerpt}</Typography> : null}
      </CardContent>
    </Card>
  )
}

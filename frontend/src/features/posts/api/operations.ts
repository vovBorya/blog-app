import { gql } from '@apollo/client'

export const POST_PAGE_SIZE = 5

export const PUBLISHED_POSTS_QUERY = gql`
  query PublishedPosts($first: Int!, $after: String) {
    publishedPosts(first: $first, after: $after) {
      edges {
        cursor
        node {
          id
          title
          excerpt
          publishedAt
          author {
            user {
              username
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`

export const CREATE_AUTHOR_MUTATION = gql`
  mutation CreateAuthor($input: CreateAuthorInput!) {
    createAuthor(input: $input) {
      success
      errors
    }
  }
`

export const CREATE_POST_MUTATION = gql`
  mutation CreatePost($input: CreatePostInput!) {
    createPost(input: $input) {
      success
      errors
      post {
        id
        title
      }
    }
  }
`

export type PostNode = {
  id: string
  title: string
  excerpt: string | null
  publishedAt: string | null
  author: {
    user: {
      username: string
    } | null
  } | null
}

export type PublishedPostsData = {
  publishedPosts: {
    edges: { cursor: string; node: PostNode | null }[]
    pageInfo: {
      hasNextPage: boolean
      endCursor: string | null
    }
  }
}

export type PublishedPostsVars = {
  first: number
  after?: string | null
}

export type CreateAuthorData = {
  createAuthor: {
    success: boolean
    errors: string[] | null
  }
}

export type CreatePostData = {
  createPost: {
    success: boolean
    errors: string[] | null
    post: { id: string; title: string } | null
  }
}

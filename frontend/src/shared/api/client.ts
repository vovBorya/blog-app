import { ApolloClient, HttpLink, InMemoryCache } from '@apollo/client'

import { env } from '../config/env.ts'

export const apolloClient = new ApolloClient({
  link: new HttpLink({
    uri: env.graphqlUrl,
    credentials: 'include',
  }),
  cache: new InMemoryCache({
    typePolicies: {
      Query: {
        fields: {
          publishedPosts: {
            keyArgs: ['search', 'authorId'],
            merge(existing, incoming, { args }) {
              if (!existing || !args?.after) {
                return incoming
              }

              const previous = existing as { edges?: readonly unknown[] }
              const next = incoming as { edges?: readonly unknown[] }

              return {
                ...next,
                edges: [...(previous.edges ?? []), ...(next.edges ?? [])],
              }
            },
          },
        },
      },
    },
  }),
})

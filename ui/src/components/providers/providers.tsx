'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState } from 'react';
import { ThemeProvider } from './theme-provider';

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes
            gcTime: 10 * 60 * 1000, // 10 minutes
            retry: (failureCount, error: Error & { response?: { status: number } }) => {
              // Don't retry on 4xx errors except 408, 429
              if (error?.response?.status >= 400 && error?.response?.status < 500) {
                if (error?.response?.status === 408 || error?.response?.status === 429) {
                  return failureCount < 2;
                }
                return false;
              }
              // Retry on network errors and 5xx errors
              return failureCount < 3;
            },
            retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
          },
          mutations: {
            retry: (failureCount, error: Error & { response?: { status: number } }) => {
              // Don't retry mutations on client errors
              if (error?.response?.status >= 400 && error?.response?.status < 500) {
                return false;
              }
              // Retry on network errors and 5xx errors
              return failureCount < 2;
            },
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        defaultTheme='system'
      >
        {children}
        {/* <ReactQueryDevtools initialIsOpen={false} /> */}
      </ThemeProvider>
    </QueryClientProvider>
  );
}
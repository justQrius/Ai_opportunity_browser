'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { LoadingSpinner } from '@/components';
import { useAuthStore } from '@/stores/authStore';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRoles?: string[];
  fallback?: React.ReactNode;
  redirectTo?: string;
}

export function ProtectedRoute({ 
  children, 
  requiredRoles = [], 
  fallback,
  redirectTo 
}: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, user, initializeAuth } = useAuthStore();
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const initialize = async () => {
      await initializeAuth();
      setIsInitialized(true);
    };
    
    initialize();
  }, [initializeAuth]);

  useEffect(() => {
    if (isInitialized && !isLoading && !isAuthenticated) {
      const loginUrl = redirectTo || `/auth/login?redirect=${encodeURIComponent(pathname)}`;
      router.push(loginUrl);
    }
  }, [isInitialized, isLoading, isAuthenticated, router, pathname, redirectTo]);

  // Show loading while initializing auth or during navigation
  if (!isInitialized || isLoading || (!isAuthenticated && isInitialized)) {
    return fallback || (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner 
          text="Verifying authentication..." 
          variant="ai-themed"
          size="lg"
        />
      </div>
    );
  }

  // Check role requirements if user is authenticated
  if (isAuthenticated && requiredRoles.length > 0 && user) {
    const hasRequiredRole = requiredRoles.some(role => {
      // Add role checking logic here based on your user model
      // For now, we'll assume all authenticated users have access
      return true;
    });

    if (!hasRequiredRole) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center space-y-4">
            <h1 className="text-2xl font-bold">Access Denied</h1>
            <p className="text-muted-foreground">
              You don't have permission to access this page.
            </p>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
}

// Higher-order component for wrapping pages
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: Omit<ProtectedRouteProps, 'children'>
) {
  return function AuthenticatedComponent(props: P) {
    return (
      <ProtectedRoute {...options}>
        <Component {...props} />
      </ProtectedRoute>
    );
  };
}

export default ProtectedRoute;
'use client';

import React, { useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { initializeAuth } = useAuthStore();

  useEffect(() => {
    // Initialize authentication on app startup
    initializeAuth();
  }, [initializeAuth]);

  return <>{children}</>;
}

export default AuthProvider;
'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LoadingSpinner } from '@/components';
import { 
  Brain, 
  Eye, 
  EyeOff, 
  Mail, 
  Lock, 
  User, 
  ArrowRight,
  AlertCircle,
  CheckCircle,
  X,
  Plus
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { cn } from '@/lib/utils';

const registerSchema = z.object({
  full_name: z
    .string()
    .min(1, 'Full name is required')
    .min(2, 'Full name must be at least 2 characters')
    .max(100, 'Full name must be less than 100 characters'),
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number'),
  confirmPassword: z
    .string()
    .min(1, 'Please confirm your password'),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type RegisterFormData = z.infer<typeof registerSchema>;

const expertiseDomains = [
  'Machine Learning',
  'Natural Language Processing',
  'Computer Vision',
  'Data Science',
  'Software Engineering',
  'Product Management',
  'Business Strategy',
  'Marketing',
  'Sales',
  'Finance',
  'Operations',
  'Design',
  'Research',
  'Consulting',
  'Entrepreneurship',
  'Investment',
  'Healthcare',
  'Education',
  'E-commerce',
  'FinTech',
  'Other'
];

export default function RegisterPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { register: registerUser, isLoading, error, clearError, isAuthenticated } = useAuthStore();
  
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [selectedExpertise, setSelectedExpertise] = useState<string[]>([]);
  const [customExpertise, setCustomExpertise] = useState('');
  const [registrationSuccess, setRegistrationSuccess] = useState(false);

  const redirectTo = searchParams.get('redirect') || '/opportunities';

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
    clearErrors,
    watch
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const password = watch('password');

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      router.push(redirectTo);
    }
  }, [isAuthenticated, isLoading, router, redirectTo]);

  // Clear errors when component mounts
  useEffect(() => {
    clearError();
  }, [clearError]);

  const addExpertise = (domain: string) => {
    if (!selectedExpertise.includes(domain) && selectedExpertise.length < 5) {
      setSelectedExpertise([...selectedExpertise, domain]);
    }
  };

  const removeExpertise = (domain: string) => {
    setSelectedExpertise(selectedExpertise.filter(d => d !== domain));
  };

  const addCustomExpertise = () => {
    if (customExpertise.trim() && !selectedExpertise.includes(customExpertise.trim()) && selectedExpertise.length < 5) {
      setSelectedExpertise([...selectedExpertise, customExpertise.trim()]);
      setCustomExpertise('');
    }
  };

  const onSubmit = async (data: RegisterFormData) => {
    clearErrors();
    clearError();
    
    try {
      await registerUser({
        full_name: data.full_name,
        email: data.email,
        password: data.password,
        expertise_domains: selectedExpertise.length > 0 ? selectedExpertise : undefined
      });
      
      setRegistrationSuccess(true);
      
      // Small delay to show success state before redirect
      setTimeout(() => {
        router.push(redirectTo);
      }, 1500);
      
    } catch (error: unknown) {
      // Error is handled by the store, but we can add form-specific error handling here
      if (error instanceof Error && 'response' in error && typeof error.response === 'object' && error.response !== null) {
        const errorResponse = error.response as { status?: number; data?: { detail?: unknown } };
        if (errorResponse.status === 409) {
          setError('email', {
            type: 'manual',
            message: 'An account with this email already exists.'
          });
        } else if (errorResponse.status === 422) {
          const validationErrors = errorResponse.data?.detail;
          if (Array.isArray(validationErrors)) {
            validationErrors.forEach((err: { loc: (string | number)[]; msg: string }) => {
              if (err.loc && err.loc[1]) {
                setError(err.loc[1] as keyof RegisterFormData, {
                  type: 'manual',
                  message: err.msg
                });
              }
            });
          }
        }
      }
    }
  };

  const getPasswordStrength = (password: string) => {
    if (!password) return { strength: 0, label: '' };
    
    let strength = 0;
    const checks = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
      special: /[^A-Za-z0-9]/.test(password)
    };
    
    strength = Object.values(checks).filter(Boolean).length;
    
    const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
    const colors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-blue-500', 'bg-green-500'];
    
    return {
      strength,
      label: labels[Math.min(strength - 1, 4)] || '',
      color: colors[Math.min(strength - 1, 4)] || 'bg-gray-300',
      checks
    };
  };

  const passwordStrength = getPasswordStrength(password || '');

  if (registrationSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="p-8 text-center space-y-4">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-2">Welcome to AI Opportunities!</h2>
              <p className="text-muted-foreground">
                Your account has been created successfully. Redirecting you now...
              </p>
            </div>
            <LoadingSpinner size="sm" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-lg space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <Link href="/" className="inline-flex items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="flex items-center justify-center w-10 h-10 bg-primary rounded-lg">
              <Brain className="w-6 h-6 text-primary-foreground" />
            </div>
            <div className="text-left">
              <div className="font-bold text-lg leading-none">AI Opportunities</div>
              <div className="text-xs text-muted-foreground leading-none">Browser</div>
            </div>
          </Link>
        </div>

        {/* Registration Card */}
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">Create Account</CardTitle>
            <CardDescription className="text-center">
              Join our community of AI opportunity hunters
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {/* Error display */}
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Registration Form */}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {/* Full Name */}
              <div className="space-y-2">
                <Label htmlFor="full_name">Full Name</Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                  <Input
                    id="full_name"
                    type="text"
                    placeholder="Enter your full name"
                    className="pl-10"
                    {...register('full_name')}
                    disabled={isLoading || isSubmitting}
                  />
                </div>
                {errors.full_name && (
                  <p className="text-sm text-destructive">{errors.full_name.message}</p>
                )}
              </div>

              {/* Email */}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="Enter your email"
                    className="pl-10"
                    {...register('email')}
                    disabled={isLoading || isSubmitting}
                  />
                </div>
                {errors.email && (
                  <p className="text-sm text-destructive">{errors.email.message}</p>
                )}
              </div>

              {/* Password */}
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Create a strong password"
                    className="pl-10 pr-10"
                    {...register('password')}
                    disabled={isLoading || isSubmitting}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    disabled={isLoading || isSubmitting}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                
                {/* Password Strength Indicator */}
                {password && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-muted rounded-full h-2">
                        <div 
                          className={cn('h-full rounded-full transition-all', passwordStrength.color)}
                          style={{ width: `${(passwordStrength.strength / 5) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {passwordStrength.label}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-1 text-xs">
                      <div className={cn(passwordStrength.checks?.length ? 'text-green-600' : 'text-muted-foreground')}>
                        ✓ 8+ characters
                      </div>
                      <div className={cn(passwordStrength.checks?.uppercase ? 'text-green-600' : 'text-muted-foreground')}>
                        ✓ Uppercase letter
                      </div>
                      <div className={cn(passwordStrength.checks?.lowercase ? 'text-green-600' : 'text-muted-foreground')}>
                        ✓ Lowercase letter
                      </div>
                      <div className={cn(passwordStrength.checks?.number ? 'text-green-600' : 'text-muted-foreground')}>
                        ✓ Number
                      </div>
                    </div>
                  </div>
                )}
                
                {errors.password && (
                  <p className="text-sm text-destructive">{errors.password.message}</p>
                )}
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="Confirm your password"
                    className="pl-10 pr-10"
                    {...register('confirmPassword')}
                    disabled={isLoading || isSubmitting}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    disabled={isLoading || isSubmitting}
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>
                )}
              </div>

              {/* Expertise Selection */}
              <div className="space-y-3">
                <div>
                  <Label>Areas of Expertise <span className="text-muted-foreground">(Optional)</span></Label>
                  <p className="text-xs text-muted-foreground">Select up to 5 areas where you have knowledge or experience</p>
                </div>
                
                {/* Selected Expertise */}
                {selectedExpertise.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {selectedExpertise.map((domain) => (
                      <Badge key={domain} variant="secondary" className="gap-1">
                        {domain}
                        <button
                          type="button"
                          onClick={() => removeExpertise(domain)}
                          className="hover:text-destructive"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
                
                {/* Expertise Options */}
                {selectedExpertise.length < 5 && (
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto">
                      {expertiseDomains
                        .filter(domain => !selectedExpertise.includes(domain))
                        .map((domain) => (
                          <Button
                            key={domain}
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => addExpertise(domain)}
                            className="justify-start text-xs h-8"
                          >
                            <Plus className="w-3 h-3 mr-1" />
                            {domain}
                          </Button>
                        ))}
                    </div>
                    
                    {/* Custom Expertise */}
                    <div className="flex gap-2">
                      <Input
                        placeholder="Add custom expertise"
                        value={customExpertise}
                        onChange={(e) => setCustomExpertise(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addCustomExpertise())}
                        className="text-sm"
                        disabled={isLoading || isSubmitting}
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={addCustomExpertise}
                        disabled={!customExpertise.trim() || isLoading || isSubmitting}
                      >
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              <Button 
                type="submit" 
                className="w-full gap-2" 
                disabled={isLoading || isSubmitting}
              >
                {(isLoading || isSubmitting) ? (
                  <LoadingSpinner size="sm" />
                ) : (
                  <>
                    Create Account
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </Button>
            </form>

            {/* Sign in link */}
            <div className="text-center text-sm">
              <span className="text-muted-foreground">Already have an account? </span>
              <Link 
                href={`/auth/login${redirectTo !== '/opportunities' ? `?redirect=${encodeURIComponent(redirectTo)}` : ''}`}
                className="text-primary hover:underline font-medium"
              >
                Sign in
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center text-xs text-muted-foreground">
          By creating an account, you agree to our{' '}
          <Link href="/legal/terms" className="underline hover:text-foreground">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link href="/legal/privacy" className="underline hover:text-foreground">
            Privacy Policy
          </Link>
        </div>
      </div>
    </div>
  );
}
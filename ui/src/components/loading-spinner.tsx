import React from 'react';
import { Loader2, Brain, Sparkles, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'default' | 'dots' | 'pulse' | 'bounce' | 'ai-themed';
  className?: string;
  text?: string;
  centered?: boolean;
  fullScreen?: boolean;
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-12 h-12'
};

const textSizeClasses = {
  sm: 'text-xs',
  md: 'text-sm',
  lg: 'text-base',
  xl: 'text-lg'
};

// Default spinner with Loader2 icon
function DefaultSpinner({ size = 'md', className }: { size?: keyof typeof sizeClasses; className?: string }) {
  return (
    <Loader2 
      className={cn(
        'animate-spin text-primary',
        sizeClasses[size],
        className
      )} 
    />
  );
}

// Animated dots loader
function DotsLoader({ size = 'md', className }: { size?: keyof typeof sizeClasses; className?: string }) {
  const dotSize = {
    sm: 'w-1 h-1',
    md: 'w-1.5 h-1.5',
    lg: 'w-2 h-2',
    xl: 'w-3 h-3'
  };

  return (
    <div className={cn('flex space-x-1', className)}>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className={cn(
            'bg-primary rounded-full animate-pulse',
            dotSize[size]
          )}
          style={{
            animationDelay: `${i * 0.2}s`,
            animationDuration: '1s'
          }}
        />
      ))}
    </div>
  );
}

// Pulsing circle
function PulseLoader({ size = 'md', className }: { size?: keyof typeof sizeClasses; className?: string }) {
  return (
    <div
      className={cn(
        'bg-primary rounded-full animate-pulse',
        sizeClasses[size],
        className
      )}
      style={{
        animationDuration: '1.5s'
      }}
    />
  );
}

// Bouncing loader
function BounceLoader({ size = 'md', className }: { size?: keyof typeof sizeClasses; className?: string }) {
  const dotSize = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4',
    xl: 'w-6 h-6'
  };

  return (
    <div className={cn('flex space-x-1', className)}>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className={cn(
            'bg-primary rounded-full',
            dotSize[size]
          )}
          style={{
            animation: `bounce 1.4s infinite ease-in-out both`,
            animationDelay: `${i * 0.16}s`
          }}
        />
      ))}
    </div>
  );
}

// AI-themed loader with rotating icons
function AIThemedLoader({ size = 'md', className }: { size?: keyof typeof sizeClasses; className?: string }) {
  const icons = [
    { Icon: Brain, delay: '0s', color: 'text-blue-500' },
    { Icon: Sparkles, delay: '0.5s', color: 'text-purple-500' },
    { Icon: Zap, delay: '1s', color: 'text-yellow-500' }
  ];

  return (
    <div className={cn('relative flex items-center justify-center', className)}>
      {icons.map(({ Icon, delay, color }, index) => (
        <Icon
          key={index}
          className={cn(
            'absolute animate-spin',
            sizeClasses[size],
            color
          )}
          style={{
            animationDelay: delay,
            animationDuration: '2s',
            transform: `rotate(${index * 120}deg)`,
            transformOrigin: 'center'
          }}
        />
      ))}
    </div>
  );
}

export function LoadingSpinner({
  size = 'md',
  variant = 'default',
  className,
  text,
  centered = false,
  fullScreen = false
}: LoadingSpinnerProps) {
  const renderSpinner = () => {
    switch (variant) {
      case 'dots':
        return <DotsLoader size={size} />;
      case 'pulse':
        return <PulseLoader size={size} />;
      case 'bounce':
        return <BounceLoader size={size} />;
      case 'ai-themed':
        return <AIThemedLoader size={size} />;
      default:
        return <DefaultSpinner size={size} />;
    }
  };

  const content = (
    <div className={cn(
      'flex flex-col items-center justify-center gap-3',
      centered && 'mx-auto',
      className
    )}>
      {renderSpinner()}
      {text && (
        <div className={cn(
          'text-muted-foreground text-center',
          textSizeClasses[size]
        )}>
          {text}
        </div>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
        {content}
      </div>
    );
  }

  return content;
}

// Skeleton loader for cards and content
export function SkeletonLoader({ 
  className,
  lines = 3,
  showAvatar = false,
  showButton = false
}: {
  className?: string;
  lines?: number;
  showAvatar?: boolean;
  showButton?: boolean;
}) {
  return (
    <div className={cn('animate-pulse space-y-4', className)}>
      {showAvatar && (
        <div className="flex items-center space-x-4">
          <div className="rounded-full bg-muted h-10 w-10"></div>
          <div className="space-y-2 flex-1">
            <div className="h-4 bg-muted rounded w-1/4"></div>
            <div className="h-3 bg-muted rounded w-1/6"></div>
          </div>
        </div>
      )}
      
      <div className="space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={cn(
              'h-4 bg-muted rounded',
              i === lines - 1 ? 'w-3/4' : 'w-full'
            )}
          />
        ))}
      </div>
      
      {showButton && (
        <div className="h-9 bg-muted rounded w-24"></div>
      )}
    </div>
  );
}

// Loading overlay for existing content
export function LoadingOverlay({ 
  loading, 
  children, 
  className,
  spinnerProps 
}: {
  loading: boolean;
  children: React.ReactNode;
  className?: string;
  spinnerProps?: Omit<LoadingSpinnerProps, 'fullScreen'>;
}) {
  return (
    <div className={cn('relative', className)}>
      {children}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-sm z-10">
          <LoadingSpinner {...spinnerProps} />
        </div>
      )}
    </div>
  );
}

// Loading states for lists
export function LoadingList({ count = 5, className }: { count?: number; className?: string }) {
  return (
    <div className={cn('space-y-4', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonLoader 
          key={i} 
          showAvatar={true} 
          showButton={true}
          lines={2}
        />
      ))}
    </div>
  );
}

export default LoadingSpinner;
'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ThemeToggle } from '@/components/theme-toggle';
import { 
  Brain, 
  Search, 
  TrendingUp, 
  Users, 
  BookOpen,
  Settings,
  User,
  LogOut,
  Menu,
  Bell,
  Plus
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavigationProps {
  className?: string;
}

const navigationItems = [
  {
    name: 'Opportunities',
    href: '/opportunities',
    icon: Search,
    description: 'Browse and discover AI opportunities'
  },
  {
    name: 'Trending',
    href: '/trending',
    icon: TrendingUp,
    description: 'See what\'s trending in AI'
  },
  {
    name: 'Community',
    href: '/community',
    icon: Users,
    description: 'Connect with other entrepreneurs'
  },
  {
    name: 'Learn',
    href: '/learn',
    icon: BookOpen,
    description: 'Educational resources and guides'
  }
];

export function Navigation({ className }: NavigationProps) {
  const pathname = usePathname();
  const { user, isAuthenticated, logout } = useAuthStore();
  
  const handleSignOut = async () => {
    await logout();
  };

  return (
    <header className={cn(
      'sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60',
      className
    )}>
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo and Brand */}
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <div className="flex items-center justify-center w-8 h-8 bg-primary rounded-lg">
                <Brain className="w-5 h-5 text-primary-foreground" />
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-lg leading-none">AI Opportunities</span>
                <span className="text-xs text-muted-foreground leading-none">Browser</span>
              </div>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              {navigationItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                
                return (
                  <Button
                    key={item.href}
                    asChild
                    variant={isActive ? "secondary" : "ghost"}
                    size="sm"
                    className="gap-2"
                  >
                    <Link href={item.href}>
                      <Icon className="w-4 h-4" />
                      {item.name}
                    </Link>
                  </Button>
                );
              })}
            </nav>
          </div>

          {/* Right side - User actions */}
          <div className="flex items-center gap-2">
            {/* Notifications */}
            {isAuthenticated && user && (
              <Button variant="ghost" size="sm" className="relative">
                <Bell className="w-4 h-4" />
                <Badge 
                  variant="destructive" 
                  className="absolute -top-1 -right-1 h-4 w-4 p-0 text-xs flex items-center justify-center"
                >
                  3
                </Badge>
              </Button>
            )}

            {/* Create Opportunity */}
            {isAuthenticated && user && (
              <Button size="sm" className="gap-2 hidden sm:flex">
                <Plus className="w-4 h-4" />
                Create
              </Button>
            )}

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* User Menu or Sign In */}
            {isAuthenticated && user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="bg-primary/10 text-primary">
                        {user.full_name.split(' ').map(n => n[0]).join('').toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56" align="end" forceMount>
                  <div className="flex items-center justify-start gap-2 p-2">
                    <div className="flex flex-col space-y-1 leading-none">
                      <p className="font-medium">{user.full_name}</p>
                      <p className="text-xs text-muted-foreground">{user.email}</p>
                      <div className="flex items-center gap-1">
                        <TrendingUp className="w-3 h-3 text-muted-foreground" />
                        <span className="text-xs text-muted-foreground">
                          {user.reputation_score} reputation
                        </span>
                      </div>
                    </div>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link href="/profile" className="cursor-pointer">
                      <User className="mr-2 h-4 w-4" />
                      Profile
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/settings" className="cursor-pointer">
                      <Settings className="mr-2 h-4 w-4" />
                      Settings
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleSignOut} className="cursor-pointer">
                    <LogOut className="mr-2 h-4 w-4" />
                    Sign out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/auth/login">Sign In</Link>
                </Button>
                <Button size="sm" asChild>
                  <Link href="/auth/register">Sign Up</Link>
                </Button>
              </div>
            )}

            {/* Mobile Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="md:hidden">
                  <Menu className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-56" align="end">
                {navigationItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <DropdownMenuItem key={item.href} asChild>
                      <Link href={item.href} className="cursor-pointer">
                        <Icon className="mr-2 h-4 w-4" />
                        <div>
                          <div>{item.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {item.description}
                          </div>
                        </div>
                      </Link>
                    </DropdownMenuItem>
                  );
                })}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navigation;
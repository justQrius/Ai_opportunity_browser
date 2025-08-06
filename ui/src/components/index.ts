// Export all reusable components for the AI Opportunity Browser

// Opportunity-related components
export { OpportunityCard } from './opportunity-card';
export { OpportunityList } from './opportunity-list';

// Search and filtering components
export { SearchBar } from './search-bar';
export { FilterPanel } from './filter-panel';

// UI state components
export { 
  LoadingSpinner, 
  SkeletonLoader, 
  LoadingOverlay, 
  LoadingList 
} from './loading-spinner';

// Validation components
export { 
  ValidationBadge, 
  ValidationScore, 
  ValidationStatus, 
  ExpertValidation 
} from './validation-badge';
export { ValidationForm } from './validation-form';

// Theme and utility components
export { ThemeToggle } from './theme-toggle';
export { Navigation } from './navigation';

// Provider components
export { Providers } from './providers/providers';
export { ThemeProvider } from './providers/theme-provider';

// Auth components
export { AuthProvider } from './auth/auth-provider';
export { ProtectedRoute, withAuth } from './auth/protected-route';

// Data visualization components
export { DataSourcePanel } from './data-source-panel';
export { MarketSignalsWidget } from './market-signals-widget';

// Profile components
export { ProfileHeader } from './profile/profile-header';
export { ExpertiseSection } from './profile/expertise-section';
export { ActivityFeed } from './profile/activity-feed';
export { CollectionsSection } from './profile/collections-section';

// Re-export shadcn/ui components for convenience
export { Alert, AlertTitle, AlertDescription } from './ui/alert';
export { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
export { Badge } from './ui/badge';
export { Button } from './ui/button';
export { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './ui/card';
export { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
export { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './ui/dropdown-menu';
export { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from './ui/form';
export { Input } from './ui/input';
export { Label } from './ui/label';
export { Progress } from './ui/progress';
export { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
export { Separator } from './ui/separator';
export { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger, SheetClose } from './ui/sheet';
export { Textarea } from './ui/textarea';

// Types for the components (re-export from types)
export type { 
  Opportunity, 
  OpportunityFilters, 
  User, 
  PaginatedResponse,
  SortField,
  SortOrder,
  Theme,
  Status 
} from '../types';
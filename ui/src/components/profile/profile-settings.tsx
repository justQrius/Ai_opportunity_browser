'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  User,
  Save,
  X,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  Shield,
  Bell,
  Globe,
  Lock
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface UserProfile {
  id: string;
  name: string;
  email: string;
  username: string;
  bio?: string;
  location?: string;
  website?: string;
  joinedAt: string;
  expertise: string[];
  stats: {
    validationsCount: number;
    discussionsCount: number;
    bookmarksCount: number;
    reputationScore: number;
  };
}

interface ProfileSettingsProps {
  profile: UserProfile;
  onSave: (data: Partial<UserProfile>) => Promise<void>;
  className?: string;
}

const profileSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters').max(50, 'Name must be less than 50 characters'),
  username: z.string().min(3, 'Username must be at least 3 characters').max(30, 'Username must be less than 30 characters').regex(/^[a-zA-Z0-9_]+$/, 'Username can only contain letters, numbers, and underscores'),
  email: z.string().email('Please enter a valid email address'),
  bio: z.string().max(500, 'Bio must be less than 500 characters').optional(),
  location: z.string().max(100, 'Location must be less than 100 characters').optional(),
  website: z.string().url('Please enter a valid URL').optional().or(z.literal('')),
  expertise: z.array(z.string()).min(1, 'Please select at least one area of expertise').max(10, 'Maximum 10 areas of expertise allowed'),
  privacy: z.object({
    profileVisibility: z.enum(['public', 'private']),
    showEmail: z.boolean(),
    showStats: z.boolean(),
    showActivity: z.boolean()
  }),
  notifications: z.object({
    emailNotifications: z.boolean(),
    discussionUpdates: z.boolean(),
    validationReminders: z.boolean(),
    weeklyDigest: z.boolean()
  })
});

type ProfileFormData = z.infer<typeof profileSchema>;

const expertiseOptions = [
  'Machine Learning',
  'Natural Language Processing',
  'Computer Vision',
  'Deep Learning',
  'Data Science',
  'Product Strategy',
  'Business Development',
  'Software Engineering',
  'DevOps',
  'Cybersecurity',
  'Blockchain',
  'IoT',
  'Robotics',
  'Healthcare AI',
  'Financial Technology',
  'Marketing Technology',
  'Educational Technology'
];

export function ProfileSettings({ profile, onSave, className }: ProfileSettingsProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [activeSection, setActiveSection] = useState<'profile' | 'privacy' | 'notifications'>('profile');
  const [newExpertise, setNewExpertise] = useState('');

  const form = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      name: profile.name,
      username: profile.username,
      email: profile.email,
      bio: profile.bio || '',
      location: profile.location || '',
      website: profile.website || '',
      expertise: profile.expertise,
      privacy: {
        profileVisibility: 'public',
        showEmail: false,
        showStats: true,
        showActivity: true
      },
      notifications: {
        emailNotifications: true,
        discussionUpdates: true,
        validationReminders: true,
        weeklyDigest: false
      }
    }
  });

  const watchedExpertise = form.watch('expertise');

  const onSubmit = async (data: ProfileFormData) => {
    setIsLoading(true);
    try {
      await onSave({
        name: data.name,
        username: data.username,
        email: data.email,
        bio: data.bio,
        location: data.location,
        website: data.website,
        expertise: data.expertise
      });
    } catch (error) {
      console.error('Failed to save profile:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const addExpertise = () => {
    if (newExpertise && !watchedExpertise.includes(newExpertise) && watchedExpertise.length < 10) {
      form.setValue('expertise', [...watchedExpertise, newExpertise]);
      setNewExpertise('');
    }
  };

  const removeExpertise = (expertise: string) => {
    form.setValue('expertise', watchedExpertise.filter(e => e !== expertise));
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const sections = [
    { id: 'profile', label: 'Profile Information', icon: User },
    { id: 'privacy', label: 'Privacy Settings', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell }
  ];

  return (
    <div className={cn('space-y-6', className)}>
      {/* Section Navigation */}
      <Card>
        <CardContent className="p-0">
          <div className="flex border-b">
            {sections.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id as 'profile' | 'privacy' | 'notifications')}
                  className={`flex items-center gap-2 px-6 py-4 text-sm font-medium transition-colors hover:text-primary ${
                    activeSection === section.id
                      ? 'border-b-2 border-primary text-primary'
                      : 'text-muted-foreground'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {section.label}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Profile Information Section */}
          {activeSection === 'profile' && (
            <div className="space-y-6">
              {/* Avatar and Basic Info */}
              <Card>
                <CardHeader>
                  <CardTitle>Profile Information</CardTitle>
                  <CardDescription>
                    Update your profile information and areas of expertise
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Avatar */}
                  <div className="flex items-center gap-4">
                    <Avatar className="w-20 h-20">
                      <AvatarFallback className="text-lg font-semibold">
                        {getInitials(form.watch('name') || profile.name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="space-y-2">
                      <h3 className="font-medium">Profile Picture</h3>
                      <p className="text-sm text-muted-foreground">
                        Avatar is generated from your name initials
                      </p>
                    </div>
                  </div>

                  <Separator />

                  {/* Basic Information */}
                  <div className="grid gap-4 md:grid-cols-2">
                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Full Name</FormLabel>
                          <FormControl>
                            <Input placeholder="Enter your full name" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="username"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Username</FormLabel>
                          <FormControl>
                            <Input placeholder="Enter your username" {...field} />
                          </FormControl>
                          <FormDescription>
                            This will be your unique identifier on the platform
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="email"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Email Address</FormLabel>
                          <FormControl>
                            <Input type="email" placeholder="Enter your email" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="location"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Location</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g., San Francisco, CA" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <FormField
                    control={form.control}
                    name="website"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Website</FormLabel>
                        <FormControl>
                          <Input placeholder="https://your-website.com" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="bio"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Bio</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Tell us about yourself and your interests in AI..."
                            className="min-h-24"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          {field.value?.length || 0}/500 characters
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>

              {/* Expertise Section */}
              <Card>
                <CardHeader>
                  <CardTitle>Areas of Expertise</CardTitle>
                  <CardDescription>
                    Select your areas of expertise to help others find you for relevant opportunities
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Current Expertise */}
                  <div className="space-y-2">
                    <FormLabel>Current Expertise</FormLabel>
                    <div className="flex flex-wrap gap-2">
                      {watchedExpertise.map((expertise) => (
                        <Badge key={expertise} variant="secondary" className="gap-1">
                          {expertise}
                          <button
                            type="button"
                            onClick={() => removeExpertise(expertise)}
                            className="ml-1 hover:text-destructive"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </Badge>
                      ))}
                    </div>
                    {form.formState.errors.expertise && (
                      <p className="text-sm text-destructive">
                        {form.formState.errors.expertise.message}
                      </p>
                    )}
                  </div>

                  {/* Add New Expertise */}
                  <div className="flex gap-2">
                    <Select value={newExpertise} onValueChange={setNewExpertise}>
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select an area of expertise" />
                      </SelectTrigger>
                      <SelectContent>
                        {expertiseOptions
                          .filter(option => !watchedExpertise.includes(option))
                          .map((option) => (
                            <SelectItem key={option} value={option}>
                              {option}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={addExpertise}
                      disabled={!newExpertise || watchedExpertise.length >= 10}
                    >
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {watchedExpertise.length}/10 areas selected
                  </p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Privacy Settings Section */}
          {activeSection === 'privacy' && (
            <Card>
              <CardHeader>
                <CardTitle>Privacy Settings</CardTitle>
                <CardDescription>
                  Control who can see your profile information and activity
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <FormField
                  control={form.control}
                  name="privacy.profileVisibility"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Profile Visibility</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="public">
                            <div className="flex items-center gap-2">
                              <Globe className="w-4 h-4" />
                              Public - Anyone can view your profile
                            </div>
                          </SelectItem>
                          <SelectItem value="private">
                            <div className="flex items-center gap-2">
                              <Lock className="w-4 h-4" />
                              Private - Only you can view your profile
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <Separator />

                <div className="space-y-4">
                  <h4 className="font-medium">Information Visibility</h4>
                  
                  <FormField
                    control={form.control}
                    name="privacy.showEmail"
                    render={({ field }) => (
                      <FormItem className="flex items-center justify-between">
                        <div>
                          <FormLabel>Show Email Address</FormLabel>
                          <FormDescription>
                            Allow others to see your email address on your profile
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Button
                            type="button"
                            variant={field.value ? "default" : "outline"}
                            size="sm"
                            onClick={() => field.onChange(!field.value)}
                          >
                            {field.value ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                          </Button>
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="privacy.showStats"
                    render={({ field }) => (
                      <FormItem className="flex items-center justify-between">
                        <div>
                          <FormLabel>Show Statistics</FormLabel>
                          <FormDescription>
                            Display your reputation score and contribution statistics
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Button
                            type="button"
                            variant={field.value ? "default" : "outline"}
                            size="sm"
                            onClick={() => field.onChange(!field.value)}
                          >
                            {field.value ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                          </Button>
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="privacy.showActivity"
                    render={({ field }) => (
                      <FormItem className="flex items-center justify-between">
                        <div>
                          <FormLabel>Show Activity Feed</FormLabel>
                          <FormDescription>
                            Allow others to see your recent activity and contributions
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Button
                            type="button"
                            variant={field.value ? "default" : "outline"}
                            size="sm"
                            onClick={() => field.onChange(!field.value)}
                          >
                            {field.value ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                          </Button>
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {/* Notifications Section */}
          {activeSection === 'notifications' && (
            <Card>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
                <CardDescription>
                  Choose how you want to be notified about platform activity
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <FormField
                  control={form.control}
                  name="notifications.emailNotifications"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between">
                      <div>
                        <FormLabel>Email Notifications</FormLabel>
                        <FormDescription>
                          Receive email notifications for important updates
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Button
                          type="button"
                          variant={field.value ? "default" : "outline"}
                          size="sm"
                          onClick={() => field.onChange(!field.value)}
                        >
                          {field.value ? <Bell className="w-4 h-4" /> : <X className="w-4 h-4" />}
                        </Button>
                      </FormControl>
                    </FormItem>
                  )}
                />

                <Separator />

                <div className="space-y-4">
                  <h4 className="font-medium">Specific Notifications</h4>
                  
                  <FormField
                    control={form.control}
                    name="notifications.discussionUpdates"
                    render={({ field }) => (
                      <FormItem className="flex items-center justify-between">
                        <div>
                          <FormLabel>Discussion Updates</FormLabel>
                          <FormDescription>
                            Get notified when someone replies to your comments
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Button
                            type="button"
                            variant={field.value ? "default" : "outline"}
                            size="sm"
                            onClick={() => field.onChange(!field.value)}
                          >
                            {field.value ? <Bell className="w-4 h-4" /> : <X className="w-4 h-4" />}
                          </Button>
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="notifications.validationReminders"
                    render={({ field }) => (
                      <FormItem className="flex items-center justify-between">
                        <div>
                          <FormLabel>Validation Reminders</FormLabel>
                          <FormDescription>
                            Reminders to validate opportunities in your expertise areas
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Button
                            type="button"
                            variant={field.value ? "default" : "outline"}
                            size="sm"
                            onClick={() => field.onChange(!field.value)}
                          >
                            {field.value ? <Bell className="w-4 h-4" /> : <X className="w-4 h-4" />}
                          </Button>
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="notifications.weeklyDigest"
                    render={({ field }) => (
                      <FormItem className="flex items-center justify-between">
                        <div>
                          <FormLabel>Weekly Digest</FormLabel>
                          <FormDescription>
                            Weekly summary of new opportunities and platform activity
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Button
                            type="button"
                            variant={field.value ? "default" : "outline"}
                            size="sm"
                            onClick={() => field.onChange(!field.value)}
                          >
                            {field.value ? <Bell className="w-4 h-4" /> : <X className="w-4 h-4" />}
                          </Button>
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {/* Save Button */}
          <div className="flex justify-end gap-4">
            <Button type="submit" disabled={isLoading} className="gap-2">
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              {isLoading ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </Form>

      {/* Danger Zone */}
      <Card className="border-destructive/20">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
          <CardDescription>
            Irreversible and destructive actions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" className="gap-2">
                <Trash2 className="w-4 h-4" />
                Delete Account
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action cannot be undone. This will permanently delete your
                  account and remove all your data from our servers, including:
                  <br />• Your profile and personal information
                  <br />• All your validations and contributions
                  <br />• Your collections and bookmarks
                  <br />• Your reputation score and achievements
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                  Yes, delete my account
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
    </div>
  );
}
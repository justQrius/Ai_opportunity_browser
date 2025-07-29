'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { 
  User, 
  Edit, 
  Star, 
  TrendingUp, 
  MessageCircle, 
  Bookmark,
  Activity,
  Award,
  Calendar,
  MapPin,
  Mail,
  Globe,
  Settings
} from 'lucide-react';
import { ProfileHeader } from '@/components/profile/profile-header';
import { ExpertiseSection } from '@/components/profile/expertise-section';
import { ActivityFeed } from '@/components/profile/activity-feed';
import { CollectionsSection } from '@/components/profile/collections-section';
import { ProfileSettings } from '@/components/profile/profile-settings';

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

// Mock data for development
const mockProfile: UserProfile = {
  id: '1',
  name: 'Demo User',
  email: 'demo@example.com',
  username: 'demo_user',
  bio: 'AI enthusiast and entrepreneur passionate about discovering market opportunities in artificial intelligence.',
  location: 'San Francisco, CA',
  website: 'https://demo-user.dev',
  joinedAt: '2024-01-15',
  expertise: ['Machine Learning', 'Natural Language Processing', 'Computer Vision', 'Product Strategy'],
  stats: {
    validationsCount: 47,
    discussionsCount: 23,
    bookmarksCount: 156,
    reputationScore: 2847
  }
};

export default function ProfilePage() {
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'activity' | 'collections' | 'settings'>('overview');

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth/login?redirect=/profile');
      return;
    }

    // In a real app, fetch user profile from API
    // For now, use mock data
    setTimeout(() => {
      setProfile(mockProfile);
      setLoading(false);
    }, 500);
  }, [isAuthenticated, router]);

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse space-y-6">
          <div className="h-32 bg-muted rounded-lg"></div>
          <div className="grid gap-6 md:grid-cols-3">
            <div className="h-64 bg-muted rounded-lg"></div>
            <div className="md:col-span-2 h-64 bg-muted rounded-lg"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <h1 className="text-2xl font-bold mb-4">Profile Not Found</h1>
        <p className="text-muted-foreground mb-4">Unable to load your profile.</p>
        <Button onClick={() => router.push('/opportunities')}>
          Back to Opportunities
        </Button>
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: User },
    { id: 'activity', label: 'Activity', icon: Activity },
    { id: 'collections', label: 'Collections', icon: Bookmark },
    { id: 'settings', label: 'Settings', icon: Settings }
  ];

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* Profile Header */}
      <ProfileHeader 
        profile={profile}
        onEdit={() => setActiveTab('settings')}
      />

      {/* Navigation Tabs */}
      <Card>
        <CardContent className="p-0">
          <div className="flex border-b">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as 'overview' | 'activity' | 'collections' | 'settings')}
                  className={`flex items-center gap-2 px-6 py-4 text-sm font-medium transition-colors hover:text-primary ${
                    activeTab === tab.id
                      ? 'border-b-2 border-primary text-primary'
                      : 'text-muted-foreground'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Tab Content */}
      <div className="grid gap-6 md:grid-cols-3">
        {activeTab === 'overview' && (
          <>
            {/* Left Column - Expertise & Stats */}
            <div className="space-y-6">
              <ExpertiseSection 
                expertise={profile.expertise}
                reputationScore={profile.stats.reputationScore}
              />
              
              {/* Quick Stats */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Award className="w-4 h-4" />
                    Contributions
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Star className="w-4 h-4 text-yellow-500" />
                      <span className="text-sm">Validations</span>
                    </div>
                    <Badge variant="secondary">{profile.stats.validationsCount}</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <MessageCircle className="w-4 h-4 text-blue-500" />
                      <span className="text-sm">Discussions</span>
                    </div>
                    <Badge variant="secondary">{profile.stats.discussionsCount}</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Bookmark className="w-4 h-4 text-green-500" />
                      <span className="text-sm">Bookmarks</span>
                    </div>
                    <Badge variant="secondary">{profile.stats.bookmarksCount}</Badge>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Right Column - Activity */}
            <div className="md:col-span-2">
              <ActivityFeed profileId={profile.id} />
            </div>
          </>
        )}

        {activeTab === 'activity' && (
          <div className="md:col-span-3">
            <ActivityFeed 
              profileId={profile.id} 
              showFilters={true}
              detailed={true}
            />
          </div>
        )}

        {activeTab === 'collections' && (
          <div className="md:col-span-3">
            <CollectionsSection 
              userId={profile.id}
              stats={profile.stats}
            />
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="md:col-span-3">
            <ProfileSettings 
              profile={profile}
              onSave={async (data) => {
                // TODO: Implement API call to save profile
                console.log('Saving profile:', data);
                // Update local state
                setProfile(prev => prev ? { ...prev, ...data } : null);
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
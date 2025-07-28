'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { 
  Edit, 
  Calendar, 
  MapPin, 
  Mail, 
  Globe,
  Star,
  TrendingUp
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

interface ProfileHeaderProps {
  profile: UserProfile;
  onEdit?: () => void;
  isOwnProfile?: boolean;
  className?: string;
}

export function ProfileHeader({ 
  profile, 
  onEdit, 
  isOwnProfile = true,
  className 
}: ProfileHeaderProps) {
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const formatJoinDate = (date: string) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long'
    });
  };

  const getReputationLevel = (score: number) => {
    if (score >= 5000) return { label: 'Expert', color: 'bg-purple-100 text-purple-800' };
    if (score >= 2000) return { label: 'Advanced', color: 'bg-blue-100 text-blue-800' };
    if (score >= 500) return { label: 'Intermediate', color: 'bg-green-100 text-green-800' };
    return { label: 'Beginner', color: 'bg-gray-100 text-gray-800' };
  };

  const reputationLevel = getReputationLevel(profile.stats.reputationScore);

  return (
    <Card className={cn('overflow-hidden', className)}>
      <div className="h-24 bg-gradient-to-r from-blue-500 to-purple-600"></div>
      <CardContent className="relative -mt-12 pb-6">
        <div className="flex flex-col sm:flex-row gap-4 items-start">
          {/* Avatar */}
          <Avatar className="w-24 h-24 border-4 border-background shadow-lg">
            <AvatarFallback className="text-lg font-semibold">
              {getInitials(profile.name)}
            </AvatarFallback>
          </Avatar>

          {/* Profile Info */}
          <div className="flex-1 pt-12 sm:pt-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold">{profile.name}</h1>
                <p className="text-muted-foreground">@{profile.username}</p>
              </div>
              
              {isOwnProfile && onEdit && (
                <Button variant="outline" onClick={onEdit} className="gap-2 shrink-0">
                  <Edit className="w-4 h-4" />
                  Edit Profile
                </Button>
              )}
            </div>

            {/* Bio */}
            {profile.bio && (
              <p className="mt-4 text-muted-foreground leading-relaxed">
                {profile.bio}
              </p>
            )}

            {/* Reputation & Stats */}
            <div className="mt-4 flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <Star className="w-4 h-4 text-yellow-500" />
                <span className="font-medium">{profile.stats.reputationScore.toLocaleString()}</span>
                <Badge className={reputationLevel.color}>
                  {reputationLevel.label}
                </Badge>
              </div>
              
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <TrendingUp className="w-4 h-4" />
                <span>{profile.stats.validationsCount} validations</span>
              </div>
            </div>

            {/* Profile Details */}
            <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                <span>Joined {formatJoinDate(profile.joinedAt)}</span>
              </div>
              
              {profile.location && (
                <div className="flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  <span>{profile.location}</span>
                </div>
              )}
              
              {profile.email && isOwnProfile && (
                <div className="flex items-center gap-1">
                  <Mail className="w-4 h-4" />
                  <span>{profile.email}</span>
                </div>
              )}
              
              {profile.website && (
                <a 
                  href={profile.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 hover:text-primary transition-colors"
                >
                  <Globe className="w-4 h-4" />
                  <span>Website</span>
                </a>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
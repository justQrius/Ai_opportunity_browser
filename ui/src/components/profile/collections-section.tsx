'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { 
  Bookmark,
  Plus,
  Search,
  Grid3X3,
  List,
  ArrowUpDown,
  Folder,
  FolderOpen
} from 'lucide-react';
import { OpportunityCard } from '@/components/opportunity-card';
import { cn } from '@/lib/utils';
import { CollectionModal } from './collection-modal';

interface Collection {
  id: string;
  name: string;
  description?: string;
  opportunityCount: number;
  isPrivate: boolean;
  createdAt: string;
  updatedAt: string;
}

interface BookmarkedOpportunity {
  id: string;
  title: string;
  description: string;
  industry: string;
  aiSolutionType: string;
  validationScore: number;
  bookmarkedAt: string;
  collections: string[]; // Collection IDs
}

interface CollectionsSectionProps {
  userId: string;
  stats: {
    bookmarksCount: number;
    validationsCount: number;
    discussionsCount: number;
    reputationScore: number;
  };
  className?: string;
}

// Mock collections data
const mockCollections: Collection[] = [
  {
    id: '1',
    name: 'High Potential',
    description: 'Opportunities I believe have exceptional market potential',
    opportunityCount: 23,
    isPrivate: false,
    createdAt: '2024-01-10',
    updatedAt: '2024-01-20'
  },
  {
    id: '2',
    name: 'Healthcare AI',
    description: 'AI opportunities specifically in healthcare domain',
    opportunityCount: 15,
    isPrivate: false,
    createdAt: '2024-01-05',
    updatedAt: '2024-01-18'
  },
  {
    id: '3',
    name: 'Quick Wins',
    description: 'Low complexity opportunities that could be implemented quickly',
    opportunityCount: 31,
    isPrivate: true,
    createdAt: '2023-12-20',
    updatedAt: '2024-01-19'
  },
  {
    id: '4',
    name: 'Research Later',
    description: 'Interesting ideas that need more investigation',
    opportunityCount: 8,
    isPrivate: true,
    createdAt: '2024-01-15',
    updatedAt: '2024-01-20'
  }
];

const mockBookmarkedOpportunities: BookmarkedOpportunity[] = [
  {
    id: '123',
    title: 'AI-Powered Customer Service Automation for SMBs',
    description: 'Automated customer service system using NLP to handle 80% of customer inquiries for small and medium businesses.',
    industry: 'Technology',
    aiSolutionType: 'Natural Language Processing',
    validationScore: 87,
    bookmarkedAt: '2024-01-20',
    collections: ['1', '3']
  },
  {
    id: '456',
    title: 'AI Diagnostic Assistant for Rural Healthcare',
    description: 'Machine learning system to assist rural healthcare providers with preliminary diagnosis suggestions.',
    industry: 'Healthcare',
    aiSolutionType: 'Machine Learning',
    validationScore: 92,
    bookmarkedAt: '2024-01-19',
    collections: ['1', '2']
  },
  {
    id: '789',
    title: 'Automated Inventory Management with Computer Vision',
    description: 'Computer vision solution for real-time inventory tracking in retail environments.',
    industry: 'Retail',
    aiSolutionType: 'Computer Vision',
    validationScore: 76,
    bookmarkedAt: '2024-01-18',
    collections: ['3']
  }
];

export function CollectionsSection({ userId, stats, className }: CollectionsSectionProps) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [bookmarkedOpportunities, setBookmarkedOpportunities] = useState<BookmarkedOpportunity[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [isCollectionModalOpen, setIsCollectionModalOpen] = useState(false);
  const [editingCollection, setEditingCollection] = useState<Collection | undefined>();

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      setCollections(mockCollections);
      setBookmarkedOpportunities(mockBookmarkedOpportunities);
      setLoading(false);
    }, 500);
  }, [userId]);

  const getFilteredOpportunities = () => {
    let filtered = bookmarkedOpportunities;

    // Filter by selected collection
    if (selectedCollection) {
      filtered = filtered.filter(opp => opp.collections.includes(selectedCollection));
    }

    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter(opp => 
        opp.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        opp.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        opp.industry.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Sort
    switch (sortBy) {
      case 'title':
        filtered.sort((a, b) => a.title.localeCompare(b.title));
        break;
      case 'score':
        filtered.sort((a, b) => b.validationScore - a.validationScore);
        break;
      case 'recent':
      default:
        filtered.sort((a, b) => new Date(b.bookmarkedAt).getTime() - new Date(a.bookmarkedAt).getTime());
        break;
    }

    return filtered;
  };

  const selectedCollectionData = selectedCollection 
    ? collections.find(c => c.id === selectedCollection)
    : null;

  if (loading) {
    return (
      <div className={cn('space-y-6', className)}>
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-muted rounded-lg"></div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-24 bg-muted rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const handleCreateCollection = async (collectionData: { name: string; description?: string; isPrivate: boolean }) => {
    // TODO: Implement API call
    const newCollection: Collection = {
      id: Date.now().toString(),
      name: collectionData.name,
      description: collectionData.description,
      isPrivate: collectionData.isPrivate,
      opportunityCount: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    setCollections(prev => [...prev, newCollection]);
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Collections Overview */}
      {!selectedCollection && (
        <>
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Bookmark className="w-5 h-5" />
                    My Collections
                  </CardTitle>
                  <CardDescription>
                    Organize your bookmarked opportunities into collections
                  </CardDescription>
                </div>
                <Button className="gap-2" onClick={() => setIsCollectionModalOpen(true)}>
                  <Plus className="w-4 h-4" />
                  New Collection
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {/* All Bookmarks */}
                <Card 
                  className="cursor-pointer hover:shadow-md transition-shadow border-2 border-dashed"
                  onClick={() => setSelectedCollection(null)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Bookmark className="w-4 h-4 text-muted-foreground" />
                        <span className="font-medium">All Bookmarks</span>
                      </div>
                      <Badge variant="secondary">{stats.bookmarksCount}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      View all your bookmarked opportunities
                    </p>
                  </CardContent>
                </Card>

                {/* User Collections */}
                {collections.map((collection) => (
                  <Card 
                    key={collection.id}
                    className="cursor-pointer hover:shadow-md transition-shadow"
                    onClick={() => setSelectedCollection(collection.id)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {collection.isPrivate ? (
                            <Folder className="w-4 h-4 text-muted-foreground" />
                          ) : (
                            <FolderOpen className="w-4 h-4 text-muted-foreground" />
                          )}
                          <span className="font-medium">{collection.name}</span>
                          {collection.isPrivate && (
                            <Badge variant="outline" className="text-xs">Private</Badge>
                          )}
                        </div>
                        <Badge variant="secondary">{collection.opportunityCount}</Badge>
                      </div>
                      {collection.description && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {collection.description}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Collection/Bookmarks View */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                {selectedCollectionData ? (
                  <>
                    <FolderOpen className="w-5 h-5" />
                    {selectedCollectionData.name}
                  </>
                ) : (
                  <>
                    <Bookmark className="w-5 h-5" />
                    All Bookmarks
                  </>
                )}
              </CardTitle>
              {selectedCollectionData?.description && (
                <CardDescription>{selectedCollectionData.description}</CardDescription>
              )}
              {selectedCollection && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setSelectedCollection(null)}
                  className="mt-2 gap-2"
                >
                  ← Back to Collections
                </Button>
              )}
            </div>

            <div className="flex items-center gap-2">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search bookmarks..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 w-48"
                />
              </div>

              {/* Sort */}
              <Button variant="outline" size="sm" className="gap-2">
                <ArrowUpDown className="w-4 h-4" />
                Sort by {sortBy}
              </Button>

              {/* View Mode */}
              <div className="flex rounded-md border">
                <Button
                  variant={viewMode === 'grid' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('grid')}
                  className="rounded-r-none"
                >
                  <Grid3X3 className="w-4 h-4" />
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('list')}
                  className="rounded-l-none"
                >
                  <List className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {getFilteredOpportunities().length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Bookmark className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium mb-2">No bookmarks found</h3>
              <p className="mb-4">
                {searchQuery 
                  ? `No bookmarks match "${searchQuery}"`
                  : selectedCollection 
                    ? "This collection is empty"
                    : "You haven't bookmarked any opportunities yet"
                }
              </p>
              <Button variant="outline">
                Browse Opportunities
              </Button>
            </div>
          ) : (
            <div className={cn(
              viewMode === 'grid' 
                ? 'grid gap-6 md:grid-cols-2 lg:grid-cols-3' 
                : 'space-y-4'
            )}>
              {getFilteredOpportunities().map((opportunity) => (
                <div key={opportunity.id} className="relative">
                  <OpportunityCard
                    opportunity={{
                      id: opportunity.id,
                      title: opportunity.title,
                      description: opportunity.description,
                      industry: opportunity.industry,
                      ai_solution_type: opportunity.aiSolutionType,
                      validation_score: opportunity.validationScore,
                      ai_feasibility_score: 85,
                      market_size_estimate: 5000000,
                      implementation_complexity: 'MEDIUM',
                      validation_count: 12,
                      created_at: opportunity.bookmarkedAt,
                      updated_at: opportunity.bookmarkedAt
                    }}
                    variant={viewMode === 'list' ? 'compact' : 'default'}
                  />
                  
                  {/* Collection badges */}
                  {opportunity.collections.length > 0 && (
                    <div className="absolute top-2 right-2 flex flex-wrap gap-1">
                      {opportunity.collections.map((collectionId) => {
                        const collection = collections.find(c => c.id === collectionId);
                        return collection ? (
                          <Badge 
                            key={collectionId} 
                            variant="secondary" 
                            className="text-xs"
                          >
                            {collection.name}
                          </Badge>
                        ) : null;
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <CollectionModal
        isOpen={isCollectionModalOpen}
        onClose={() => {
          setIsCollectionModalOpen(false);
          setEditingCollection(undefined);
        }}
        onSave={handleCreateCollection}
        collection={editingCollection}
        mode={editingCollection ? 'edit' : 'create'}
      />
    </div>
  );
}
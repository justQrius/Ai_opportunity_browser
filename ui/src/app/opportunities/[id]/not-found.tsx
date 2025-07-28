import React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Search, ArrowLeft, Home } from 'lucide-react';

export default function OpportunityNotFound() {
  return (
    <div className="container mx-auto px-4 py-12">
      <Card className="max-w-md mx-auto text-center">
        <CardContent className="p-8">
          <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
            <Search className="w-8 h-8 text-muted-foreground" />
          </div>
          
          <h1 className="text-2xl font-bold mb-2">Opportunity Not Found</h1>
          <p className="text-muted-foreground mb-6">
            The opportunity you're looking for doesn't exist or may have been removed.
          </p>
          
          <div className="space-y-3">
            <Button asChild className="w-full">
              <Link href="/opportunities" className="gap-2">
                <Search className="w-4 h-4" />
                Browse All Opportunities
              </Link>
            </Button>
            
            <Button variant="outline" asChild className="w-full">
              <Link href="/" className="gap-2">
                <Home className="w-4 h-4" />
                Go Home
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
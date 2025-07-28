'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Save, Folder, Lock, Globe } from 'lucide-react';

interface Collection {
  id: string;
  name: string;
  description?: string;
  opportunityCount: number;
  isPrivate: boolean;
  createdAt: string;
  updatedAt: string;
}

interface CollectionFormData {
  name: string;
  description?: string;
  isPrivate: boolean;
}

interface CollectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (collection: CollectionFormData) => Promise<void>;
  collection?: Collection;
  mode: 'create' | 'edit';
}

const collectionSchema = z.object({
  name: z.string().min(1, 'Collection name is required').max(50, 'Name must be less than 50 characters'),
  description: z.string().max(200, 'Description must be less than 200 characters').optional(),
  isPrivate: z.boolean()
});

export function CollectionModal({ 
  isOpen, 
  onClose, 
  onSave, 
  collection, 
  mode 
}: CollectionModalProps) {
  const [isLoading, setIsLoading] = useState(false);

  const form = useForm<CollectionFormData>({
    resolver: zodResolver(collectionSchema),
    defaultValues: {
      name: collection?.name || '',
      description: collection?.description || '',
      isPrivate: collection?.isPrivate || false
    }
  });

  const onSubmit = async (data: CollectionFormData) => {
    setIsLoading(true);
    try {
      await onSave(data);
      onClose();
      form.reset();
    } catch (error) {
      console.error('Failed to save collection:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    onClose();
    form.reset();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Folder className="w-5 h-5" />
            {mode === 'create' ? 'Create New Collection' : 'Edit Collection'}
          </DialogTitle>
          <DialogDescription>
            {mode === 'create' 
              ? 'Create a new collection to organize your bookmarked opportunities'
              : 'Update your collection details'
            }
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Collection Name</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g., High Potential Opportunities" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description (Optional)</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Describe what kind of opportunities you'll save in this collection..."
                      className="min-h-20"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    {field.value?.length || 0}/200 characters
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="isPrivate"
              render={({ field }) => (
                <FormItem className="flex items-center justify-between space-y-0">
                  <div className="space-y-1">
                    <FormLabel>Privacy Setting</FormLabel>
                    <FormDescription className="flex items-center gap-2">
                      {field.value ? (
                        <>
                          <Lock className="w-4 h-4" />
                          Private - Only you can see this collection
                        </>
                      ) : (
                        <>
                          <Globe className="w-4 h-4" />
                          Public - Others can see this collection
                        </>
                      )}
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading} className="gap-2">
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                {isLoading ? 'Saving...' : mode === 'create' ? 'Create Collection' : 'Save Changes'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
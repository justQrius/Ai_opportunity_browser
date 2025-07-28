import { LoadingSpinner } from '@/components';

export default function OpportunityLoading() {
  return (
    <div className="container mx-auto px-4 py-6">
      <LoadingSpinner 
        text="Loading opportunity details..." 
        className="py-12"
        variant="ai-themed"
        size="lg"
        centered
      />
    </div>
  );
}
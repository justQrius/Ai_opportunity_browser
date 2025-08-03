"use client";

import { OpportunityCreationForm } from "@/components/opportunity-creation-form";

export default function NewOpportunityPage() {
  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-6">Generate New Opportunity</h1>
      <OpportunityCreationForm />
    </div>
  );
}

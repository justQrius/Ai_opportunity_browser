#!/usr/bin/env python3
"""
Demo script for search endpoints implementation.

This script demonstrates the semantic search and faceted search capabilities
implemented for task 6.1.2.

Requirements tested:
- Semantic search with vector similarity
- Faceted search capabilities
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.schemas.opportunity import OpportunitySearchRequest
from shared.services.opportunity_service import opportunity_service
from shared.services.ai_service import ai_service
from shared.vector_db import opportunity_vector_service


def create_sample_opportunities():
    """Create sample opportunities for demonstration."""
    return [
        Opportunity(
            id="opp-1",
            title="AI-Powered Customer Service Chatbot",
            description="Develop an intelligent chatbot for customer service automation using NLP and machine learning",
            summary="AI chatbot for customer support automation",
            ai_solution_types='["NLP", "ML", "Conversational AI"]',
            target_industries='["Technology", "E-commerce", "SaaS"]',
            tags='["chatbot", "customer-service", "automation", "nlp"]',
            status=OpportunityStatus.VALIDATED,
            validation_score=8.5,
            ai_feasibility_score=7.8,
            geographic_scope="Global",
            implementation_complexity="Medium",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Opportunity(
            id="opp-2",
            title="Computer Vision for Manufacturing Quality Control",
            description="Implement computer vision system for automated quality control in manufacturing processes",
            summary="CV system for manufacturing quality assurance",
            ai_solution_types='["Computer Vision", "ML", "Image Recognition"]',
            target_industries='["Manufacturing", "Automotive", "Electronics"]',
            tags='["computer-vision", "quality-control", "manufacturing", "automation"]',
            status=OpportunityStatus.VALIDATED,
            validation_score=9.2,
            ai_feasibility_score=8.1,
            geographic_scope="North America",
            implementation_complexity="High",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Opportunity(
            id="opp-3",
            title="Predictive Analytics for Healthcare Outcomes",
            description="Build predictive models for patient outcome prediction and treatment optimization",
            summary="Predictive analytics for healthcare decision support",
            ai_solution_types='["ML", "Predictive Analytics", "Data Science"]',
            target_industries='["Healthcare", "Medical", "Pharmaceuticals"]',
            tags='["healthcare", "predictive-analytics", "patient-care", "medical-ai"]',
            status=OpportunityStatus.VALIDATING,
            validation_score=6.8,
            ai_feasibility_score=7.2,
            geographic_scope="United States",
            implementation_complexity="High",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Opportunity(
            id="opp-4",
            title="Natural Language Processing for Document Analysis",
            description="Develop NLP system for automated document processing and information extraction",
            summary="NLP for document automation",
            ai_solution_types='["NLP", "Text Analytics", "ML"]',
            target_industries='["Legal", "Finance", "Insurance"]',
            tags='["nlp", "document-processing", "text-analysis", "automation"]',
            status=OpportunityStatus.VALIDATED,
            validation_score=7.9,
            ai_feasibility_score=8.3,
            geographic_scope="Global",
            implementation_complexity="Medium",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Opportunity(
            id="opp-5",
            title="Recommendation System for E-commerce",
            description="Build personalized recommendation engine for e-commerce platforms",
            summary="AI-powered product recommendations",
            ai_solution_types='["Recommendation Systems", "ML", "Collaborative Filtering"]',
            target_industries='["E-commerce", "Retail", "Technology"]',
            tags='["recommendations", "e-commerce", "personalization", "ml"]',
            status=OpportunityStatus.DISCOVERED,
            validation_score=5.4,
            ai_feasibility_score=6.7,
            geographic_scope="Global",
            implementation_complexity="Low",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    ]


async def demo_semantic_search():
    """Demonstrate semantic search functionality."""
    print("=" * 60)
    print("SEMANTIC SEARCH DEMONSTRATION")
    print("=" * 60)
    
    # Create mock database and sample data
    mock_db = AsyncMock()
    sample_opportunities = create_sample_opportunities()
    
    # Mock AI service embedding generation
    mock_embedding = [0.1 + i * 0.001 for i in range(1536)]  # Mock 1536-dimensional embedding
    
    # Mock vector search results (sorted by similarity)
    mock_vector_results = [
        {"id": "opp-1", "score": 0.95, "metadata": {"title": "AI-Powered Customer Service Chatbot"}},
        {"id": "opp-4", "score": 0.87, "metadata": {"title": "Natural Language Processing for Document Analysis"}},
        {"id": "opp-2", "score": 0.72, "metadata": {"title": "Computer Vision for Manufacturing Quality Control"}}
    ]
    
    with patch.object(ai_service, 'generate_search_query_embedding', return_value=mock_embedding), \
         patch.object(opportunity_vector_service, 'find_similar_opportunities', return_value=mock_vector_results), \
         patch('shared.services.opportunity_service.select') as mock_select:
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            sample_opportunities[0],  # opp-1
            sample_opportunities[3],  # opp-4
            sample_opportunities[1]   # opp-2
        ]
        mock_db.execute.return_value = mock_result
        
        # Test different search queries
        search_queries = [
            "AI chatbot for customer service",
            "computer vision quality control",
            "natural language processing documents",
            "machine learning healthcare"
        ]
        
        for query in search_queries:
            print(f"\n🔍 Search Query: '{query}'")
            print("-" * 40)
            
            # Create search request
            search_request = OpportunitySearchRequest(
                query=query,
                page=1,
                page_size=5
            )
            
            # Execute semantic search
            opportunities, total_count = await opportunity_service.semantic_search_opportunities(
                mock_db, search_request, "demo-user"
            )
            
            print(f"📊 Results: {len(opportunities)} opportunities found (total: {total_count})")
            
            for i, opp in enumerate(opportunities, 1):
                similarity_score = getattr(opp, '_similarity_score', 0.0)
                print(f"  {i}. {opp.title}")
                print(f"     Similarity: {similarity_score:.3f} | Validation: {opp.validation_score}/10")
                print(f"     AI Types: {opp.ai_solution_types}")
                print(f"     Industries: {opp.target_industries}")
                print()


async def demo_faceted_search():
    """Demonstrate faceted search functionality."""
    print("=" * 60)
    print("FACETED SEARCH DEMONSTRATION")
    print("=" * 60)
    
    # Create mock database and sample data
    mock_db = AsyncMock()
    sample_opportunities = create_sample_opportunities()
    
    with patch('shared.services.opportunity_service.select') as mock_select:
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_opportunities
        mock_db.execute.return_value = mock_result
        
        # Test faceted search without query
        print("\n📊 All Opportunities Facets:")
        print("-" * 30)
        
        facets = await opportunity_service.get_search_facets(mock_db, None)
        
        # Display facet results
        print(f"Total Opportunities: {facets['_metadata']['total_opportunities']}")
        print()
        
        print("Status Distribution:")
        for status, count in facets["status"].items():
            print(f"  • {status.title()}: {count}")
        print()
        
        print("AI Solution Types:")
        for ai_type, count in sorted(facets["ai_solution_types"].items(), key=lambda x: x[1], reverse=True):
            print(f"  • {ai_type}: {count}")
        print()
        
        print("Target Industries:")
        for industry, count in sorted(facets["target_industries"].items(), key=lambda x: x[1], reverse=True):
            print(f"  • {industry}: {count}")
        print()
        
        print("Implementation Complexity:")
        for complexity, count in facets["implementation_complexity"].items():
            print(f"  • {complexity}: {count}")
        print()
        
        print("Validation Score Ranges:")
        for score_range, count in facets["validation_score_ranges"].items():
            print(f"  • {score_range}: {count}")
        print()
        
        print("Popular Tags:")
        for tag, count in sorted(facets["tags"].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  • {tag}: {count}")
        print()
        
        # Test faceted search with query filter
        print("\n🔍 Facets for 'AI' related opportunities:")
        print("-" * 40)
        
        # Mock filtered results (opportunities containing "AI")
        ai_opportunities = [opp for opp in sample_opportunities if "AI" in opp.title or "ai" in opp.tags.lower()]
        mock_result.scalars.return_value.all.return_value = ai_opportunities
        
        ai_facets = await opportunity_service.get_search_facets(mock_db, "AI")
        
        print(f"Filtered Opportunities: {ai_facets['_metadata']['total_opportunities']}")
        print()
        
        print("AI-Related Status Distribution:")
        for status, count in ai_facets["status"].items():
            print(f"  • {status.title()}: {count}")
        print()
        
        print("AI-Related Solution Types:")
        for ai_type, count in sorted(ai_facets["ai_solution_types"].items(), key=lambda x: x[1], reverse=True):
            print(f"  • {ai_type}: {count}")


async def demo_embedding_generation():
    """Demonstrate embedding generation for opportunities."""
    print("=" * 60)
    print("EMBEDDING GENERATION DEMONSTRATION")
    print("=" * 60)
    
    sample_opportunities = create_sample_opportunities()
    
    # Mock AI service
    mock_embedding = [0.1 + i * 0.001 for i in range(1536)]
    
    with patch.object(ai_service, 'generate_opportunity_embedding', return_value=mock_embedding), \
         patch.object(opportunity_vector_service, 'store_opportunity_embedding', return_value=True) as mock_store:
        
        print("\n🧠 Generating embeddings for sample opportunities...")
        print("-" * 50)
        
        for i, opportunity in enumerate(sample_opportunities[:3], 1):
            print(f"\n{i}. Processing: {opportunity.title}")
            
            # Generate and store embedding
            await opportunity_service._generate_and_store_embedding(opportunity)
            
            print(f"   ✅ Embedding generated (dimension: {len(mock_embedding)})")
            print(f"   ✅ Stored in vector database")
            
            # Verify the call was made
            if mock_store.call_count >= i:
                call_args = mock_store.call_args
                metadata = call_args[1]["metadata"]
                print(f"   📊 Metadata: Status={metadata['status']}, Score={metadata['validation_score']}")
        
        print(f"\n📈 Total embeddings generated: {mock_store.call_count}")


async def demo_search_with_filters():
    """Demonstrate search with various filters."""
    print("=" * 60)
    print("SEARCH WITH FILTERS DEMONSTRATION")
    print("=" * 60)
    
    mock_db = AsyncMock()
    sample_opportunities = create_sample_opportunities()
    
    # Mock vector search and database
    mock_embedding = [0.1] * 1536
    mock_vector_results = [
        {"id": "opp-1", "score": 0.95, "metadata": {"title": "AI Chatbot"}},
        {"id": "opp-2", "score": 0.87, "metadata": {"title": "Computer Vision"}}
    ]
    
    with patch.object(ai_service, 'generate_search_query_embedding', return_value=mock_embedding), \
         patch.object(opportunity_vector_service, 'find_similar_opportunities', return_value=mock_vector_results), \
         patch('shared.services.opportunity_service.select') as mock_select:
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_opportunities[:2]
        mock_db.execute.return_value = mock_result
        
        # Test different filter combinations
        filter_tests = [
            {
                "name": "High-quality validated opportunities",
                "filters": {
                    "query": "AI automation",
                    "status": [OpportunityStatus.VALIDATED],
                    "min_validation_score": 8.0
                }
            },
            {
                "name": "NLP and ML opportunities in Technology",
                "filters": {
                    "query": "natural language processing",
                    "ai_solution_types": ["NLP", "ML"],
                    "target_industries": ["Technology"]
                }
            },
            {
                "name": "Global medium complexity opportunities",
                "filters": {
                    "query": "machine learning",
                    "geographic_scope": "Global",
                    "implementation_complexity": ["Medium"]
                }
            }
        ]
        
        for test in filter_tests:
            print(f"\n🎯 Filter Test: {test['name']}")
            print("-" * 50)
            
            # Create search request with filters
            search_request = OpportunitySearchRequest(
                page=1,
                page_size=10,
                **test["filters"]
            )
            
            print("Applied Filters:")
            for key, value in test["filters"].items():
                if value:
                    print(f"  • {key}: {value}")
            
            # Execute search
            opportunities, total_count = await opportunity_service.semantic_search_opportunities(
                mock_db, search_request, "demo-user"
            )
            
            print(f"\n📊 Results: {len(opportunities)} opportunities found")
            
            for i, opp in enumerate(opportunities, 1):
                print(f"  {i}. {opp.title}")
                print(f"     Status: {opp.status.value} | Score: {opp.validation_score}/10")
                print(f"     Complexity: {opp.implementation_complexity}")
                print()


async def main():
    """Run all demonstrations."""
    print("🚀 AI Opportunity Browser - Search Endpoints Demo")
    print("Task 6.1.2: Semantic Search with Vector Similarity & Faceted Search")
    print("=" * 80)
    
    try:
        # Run demonstrations
        await demo_semantic_search()
        await demo_faceted_search()
        await demo_embedding_generation()
        await demo_search_with_filters()
        
        print("=" * 80)
        print("✅ DEMO COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nImplemented Features:")
        print("• Semantic search using vector similarity")
        print("• Faceted search with multiple filter categories")
        print("• Automatic embedding generation for opportunities")
        print("• Advanced filtering with multiple criteria")
        print("• Fallback to regular search on errors")
        print("• Comprehensive test coverage")
        
        print("\nAPI Endpoints Added:")
        print("• POST /api/v1/opportunities/search/semantic - Semantic search")
        print("• GET /api/v1/opportunities/search/facets - Faceted search data")
        print("• Enhanced existing search with vector capabilities")
        
        print("\nKey Technologies:")
        print("• OpenAI embeddings (with mock fallback)")
        print("• Pinecone vector database")
        print("• FastAPI async endpoints")
        print("• SQLAlchemy async queries")
        print("• Comprehensive error handling")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
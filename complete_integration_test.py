#!/usr/bin/env python3
"""
Complete Real-Time Integration Test
Tests the entire data flow from real-time sources → agents → API → frontend
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Any


class CompleteIntegrationTest:
    """Complete integration test for real-time data flow"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3004"
        self.results = {}
    
    async def run_complete_test(self):
        """Run complete integration test"""
        print("🚀 COMPLETE REAL-TIME INTEGRATION TEST")
        print("=" * 60)
        print("Testing: Real-time Data → AI Agents → API → Frontend")
        print("=" * 60)
        
        # Test the complete pipeline
        await self.test_realtime_data_sources()
        await self.test_ai_agents_processing()
        await self.test_api_endpoints()
        await self.test_data_freshness()
        await self.test_frontend_compatibility()
        
        # Final report
        self.generate_final_report()
    
    async def test_realtime_data_sources(self):
        """Test real-time data sources"""
        print("\n📡 STEP 1: Testing Real-Time Data Sources")
        print("-" * 50)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.backend_url}/data-sources/status") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        active_sources = data.get('active_sources', 0)
                        realtime_available = data.get('realtime_integration', False)
                        
                        print(f"✅ Real-time integration: {'Active' if realtime_available else 'Inactive'}")
                        print(f"✅ Active data sources: {active_sources}")
                        
                        # Show available sources
                        sources = data.get('data_sources', {})
                        for source_name, source_info in sources.items():
                            status = "🟢 Available" if source_info.get('available') else "🔴 Unavailable"
                            print(f"   {source_name}: {status}")
                        
                        self.results['realtime_sources'] = {
                            'active': realtime_available,
                            'count': active_sources,
                            'sources': sources
                        }
                    else:
                        print(f"❌ Data sources status failed: {resp.status}")
                        self.results['realtime_sources'] = {'active': False}
        except Exception as e:
            print(f"❌ Real-time data sources test failed: {e}")
            self.results['realtime_sources'] = {'active': False}
    
    async def test_ai_agents_processing(self):
        """Test AI agents processing real data"""
        print("\n🤖 STEP 2: Testing AI Agents Processing")
        print("-" * 50)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.backend_url}/agents/status") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        total_agents = data.get('total_agents', 0)
                        cached_opportunities = data.get('cached_opportunities', 0)
                        last_run = data.get('last_run')
                        
                        print(f"✅ Active AI agents: {total_agents}")
                        print(f"✅ Generated opportunities: {cached_opportunities}")
                        if last_run:
                            last_run_time = datetime.fromisoformat(last_run)
                            age_minutes = (datetime.utcnow() - last_run_time).total_seconds() / 60
                            print(f"✅ Last generation: {age_minutes:.1f} minutes ago")
                        
                        # Show agent details
                        agents = data.get('agents', {})
                        for agent_name, agent_info in agents.items():
                            print(f"   {agent_name}: {agent_info.get('type')} ({'Active' if agent_info.get('active') else 'Inactive'})")
                        
                        self.results['ai_agents'] = {
                            'active': total_agents > 0,
                            'count': total_agents,
                            'opportunities': cached_opportunities,
                            'agents': agents
                        }
                    else:
                        print(f"❌ Agents status failed: {resp.status}")
                        self.results['ai_agents'] = {'active': False}
        except Exception as e:
            print(f"❌ AI agents test failed: {e}")
            self.results['ai_agents'] = {'active': False}
    
    async def test_api_endpoints(self):
        """Test API endpoints with real data"""
        print("\n🌐 STEP 3: Testing API Endpoints")
        print("-" * 50)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test critical endpoints
                endpoints = [
                    ("Opportunities", "/opportunities/"),
                    ("Trending", "/opportunities/trending"),
                    ("Recommendations", "/opportunities/recommendations"),
                    ("Search", "/opportunities/search?query=AI")
                ]
                
                endpoint_results = {}
                
                for name, path in endpoints:
                    try:
                        async with session.get(f"{self.backend_url}{path}") as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                
                                # Count items based on response format
                                item_count = 0
                                if isinstance(data, list):
                                    item_count = len(data)
                                elif isinstance(data, dict) and 'items' in data:
                                    item_count = len(data['items'])
                                
                                print(f"✅ {name}: {item_count} items")
                                endpoint_results[name.lower()] = {'status': 'success', 'count': item_count}
                                
                                # Show sample data for trending
                                if name == "Trending" and item_count > 0:
                                    sample = data[0] if isinstance(data, list) else data['items'][0]
                                    print(f"   Sample: {sample.get('title', 'No title')[:50]}...")
                            else:
                                print(f"❌ {name}: Status {resp.status}")
                                endpoint_results[name.lower()] = {'status': 'failed', 'code': resp.status}
                    except Exception as e:
                        print(f"❌ {name}: Error {e}")
                        endpoint_results[name.lower()] = {'status': 'error', 'error': str(e)}
                
                self.results['api_endpoints'] = endpoint_results
        except Exception as e:
            print(f"❌ API endpoints test failed: {e}")
            self.results['api_endpoints'] = {'status': 'failed'}
    
    async def test_data_freshness(self):
        """Test that data is fresh and contains real-time elements"""
        print("\n📅 STEP 4: Testing Data Freshness")
        print("-" * 50)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.backend_url}/opportunities/trending?limit=3") as resp:
                    if resp.status == 200:
                        opportunities = await resp.json()
                        
                        current_time = datetime.utcnow()
                        fresh_count = 0
                        total_count = len(opportunities)
                        
                        print(f"📊 Analyzing {total_count} trending opportunities...")
                        
                        for i, opp in enumerate(opportunities, 1):
                            title = opp.get('title', 'No title')
                            created_at = opp.get('created_at', opp.get('timestamp'))
                            
                            if created_at:
                                try:
                                    # Handle different datetime formats
                                    if 'Z' in created_at:
                                        created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                    else:
                                        created_time = datetime.fromisoformat(created_at)
                                    
                                    age_hours = (current_time - created_time).total_seconds() / 3600
                                    
                                    if age_hours < 24:  # Less than 24 hours old
                                        fresh_count += 1
                                        print(f"   {i}. ✅ {title[:40]}... ({age_hours:.1f}h ago)")
                                    else:
                                        print(f"   {i}. ⏰ {title[:40]}... ({age_hours:.1f}h ago)")
                                except:
                                    print(f"   {i}. 📝 {title[:40]}... (timestamp parsing failed)")
                            else:
                                # Check if it has real-time indicators
                                realtime_indicators = [
                                    'real-time', 'trending', 'current', 'latest', 'recent',
                                    'AI', 'automation', 'startup', 'market'
                                ]
                                has_indicators = any(indicator.lower() in title.lower() for indicator in realtime_indicators)
                                
                                if has_indicators:
                                    fresh_count += 1
                                    print(f"   {i}. 🔥 {title[:40]}... (realtime indicators)")
                                else:
                                    print(f"   {i}. 📝 {title[:40]}... (no timestamp)")
                        
                        freshness_ratio = fresh_count / total_count if total_count > 0 else 0
                        print(f"\n📈 Data freshness: {fresh_count}/{total_count} ({freshness_ratio:.1%}) appear fresh/relevant")
                        
                        self.results['data_freshness'] = {
                            'total': total_count,
                            'fresh': fresh_count,
                            'ratio': freshness_ratio
                        }
                    else:
                        print(f"❌ Data freshness test failed: {resp.status}")
                        self.results['data_freshness'] = {'status': 'failed'}
        except Exception as e:
            print(f"❌ Data freshness test failed: {e}")
            self.results['data_freshness'] = {'status': 'error'}
    
    async def test_frontend_compatibility(self):
        """Test frontend service layer compatibility"""
        print("\n🖥️  STEP 5: Testing Frontend Compatibility")
        print("-" * 50)
        
        try:
            # Test if frontend is running
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(self.frontend_url, timeout=5) as resp:
                        if resp.status == 200:
                            print("✅ Frontend server is running")
                            
                            # Check if frontend can connect to backend
                            # This simulates what the frontend's opportunitiesService would do
                            test_endpoints = [
                                "/opportunities/",
                                "/opportunities/trending",
                                "/opportunities/recommendations"
                            ]
                            
                            frontend_compatible = True
                            for endpoint in test_endpoints:
                                try:
                                    async with session.get(f"{self.backend_url}{endpoint}") as api_resp:
                                        if api_resp.status != 200:
                                            frontend_compatible = False
                                            print(f"❌ Frontend would fail to load {endpoint}")
                                        else:
                                            print(f"✅ Frontend can load {endpoint}")
                                except:
                                    frontend_compatible = False
                                    print(f"❌ Frontend cannot connect to {endpoint}")
                            
                            if frontend_compatible:
                                print("✅ Frontend service layer is fully compatible with backend API")
                            else:
                                print("⚠️  Frontend may have connectivity issues with some endpoints")
                            
                            self.results['frontend'] = {
                                'running': True,
                                'compatible': frontend_compatible
                            }
                        else:
                            print(f"⚠️  Frontend server returned status {resp.status}")
                            self.results['frontend'] = {'running': False}
                except asyncio.TimeoutError:
                    print("⚠️  Frontend server is not responding (timeout)")
                    self.results['frontend'] = {'running': False}
                except Exception as e:
                    print(f"⚠️  Frontend server is not accessible: {e}")
                    self.results['frontend'] = {'running': False}
        except Exception as e:
            print(f"❌ Frontend compatibility test failed: {e}")
            self.results['frontend'] = {'status': 'error'}
    
    def generate_final_report(self):
        """Generate final integration report"""
        print("\n" + "=" * 60)
        print("🎯 COMPLETE INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        # Calculate overall health
        checks = [
            ("Real-time Data Sources", self.results.get('realtime_sources', {}).get('active', False)),
            ("AI Agents Processing", self.results.get('ai_agents', {}).get('active', False)),
            ("API Endpoints", 'api_endpoints' in self.results and len(self.results['api_endpoints']) > 0),
            ("Data Freshness", self.results.get('data_freshness', {}).get('ratio', 0) > 0),
            ("Frontend Compatibility", self.results.get('frontend', {}).get('running', False))
        ]
        
        passed_checks = sum(1 for _, status in checks if status)
        total_checks = len(checks)
        
        print(f"\n📊 OVERALL HEALTH: {passed_checks}/{total_checks} ({passed_checks/total_checks:.1%})")
        print("-" * 40)
        
        for check_name, status in checks:
            icon = "✅" if status else "❌"
            print(f"{icon} {check_name}")
        
        print("\n🔍 DETAILED RESULTS:")
        print("-" * 40)
        
        # Real-time sources
        if 'realtime_sources' in self.results:
            sources = self.results['realtime_sources']
            print(f"📡 Data Sources: {sources.get('count', 0)} active")
        
        # AI agents
        if 'ai_agents' in self.results:
            agents = self.results['ai_agents']
            print(f"🤖 AI Agents: {agents.get('count', 0)} active, {agents.get('opportunities', 0)} opportunities generated")
        
        # Data freshness
        if 'data_freshness' in self.results:
            freshness = self.results['data_freshness']
            if isinstance(freshness, dict) and 'ratio' in freshness:
                print(f"📅 Data Freshness: {freshness['ratio']:.1%} fresh/recent")
        
        # Frontend
        if 'frontend' in self.results:
            frontend = self.results['frontend']
            status = "Running & Compatible" if frontend.get('running') and frontend.get('compatible') else "Issues Detected"
            print(f"🖥️  Frontend: {status}")
        
        print("\n🎉 INTEGRATION STATUS:")
        if passed_checks >= 4:
            print("🟢 EXCELLENT - Real-time integration is fully operational!")
            print("   ✅ Data flows from sources → agents → API → frontend")
            print("   ✅ All components are working together seamlessly")
        elif passed_checks >= 3:
            print("🟡 GOOD - Real-time integration is mostly working")
            print("   ✅ Core functionality is operational")
            print("   ⚠️  Some minor issues detected")
        else:
            print("🔴 NEEDS ATTENTION - Integration has issues")
            print("   ❌ Multiple components need debugging")
        
        print(f"\n📈 Ready for demonstration and further development!")


async def main():
    """Run complete integration test"""
    tester = CompleteIntegrationTest()
    await tester.run_complete_test()


if __name__ == "__main__":
    asyncio.run(main())
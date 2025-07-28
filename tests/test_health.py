"""Tests for health check functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from shared.health import HealthChecker


class TestHealthChecker:
    """Test health checker functionality."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker instance."""
        return HealthChecker()
    
    @pytest.mark.asyncio
    async def test_check_database_healthy(self, health_checker):
        """Test healthy database check."""
        with patch('shared.health.db_manager') as mock_db:
            # Mock successful database session
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_row = Mock()
            mock_row.health_check = 1
            mock_result.fetchone.return_value = mock_row
            mock_session.execute.return_value = mock_result
            
            # Mock table count query
            mock_table_result = Mock()
            mock_table_row = Mock()
            mock_table_row.table_count = 5
            mock_table_result.fetchone.return_value = mock_table_row
            mock_session.execute.side_effect = [mock_result, mock_table_result]
            
            mock_db.async_session.return_value.__aenter__.return_value = mock_session
            
            # Mock engine pool stats
            mock_pool = Mock()
            mock_pool.size.return_value = 20
            mock_pool.checkedin.return_value = 5
            mock_pool.checkedout.return_value = 3
            mock_pool.overflow.return_value = 0
            mock_db.engine.pool = mock_pool
            
            result = await health_checker.check_database()
            
            assert result["status"] == "healthy"
            assert result["message"] == "Database connection successful"
            assert "response_time_ms" in result
            assert result["table_count"] == 5
            assert "connection_pool" in result
    
    @pytest.mark.asyncio
    async def test_check_database_unhealthy(self, health_checker):
        """Test unhealthy database check."""
        with patch('shared.health.db_manager') as mock_db:
            # Mock database connection failure
            mock_db.async_session.side_effect = Exception("Connection failed")
            
            result = await health_checker.check_database()
            
            assert result["status"] == "unhealthy"
            assert result["message"] == "Database connection failed"
            assert result["error"] == "Connection failed"
            assert "response_time_ms" in result
    
    @pytest.mark.asyncio
    async def test_check_redis_healthy(self, health_checker):
        """Test healthy Redis check."""
        with patch('shared.health.cache_manager') as mock_cache:
            mock_cache.health_check.return_value = {
                "status": "healthy",
                "message": "Redis cache is working correctly"
            }
            
            result = await health_checker.check_redis()
            
            assert result["status"] == "healthy"
            assert result["message"] == "Redis cache is working correctly"
    
    @pytest.mark.asyncio
    async def test_check_redis_unhealthy(self, health_checker):
        """Test unhealthy Redis check."""
        with patch('shared.health.cache_manager') as mock_cache:
            mock_cache.health_check.side_effect = Exception("Redis connection failed")
            
            result = await health_checker.check_redis()
            
            assert result["status"] == "unhealthy"
            assert result["message"] == "Redis health check failed"
            assert "Redis connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_check_vector_database_healthy(self, health_checker):
        """Test healthy vector database check."""
        with patch('shared.health.vector_db_manager') as mock_vector_db:
            mock_vector_db.health_check.return_value = {
                "status": "healthy",
                "message": "Vector database is working correctly",
                "indexes": ["opportunities", "market-signals", "user-preferences"]
            }
            
            result = await health_checker.check_vector_database()
            
            assert result["status"] == "healthy"
            assert result["message"] == "Vector database is working correctly"
            assert "indexes" in result
    
    @pytest.mark.asyncio
    async def test_check_vector_database_unhealthy(self, health_checker):
        """Test unhealthy vector database check."""
        with patch('shared.health.vector_db_manager') as mock_vector_db:
            mock_vector_db.health_check.side_effect = Exception("Pinecone connection failed")
            
            result = await health_checker.check_vector_database()
            
            assert result["status"] == "unhealthy"
            assert result["message"] == "Vector database health check failed"
            assert "Pinecone connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_check_system_resources_healthy(self, health_checker):
        """Test healthy system resources check."""
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            # Mock memory stats
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 60.0
            mock_memory_obj.available = 4 * 1024**3  # 4GB
            mock_memory.return_value = mock_memory_obj
            
            # Mock disk stats
            mock_disk_obj = Mock()
            mock_disk_obj.used = 50 * 1024**3  # 50GB
            mock_disk_obj.total = 100 * 1024**3  # 100GB
            mock_disk_obj.free = 50 * 1024**3  # 50GB
            mock_disk.return_value = mock_disk_obj
            
            result = await health_checker.check_system_resources()
            
            assert result["status"] == "healthy"
            assert result["cpu_percent"] == 50.0
            assert result["memory_percent"] == 60.0
            assert result["disk_percent"] == 50.0
            assert len(result["warnings"]) == 0
    
    @pytest.mark.asyncio
    async def test_check_system_resources_degraded(self, health_checker):
        """Test degraded system resources check."""
        with patch('psutil.cpu_percent', return_value=85.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            # Mock high memory usage
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 90.0
            mock_memory_obj.available = 1 * 1024**3  # 1GB
            mock_memory.return_value = mock_memory_obj
            
            # Mock high disk usage
            mock_disk_obj = Mock()
            mock_disk_obj.used = 95 * 1024**3  # 95GB
            mock_disk_obj.total = 100 * 1024**3  # 100GB
            mock_disk_obj.free = 5 * 1024**3  # 5GB
            mock_disk.return_value = mock_disk_obj
            
            result = await health_checker.check_system_resources()
            
            assert result["status"] == "degraded"
            assert len(result["warnings"]) == 3  # CPU, memory, and disk warnings
            assert "High CPU usage: 85.0%" in result["warnings"]
            assert "High memory usage: 90.0%" in result["warnings"]
            assert "High disk usage: 95.0%" in result["warnings"]
    
    @pytest.mark.asyncio
    async def test_check_ai_providers_not_implemented(self, health_checker):
        """Test AI providers check (not yet implemented)."""
        result = await health_checker.check_ai_providers()
        
        assert result["status"] == "not_implemented"
        assert result["message"] == "AI provider health checks not yet implemented"
        assert "providers" in result
        assert result["providers"]["openai"] == "not_checked"
    
    @pytest.mark.asyncio
    async def test_get_overall_health_all_healthy(self, health_checker):
        """Test overall health when all services are healthy."""
        with patch.object(health_checker, 'check_database') as mock_db, \
             patch.object(health_checker, 'check_redis') as mock_redis, \
             patch.object(health_checker, 'check_vector_database') as mock_vector:
            
            mock_db.return_value = {"status": "healthy", "message": "DB OK"}
            mock_redis.return_value = {"status": "healthy", "message": "Redis OK"}
            mock_vector.return_value = {"status": "healthy", "message": "Vector DB OK"}
            
            result = await health_checker.get_overall_health()
            
            assert result["status"] == "healthy"
            assert "All implemented services healthy" in result["message"]
            assert len(result["services"]) == 3
            assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_get_overall_health_some_unhealthy(self, health_checker):
        """Test overall health when some services are unhealthy."""
        with patch.object(health_checker, 'check_database') as mock_db, \
             patch.object(health_checker, 'check_redis') as mock_redis, \
             patch.object(health_checker, 'check_vector_database') as mock_vector:
            
            mock_db.return_value = {"status": "unhealthy", "message": "DB failed"}
            mock_redis.return_value = {"status": "healthy", "message": "Redis OK"}
            mock_vector.return_value = {"status": "healthy", "message": "Vector DB OK"}
            
            result = await health_checker.get_overall_health()
            
            assert result["status"] == "unhealthy"
            assert "Services unhealthy: database" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_detailed_health(self, health_checker):
        """Test detailed health check with all metrics."""
        with patch.object(health_checker, 'check_database') as mock_db, \
             patch.object(health_checker, 'check_redis') as mock_redis, \
             patch.object(health_checker, 'check_vector_database') as mock_vector, \
             patch.object(health_checker, 'check_system_resources') as mock_system, \
             patch.object(health_checker, 'check_ai_providers') as mock_ai, \
             patch('psutil.boot_time', return_value=1000000):
            
            mock_db.return_value = {"status": "healthy", "message": "DB OK"}
            mock_redis.return_value = {"status": "healthy", "message": "Redis OK"}
            mock_vector.return_value = {"status": "healthy", "message": "Vector DB OK"}
            mock_system.return_value = {"status": "healthy", "message": "System OK"}
            mock_ai.return_value = {"status": "not_implemented", "message": "AI not implemented"}
            
            result = await health_checker.get_detailed_health()
            
            assert result["status"] == "healthy"
            assert len(result["services"]) == 5
            assert "health_check_duration_ms" in result
            assert "timestamp" in result
            assert "uptime_seconds" in result
            assert result["services"]["database"]["status"] == "healthy"
            assert result["services"]["redis"]["status"] == "healthy"
            assert result["services"]["vector_database"]["status"] == "healthy"
            assert result["services"]["system_resources"]["status"] == "healthy"
            assert result["services"]["ai_providers"]["status"] == "not_implemented"
    
    @pytest.mark.asyncio
    async def test_get_detailed_health_with_degraded_services(self, health_checker):
        """Test detailed health check with degraded services."""
        with patch.object(health_checker, 'check_database') as mock_db, \
             patch.object(health_checker, 'check_redis') as mock_redis, \
             patch.object(health_checker, 'check_vector_database') as mock_vector, \
             patch.object(health_checker, 'check_system_resources') as mock_system, \
             patch.object(health_checker, 'check_ai_providers') as mock_ai:
            
            mock_db.return_value = {"status": "healthy", "message": "DB OK"}
            mock_redis.return_value = {"status": "healthy", "message": "Redis OK"}
            mock_vector.return_value = {"status": "healthy", "message": "Vector DB OK"}
            mock_system.return_value = {"status": "degraded", "message": "High CPU usage"}
            mock_ai.return_value = {"status": "not_implemented", "message": "AI not implemented"}
            
            result = await health_checker.get_detailed_health()
            
            assert result["status"] == "degraded"
            assert "Services degraded: system_resources" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_detailed_health_with_critical_failures(self, health_checker):
        """Test detailed health check with critical service failures."""
        with patch.object(health_checker, 'check_database') as mock_db, \
             patch.object(health_checker, 'check_redis') as mock_redis, \
             patch.object(health_checker, 'check_vector_database') as mock_vector, \
             patch.object(health_checker, 'check_system_resources') as mock_system, \
             patch.object(health_checker, 'check_ai_providers') as mock_ai:
            
            mock_db.return_value = {"status": "unhealthy", "message": "DB failed"}
            mock_redis.return_value = {"status": "unhealthy", "message": "Redis failed"}
            mock_vector.return_value = {"status": "healthy", "message": "Vector DB OK"}
            mock_system.return_value = {"status": "healthy", "message": "System OK"}
            mock_ai.return_value = {"status": "not_implemented", "message": "AI not implemented"}
            
            result = await health_checker.get_detailed_health()
            
            assert result["status"] == "unhealthy"
            assert "Critical services unhealthy: database, redis" in result["message"]
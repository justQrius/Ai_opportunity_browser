"""Health check utilities for database and services.

Implements the design document's monitoring and error handling strategies:
- Real-time alerts for source availability
- Performance monitoring and alerting
- Health checks and automatic restart mechanisms
"""

import asyncio
import time
import psutil
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from .database import db_manager
from .monitoring import HealthCheck, HealthStatus, get_health_monitor, get_metrics_collector
import structlog

logger = structlog.get_logger(__name__)


class HealthChecker:
    """Health check service for monitoring system components."""
    
    async def check_database(self) -> Dict[str, Any]:
        """Check PostgreSQL database connectivity with performance metrics."""
        start_time = time.time()
        
        try:
            async with db_manager.async_session() as session:
                # Basic connectivity test
                result = await session.execute(text("SELECT 1 as health_check"))
                row = result.fetchone()
                
                # Performance test - check table count
                table_count_result = await session.execute(text("""
                    SELECT COUNT(*) as table_count 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                table_count = table_count_result.fetchone().table_count
                
                # Connection pool stats
                pool_info = {
                    "pool_size": db_manager.engine.pool.size(),
                    "checked_in": db_manager.engine.pool.checkedin(),
                    "checked_out": db_manager.engine.pool.checkedout(),
                    "overflow": db_manager.engine.pool.overflow(),
                }
                
                response_time = round((time.time() - start_time) * 1000, 2)
                
                if row and row.health_check == 1:
                    return {
                        "status": "healthy",
                        "message": "Database connection successful",
                        "response_time_ms": response_time,
                        "table_count": table_count,
                        "connection_pool": pool_info,
                        "performance": "good" if response_time < 100 else "slow"
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "message": "Database query returned unexpected result",
                        "error": f"Expected 1, got {row.health_check if row else None}",
                        "response_time_ms": response_time
                    }
                    
        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            logger.error("Database health check failed", error=str(e), exc_info=True)
            return {
                "status": "unhealthy",
                "message": "Database connection failed",
                "error": str(e),
                "response_time_ms": response_time
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            from .cache import cache_manager
            return await cache_manager.health_check()
        except Exception as e:
            logger.error("Redis health check failed", error=str(e), exc_info=True)
            return {
                "status": "unhealthy",
                "message": "Redis health check failed",
                "error": str(e)
            }
    
    async def check_vector_database(self) -> Dict[str, Any]:
        """Check vector database connectivity."""
        try:
            from .vector_db import vector_db_manager
            return await vector_db_manager.health_check()
        except Exception as e:
            logger.error("Vector database health check failed", error=str(e), exc_info=True)
            return {
                "status": "unhealthy",
                "message": "Vector database health check failed",
                "error": str(e)
            }
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource utilization."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = round(memory.available / (1024**3), 2)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = round((disk.used / disk.total) * 100, 2)
            disk_free_gb = round(disk.free / (1024**3), 2)
            
            # Determine status based on thresholds
            status = "healthy"
            warnings = []
            
            if cpu_percent > 80:
                status = "degraded"
                warnings.append(f"High CPU usage: {cpu_percent}%")
            
            if memory_percent > 85:
                status = "degraded"
                warnings.append(f"High memory usage: {memory_percent}%")
            
            if disk_percent > 90:
                status = "degraded"
                warnings.append(f"High disk usage: {disk_percent}%")
            
            return {
                "status": status,
                "message": "System resources checked" if status == "healthy" else f"Resource warnings: {', '.join(warnings)}",
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_available_gb": memory_available_gb,
                "disk_percent": disk_percent,
                "disk_free_gb": disk_free_gb,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.error("System resource check failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": "Failed to check system resources",
                "error": str(e)
            }
    
    async def check_ai_providers(self) -> Dict[str, Any]:
        """Check AI provider connectivity (placeholder for future implementation)."""
        # TODO: Implement when AI provider clients are set up
        return {
            "status": "not_implemented",
            "message": "AI provider health checks not yet implemented",
            "providers": {
                "openai": "not_checked",
                "anthropic": "not_checked", 
                "google": "not_checked",
                "cohere": "not_checked"
            }
        }
    
    async def get_detailed_health(self) -> Dict[str, Any]:
        """Get comprehensive system health with detailed metrics."""
        start_time = time.time()
        
        # Run all health checks concurrently
        checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_vector_database(),
            self.check_system_resources(),
            self.check_ai_providers(),
            return_exceptions=True
        )
        
        # Map results to service names
        service_checks = {
            "database": checks[0] if not isinstance(checks[0], Exception) else {"status": "error", "error": str(checks[0])},
            "redis": checks[1] if not isinstance(checks[1], Exception) else {"status": "error", "error": str(checks[1])},
            "vector_database": checks[2] if not isinstance(checks[2], Exception) else {"status": "error", "error": str(checks[2])},
            "system_resources": checks[3] if not isinstance(checks[3], Exception) else {"status": "error", "error": str(checks[3])},
            "ai_providers": checks[4] if not isinstance(checks[4], Exception) else {"status": "error", "error": str(checks[4])}
        }
        
        # Calculate overall status
        critical_services = ["database", "redis", "vector_database"]
        unhealthy_critical = [
            service for service in critical_services 
            if service_checks[service]["status"] == "unhealthy"
        ]
        
        degraded_services = [
            service for service, status in service_checks.items()
            if status["status"] == "degraded"
        ]
        
        if unhealthy_critical:
            overall_status = "unhealthy"
            message = f"Critical services unhealthy: {', '.join(unhealthy_critical)}"
        elif degraded_services:
            overall_status = "degraded"
            message = f"Services degraded: {', '.join(degraded_services)}"
        else:
            healthy_services = [
                service for service, status in service_checks.items()
                if status["status"] == "healthy"
            ]
            overall_status = "healthy"
            message = f"All services operational ({len(healthy_services)} healthy)"
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "status": overall_status,
            "message": message,
            "services": service_checks,
            "health_check_duration_ms": total_time,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - psutil.boot_time()
        }
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get basic system health status (lightweight version)."""
        checks = {
            "database": await self.check_database(),
            "redis": await self.check_redis(),
            "vector_database": await self.check_vector_database(),
        }
        
        # Determine overall status
        unhealthy_services = [
            service for service, status in checks.items() 
            if status["status"] == "unhealthy"
        ]
        
        if unhealthy_services:
            overall_status = "unhealthy"
            message = f"Services unhealthy: {', '.join(unhealthy_services)}"
        else:
            healthy_services = [
                service for service, status in checks.items()
                if status["status"] == "healthy"
            ]
            if healthy_services:
                overall_status = "healthy"
                message = f"All implemented services healthy ({len(healthy_services)} services)"
            else:
                overall_status = "degraded"
                message = "No services fully implemented yet"
        
        return {
            "status": overall_status,
            "message": message,
            "services": checks,
            "timestamp": datetime.utcnow().isoformat()
        }


# Global health checker instance
health_checker = HealthChecker()

# Register health checks with the monitoring system
async def _register_health_checks():
    """Register all health checks with the monitoring system."""
    monitor = get_health_monitor()
    
    async def database_check() -> HealthCheck:
        result = await health_checker.check_database()
        status = HealthStatus.HEALTHY if result["status"] == "healthy" else HealthStatus.UNHEALTHY
        return HealthCheck(
            name="database",
            status=status,
            message=result["message"],
            details=result
        )
    
    async def redis_check() -> HealthCheck:
        result = await health_checker.check_redis()
        status = HealthStatus.HEALTHY if result["status"] == "healthy" else HealthStatus.UNHEALTHY
        return HealthCheck(
            name="redis",
            status=status,
            message=result["message"],
            details=result
        )
    
    async def vector_db_check() -> HealthCheck:
        result = await health_checker.check_vector_database()
        status = HealthStatus.HEALTHY if result["status"] == "healthy" else HealthStatus.UNHEALTHY
        return HealthCheck(
            name="vector_database",
            status=status,
            message=result["message"],
            details=result
        )
    
    async def system_resources_check() -> HealthCheck:
        result = await health_checker.check_system_resources()
        if result["status"] == "healthy":
            status = HealthStatus.HEALTHY
        elif result["status"] == "degraded":
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
        
        return HealthCheck(
            name="system_resources",
            status=status,
            message=result["message"],
            details=result
        )
    
    # Register checks
    monitor.register_check("database", database_check)
    monitor.register_check("redis", redis_check)
    monitor.register_check("vector_database", vector_db_check)
    monitor.register_check("system_resources", system_resources_check)
    
    logger.info("Health checks registered with monitoring system")

# Initialize health checks registration
import asyncio
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(_register_health_checks())
    else:
        loop.run_until_complete(_register_health_checks())
except RuntimeError:
    # No event loop running, will be registered when the app starts
    pass
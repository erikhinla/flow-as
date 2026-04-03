"""
Redis Queue Integration for FLOW Agent OS

Manages hot-state queues for job distribution.

Queues:
- openclaw:jobs → pending jobs for OpenClaw router
- hermes:jobs → pending jobs for Hermes worker
- agent_zero:jobs → pending jobs for Agent Zero executor

All operations are async/await compatible.
"""

import logging
from typing import Optional, List, Dict, Any
import json

import aioredis
from aioredis import Redis

logger = logging.getLogger(__name__)


class RedisQueueService:
    """
    Manage Redis queues for job distribution.
    
    Each agent has its own FIFO queue:
    - Push jobs with lpush (left push, for FIFO)
    - Pop jobs with brpop (blocking right pop)
    """
    
    # Queue naming convention
    QUEUE_PREFIX = "flow"
    
    # Owner queue names
    OPENCLAW_QUEUE = f"{QUEUE_PREFIX}:openclaw:jobs"
    HERMES_QUEUE = f"{QUEUE_PREFIX}:hermes:jobs"
    AGENT_ZERO_QUEUE = f"{QUEUE_PREFIX}:agent_zero:jobs"
    
    ALL_QUEUES = [OPENCLAW_QUEUE, HERMES_QUEUE, AGENT_ZERO_QUEUE]
    
    # DLQ (dead-letter queue) for failed jobs
    DLQ_QUEUE = f"{QUEUE_PREFIX}:dead_letter"
    
    def __init__(self, redis_client: Redis):
        """Initialize with Redis client"""
        self.redis = redis_client
    
    @staticmethod
    def get_queue_name(owner: str) -> str:
        """Get queue name for owner"""
        return f"{RedisQueueService.QUEUE_PREFIX}:{owner}:jobs"
    
    async def enqueue_job(self, owner: str, job_id: str) -> bool:
        """
        Add job to owner's queue (FIFO).
        
        Args:
            owner: openclaw, hermes, or agent_zero
            job_id: unique job identifier
        
        Returns:
            True if enqueued, False on error
        """
        
        try:
            queue_name = self.get_queue_name(owner)
            await self.redis.lpush(queue_name, job_id)
            logger.info(f"Enqueued job {job_id} to {queue_name}")
            return True
        except Exception as e:
            logger.error(f"Error enqueuing job {job_id}: {e}")
            return False
    
    async def dequeue_job(self, owner: str, timeout: int = 5) -> Optional[str]:
        """
        Pop job from owner's queue (blocking).
        
        Called by worker to get next job.
        
        Args:
            owner: openclaw, hermes, or agent_zero
            timeout: seconds to wait for job (0 = no wait)
        
        Returns:
            job_id if available, None if timeout
        """
        
        try:
            queue_name = self.get_queue_name(owner)
            result = await self.redis.brpop(queue_name, timeout=timeout)
            
            if result:
                job_id = result[1].decode('utf-8') if isinstance(result[1], bytes) else result[1]
                logger.info(f"Dequeued job {job_id} from {queue_name}")
                return job_id
            else:
                logger.debug(f"No jobs available in {queue_name} after {timeout}s")
                return None
        
        except Exception as e:
            logger.error(f"Error dequeuing from {owner} queue: {e}")
            return None
    
    async def get_queue_depth(self, owner: str) -> int:
        """
        Get number of jobs waiting in owner's queue.
        
        Returns:
            queue length (0 if empty or error)
        """
        
        try:
            queue_name = self.get_queue_name(owner)
            depth = await self.redis.llen(queue_name)
            return depth or 0
        except Exception as e:
            logger.error(f"Error getting queue depth for {owner}: {e}")
            return 0
    
    async def get_all_queue_depths(self) -> Dict[str, int]:
        """
        Get queue depths for all owners.
        
        Returns:
            {owner: depth}
        """
        
        depths = {}
        for owner in ['openclaw', 'hermes', 'agent_zero']:
            depths[owner] = await self.get_queue_depth(owner)
        return depths
    
    async def move_to_dlq(self, job_id: str, reason: str) -> bool:
        """
        Move job to dead-letter queue (for failed/abandoned jobs).
        
        Args:
            job_id: job identifier
            reason: why job was sent to DLQ
        
        Returns:
            True if moved, False on error
        """
        
        try:
            dlq_entry = json.dumps({
                'job_id': job_id,
                'reason': reason,
                'timestamp': datetime.utcnow().isoformat()
            })
            await self.redis.lpush(self.DLQ_QUEUE, dlq_entry)
            logger.warning(f"Moved job {job_id} to DLQ: {reason}")
            return True
        except Exception as e:
            logger.error(f"Error moving job to DLQ: {e}")
            return False
    
    async def get_dlq(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent jobs from dead-letter queue.
        
        Args:
            count: how many to retrieve
        
        Returns:
            List of {job_id, reason, timestamp}
        """
        
        try:
            items = await self.redis.lrange(self.DLQ_QUEUE, 0, count - 1)
            dlq_items = []
            
            for item in items:
                try:
                    dlq_item = json.loads(item.decode('utf-8') if isinstance(item, bytes) else item)
                    dlq_items.append(dlq_item)
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse DLQ item: {item}")
            
            return dlq_items
        except Exception as e:
            logger.error(f"Error retrieving DLQ: {e}")
            return []
    
    async def clear_queue(self, owner: str) -> bool:
        """
        Clear all jobs from owner's queue (DANGEROUS - use carefully).
        
        Args:
            owner: openclaw, hermes, or agent_zero
        
        Returns:
            True if cleared, False on error
        """
        
        try:
            queue_name = self.get_queue_name(owner)
            await self.redis.delete(queue_name)
            logger.warning(f"Cleared queue {queue_name}")
            return True
        except Exception as e:
            logger.error(f"Error clearing queue {owner}: {e}")
            return False
    
    async def healthcheck(self) -> bool:
        """
        Check Redis connectivity.
        
        Returns:
            True if Redis is reachable
        """
        
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis healthcheck failed: {e}")
            return False


async def get_redis_client(redis_url: str = "redis://localhost:6379") -> Redis:
    """
    Create Redis connection.
    
    Args:
        redis_url: Redis connection string
    
    Returns:
        Redis client
    """
    
    try:
        redis = await aioredis.from_url(redis_url)
        logger.info(f"Connected to Redis at {redis_url}")
        return redis
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def create_queue_service(redis_url: str = "redis://localhost:6379") -> RedisQueueService:
    """
    Factory function to create queue service.
    
    Args:
        redis_url: Redis connection string
    
    Returns:
        RedisQueueService instance
    """
    
    redis = await get_redis_client(redis_url)
    return RedisQueueService(redis)

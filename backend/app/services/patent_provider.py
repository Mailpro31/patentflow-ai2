import httpx
from typing import Optional, List
from bs4 import BeautifulSoup
import logging
from datetime import datetime
from app.config import settings
from app.services.cache_service import cache_service
from app.schemas.espacenet import EspacenetPatentMetadata, EspacenetSearchResult

logger = logging.getLogger(__name__)


class PatentProvider:
    """
    Service for fetching patent metadata from Espacenet API.
    Simulates calls to Espacenet OPS API with Redis caching.
    Can be configured to use Bright Data proxy for rate limiting.
    """
    
    def __init__(self):
        self.api_url = settings.ESPACENET_API_URL
        self.proxy = settings.BRIGHT_DATA_PROXY if settings.BRIGHT_DATA_PROXY else None
        self.cache_ttl = settings.REDIS_CACHE_TTL
        
    def _get_cache_key(self, patent_number: str) -> str:
        """Generate cache key for patent metadata."""
        return f"patent:metadata:{patent_number}"
    
    def _get_search_cache_key(self, query: str, limit: int) -> str:
        """Generate cache key for search results."""
        return f"patent:search:{query}:{limit}"
    
    async def fetch_patent_metadata(self, patent_number: str) -> Optional[EspacenetPatentMetadata]:
        """
        Fetch patent metadata from Espacenet.
        Checks Redis cache first, then calls API if needed.
        
        Args:
            patent_number: Patent number (e.g., "EP1234567")
            
        Returns:
            EspacenetPatentMetadata or None if not found
        """
        # Check cache first
        cache_key = self._get_cache_key(patent_number)
        cached_data = await cache_service.get(cache_key)
        
        if cached_data:
            logger.info(f"Cache hit for patent {patent_number}")
            return EspacenetPatentMetadata(**cached_data)
        
        # Cache miss - fetch from API
        logger.info(f"Cache miss for patent {patent_number}, fetching from Espacenet")
        
        try:
            metadata = await self._fetch_from_api(patent_number)
            
            if metadata:
                # Store in cache
                await cache_service.set(
                    cache_key,
                    metadata.model_dump(),
                    ttl=self.cache_ttl
                )
                logger.info(f"Cached metadata for patent {patent_number}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to fetch patent {patent_number}: {e}")
            return None
    
    async def _fetch_from_api(self, patent_number: str) -> Optional[EspacenetPatentMetadata]:
        """
        Fetch patent data from Espacenet API.
        This is a SIMULATION - in production, use real Espacenet OPS API.
        """
        # SIMULATION: Generate mock data for demonstration
        # In production, replace with actual API calls
        
        # For demo purposes, create synthetic data
        metadata = self._generate_mock_patent(patent_number)
        
        # Uncomment below for real API implementation:
        # metadata = await self._fetch_from_real_api(patent_number)
        
        return metadata
    
    def _generate_mock_patent(self, patent_number: str) -> EspacenetPatentMetadata:
        """
        Generate mock patent data for simulation.
        Replace this with real API calls in production.
        """
        # Extract parts from patent number for variation
        num_suffix = sum(ord(c) for c in patent_number) % 10
        
        mock_titles = [
            "Lithium-ion battery with improved energy density",
            "Solar panel manufacturing process optimization",
            "Artificial intelligence model training method",
            "Wireless charging system for electric vehicles",
            "Biodegradable plastic composition",
            "Quantum computing error correction technique",
            "Medical imaging device with enhanced resolution",
            "Water purification membrane technology",
            "Wind turbine blade design optimization",
            "Pharmaceutical compound for cancer treatment"
        ]
        
        mock_abstracts = [
            "The present invention relates to an improved battery technology with enhanced performance characteristics.",
            "A novel method for manufacturing solar panels with increased efficiency and reduced costs.",
            "An innovative approach to training machine learning models using novel optimization techniques.",
            "A wireless charging system designed specifically for electric vehicle applications.",
            "A biodegradable plastic material with improved strength and environmental characteristics.",
            "A quantum error correction method that significantly improves qubit stability.",
            "An advanced medical imaging device providing superior image quality for diagnosis.",
            "A water purification membrane with enhanced filtration capabilities.",
            "An optimized wind turbine blade design for improved energy capture.",
            "A pharmaceutical composition with novel therapeutic properties for oncology."
        ]
        
        return EspacenetPatentMetadata(
            patent_number=patent_number,
            title=mock_titles[num_suffix],
            abstract=mock_abstracts[num_suffix],
            filing_date=datetime(2020 + num_suffix % 5, (num_suffix % 12) + 1, (num_suffix % 28) + 1),
            publication_date=datetime(2021 + num_suffix % 5, (num_suffix % 12) + 1, (num_suffix % 28) + 1),
            applicants=[f"Company {chr(65 + num_suffix)}", f"Research Institute {num_suffix}"],
            inventors=[f"Dr. John Smith {num_suffix}", f"Dr. Jane Doe {num_suffix}"],
            ipc_classes=[f"H01M {num_suffix}/00", f"G06F {num_suffix}/00"]
        )
    
    async def _fetch_from_real_api(self, patent_number: str) -> Optional[EspacenetPatentMetadata]:
        """
        Fetch from real Espacenet OPS API.
        Uncomment and implement for production use.
        """
        try:
            # Configure proxy if available
            proxies = {"http://": self.proxy, "https://": self.proxy} if self.proxy else None
            
            async with httpx.AsyncClient(proxies=proxies, timeout=30.0) as client:
                # Espacenet OPS API endpoint
                url = f"{self.api_url}/published-data/publication/epodoc/{patent_number}/biblio"
                
                # Add authentication headers if needed
                headers = {
                    "Accept": "application/json",
                    # Add API key if required: "Authorization": "Bearer YOUR_API_KEY"
                }
                
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Parse response and create metadata object
                    # This is a simplified parser - adjust based on actual API response
                    metadata = EspacenetPatentMetadata(
                        patent_number=patent_number,
                        title=data.get("title", ""),
                        abstract=data.get("abstract", ""),
                        filing_date=self._parse_date(data.get("filing_date")),
                        publication_date=self._parse_date(data.get("publication_date")),
                        applicants=data.get("applicants", []),
                        inventors=data.get("inventors", []),
                        ipc_classes=data.get("ipc_classes", [])
                    )
                    
                    return metadata
                elif response.status_code == 404:
                    logger.warning(f"Patent {patent_number} not found")
                    return None
                else:
                    logger.error(f"API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching from Espacenet API: {e}")
            return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string from API response."""
        if not date_str:
            return None
        
        try:
            # Adjust format based on actual API response
            return datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return None
    
    async def search_espacenet(
        self,
        query: str,
        limit: int = 10
    ) -> List[EspacenetSearchResult]:
        """
        Search Espacenet for patents matching query.
        Returns list of patent numbers with basic info.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of EspacenetSearchResult
        """
        # Check cache
        cache_key = self._get_search_cache_key(query, limit)
        cached_results = await cache_service.get(cache_key)
        
        if cached_results:
            logger.info(f"Cache hit for search query: {query}")
            return [EspacenetSearchResult(**r) for r in cached_results]
        
        # Cache miss - perform search
        logger.info(f"Performing search for: {query}")
        
        # SIMULATION: Generate mock search results
        results = self._generate_mock_search_results(query, limit)
        
        # Cache results
        results_dict = [r.model_dump() for r in results]
        await cache_service.set(cache_key, results_dict, ttl=3600)  # 1 hour cache for searches
        
        return results
    
    def _generate_mock_search_results(self, query: str, limit: int) -> List[EspacenetSearchResult]:
        """Generate mock search results for simulation."""
        results = []
        
        for i in range(min(limit, 10)):
            patent_num = f"EP{1000000 + i + len(query) * 100}"
            results.append(
                EspacenetSearchResult(
                    patent_number=patent_num,
                    title=f"Patent related to {query} - {i+1}",
                    abstract=f"This patent describes technology related to {query}",
                    score=1.0 - (i * 0.1)
                )
            )
        
        return results
    
    async def bulk_fetch_patents(
        self,
        patent_numbers: List[str]
    ) -> List[Optional[EspacenetPatentMetadata]]:
        """
        Fetch multiple patents efficiently using cache pipeline.
        
        Args:
            patent_numbers: List of patent numbers to fetch
            
        Returns:
            List of metadata objects (None for failed fetches)
        """
        # Get cache keys
        cache_keys = [self._get_cache_key(pn) for pn in patent_numbers]
        
        # Bulk check cache
        cached_data = await cache_service.get_many(cache_keys)
        
        results = []
        to_fetch = []
        
        for i, data in enumerate(cached_data):
            if data:
                results.append(EspacenetPatentMetadata(**data))
                logger.debug(f"Cache hit for {patent_numbers[i]}")
            else:
                results.append(None)
                to_fetch.append((i, patent_numbers[i]))
        
        # Fetch missing patents
        for idx, patent_number in to_fetch:
            metadata = await self._fetch_from_api(patent_number)
            results[idx] = metadata
            
            if metadata:
                # Cache individually
                cache_key = self._get_cache_key(patent_number)
                await cache_service.set(cache_key, metadata.model_dump(), ttl=self.cache_ttl)
        
        logger.info(f"Bulk fetch: {len(cached_data) - len(to_fetch)} from cache, {len(to_fetch)} from API")
        
        return results


# Global instance
patent_provider = PatentProvider()

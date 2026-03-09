import re
import logging
from typing import List, Optional
from simhash import Simhash

logger = logging.getLogger(__name__)

class ContentHasher:
    """
    Utility for calculating fuzzy hashes (SimHash) to detect near-duplicate text.
    """
    
    @staticmethod
    def _preprocess(text: str) -> List[str]:
        """
        Tokenizes and cleans text for hashing.
        Optimized: For small text, use 3-char shingles. For large text, use word-based shingles.
        """
        text = text.lower()
        
        # If very large, use word-based approach to avoid millions of features
        if len(text) > 100 * 1024:
            # Word-based shingles
            words = re.findall(r'\w+', text)
            # Use windows of 3 words
            return [" ".join(words[i:i+3]) for i in range(max(len(words)-2, 1))]
        
        # Default: 3-character shingles
        width = 3
        return [text[i:i + width] for i in range(max(len(text) - width + 1, 1))]

    @classmethod
    def calculate_hash(cls, text: str) -> Optional[str]:
        """
        Calculates the SimHash of the provided text.
        Returns the hash as a hex string.
        """
        if not text or len(text) < 10:
            return None
        
        try:
            features = cls._preprocess(text)
            shash = Simhash(features)
            return hex(shash.value)
        except Exception as e:
            logger.error(f"Failed to calculate SimHash: {e}")
            return None

    @staticmethod
    def get_similarity(hash1: str, hash2: str) -> float:
        """
        Calculates the similarity (0.0 to 1.0) between two SimHashes.
        """
        if not hash1 or not hash2:
            return 0.0
        
        try:
            val1 = int(hash1, 16)
            val2 = int(hash2, 16)
            
            shash1 = Simhash(val1)
            shash2 = Simhash(val2)
            
            # distance is Hamming distance (0-64)
            dist = shash1.distance(shash2)
            # Similarity = (64 - distance) / 64
            return (64 - dist) / 64.0
        except Exception as e:
            logger.error(f"Error comparing hashes: {e}")
            return 0.0

    @classmethod
    def is_near_duplicate(cls, hash1: str, hash2: str, threshold: float = 0.9) -> bool:
        """
        Checks if two hashes represent near-duplicate content based on threshold.
        """
        return cls.get_similarity(hash1, hash2) >= threshold

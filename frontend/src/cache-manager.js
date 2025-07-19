// Cache Manager for Post Guardian
// This utility helps monitor and manage the smart caching system

export class CacheManager {
    constructor() {
        this.keywordCache = new Map();
        this.contextCache = new Map();
        this.stats = {
            hits: 0,
            misses: 0,
            apiCalls: 0,
            cacheSize: 0
        };
    }

    // Get cache statistics
    getStats() {
        return {
            ...this.stats,
            keywordCacheSize: this.keywordCache.size,
            contextCacheSize: this.contextCache.size,
            totalCacheSize: this.keywordCache.size + this.contextCache.size
        };
    }

    // Clear all caches
    clearAll() {
        this.keywordCache.clear();
        this.contextCache.clear();
        this.stats = {
            hits: 0,
            misses: 0,
            apiCalls: 0,
            cacheSize: 0
        };
        console.log('All caches cleared');
    }

    // Clear expired entries
    clearExpired() {
        const now = Date.now();
        const maxAge = 3600000; // 1 hour

        // Clear expired keyword cache entries
        let keywordCleared = 0;
        for (const [key, value] of this.keywordCache.entries()) {
            if (now - value.timestamp > maxAge) {
                this.keywordCache.delete(key);
                keywordCleared++;
            }
        }

        // Clear expired context cache entries
        let contextCleared = 0;
        for (const [key, value] of this.contextCache.entries()) {
            if (now - value.timestamp > maxAge) {
                this.contextCache.delete(key);
                contextCleared++;
            }
        }

        console.log(`Cleared ${keywordCleared} expired keyword entries and ${contextCleared} expired context entries`);
    }

    // Get cache hit rate
    getHitRate() {
        const total = this.stats.hits + this.stats.misses;
        return total > 0 ? (this.stats.hits / total * 100).toFixed(2) : 0;
    }

    // Log cache performance
    logPerformance() {
        const stats = this.getStats();
        console.log('📊 Post Guardian Cache Performance:');
        console.log(`  Cache Hit Rate: ${this.getHitRate()}%`);
        console.log(`  API Calls: ${stats.apiCalls}`);
        console.log(`  Cache Hits: ${stats.hits}`);
        console.log(`  Cache Misses: ${stats.misses}`);
        console.log(`  Keyword Cache Size: ${stats.keywordCacheSize}`);
        console.log(`  Context Cache Size: ${stats.contextCacheSize}`);
    }

    // Export cache data for debugging
    exportCache() {
        return {
            keywordCache: Object.fromEntries(this.keywordCache),
            contextCache: Object.fromEntries(this.contextCache),
            stats: this.getStats()
        };
    }
}

// LRU Cache for efficient contextual caching
export class LRUCache {
    constructor(limit = 20) {
        this.limit = limit;
        this.cache = new Map();
        this.stats = {
            hits: 0,
            misses: 0,
            apiCalls: 0
        };
    }
    get(key) {
        if (!this.cache.has(key)) {
            this.stats.misses++;
            return undefined;
        }
        const value = this.cache.get(key);
        // Move to end (most recently used)
        this.cache.delete(key);
        this.cache.set(key, value);
        this.stats.hits++;
        return value;
    }
    set(key, value) {
        if (this.cache.has(key)) this.cache.delete(key);
        else if (this.cache.size >= this.limit) {
            // Remove least recently used
            const lru = this.cache.keys().next().value;
            this.cache.delete(lru);
        }
        this.cache.set(key, value);
    }
    has(key) {
        return this.cache.has(key);
    }
    clear() {
        this.cache.clear();
        this.stats = {
            hits: 0,
            misses: 0,
            apiCalls: 0
        };
    }
    size() {
        return this.cache.size;
    }
    getStats() {
        return { ...this.stats, cacheSize: this.cache.size };
    }
}

// Make cache manager available globally for debugging
if (typeof window !== 'undefined') {
    window.PostGuardianCacheManager = CacheManager;
} 
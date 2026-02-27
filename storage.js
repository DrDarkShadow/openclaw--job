const fs = require('fs');
const path = require('path');

/**
 * Simple JSON-based storage for tracking seen jobs
 * Prevents duplicate notifications
 */
class JobStorage {
  constructor(storageFile) {
    this.storageFile = storageFile || path.join(__dirname, 'seen-jobs.json');
    this.seenJobs = new Map();
    this.load();
  }

  load() {
    try {
      if (fs.existsSync(this.storageFile)) {
        const data = JSON.parse(fs.readFileSync(this.storageFile, 'utf8'));
        // Convert to Map for O(1) lookups
        for (const [key, value] of Object.entries(data)) {
          this.seenJobs.set(key, value);
        }
        console.log(`📦 Loaded ${this.seenJobs.size} previously seen jobs`);
      }
    } catch (error) {
      console.warn('⚠️ Could not load seen jobs:', error.message);
      this.seenJobs = new Map();
    }
  }

  save() {
    try {
      const data = Object.fromEntries(this.seenJobs);
      fs.writeFileSync(this.storageFile, JSON.stringify(data, null, 2));
    } catch (error) {
      console.error('❌ Failed to save seen jobs:', error.message);
    }
  }

  /**
   * Check if job was already seen
   * @param {string} jobId - Unique job identifier
   * @returns {boolean}
   */
  has(jobId) {
    return this.seenJobs.has(jobId);
  }

  /**
   * Add job to seen list
   * @param {string} jobId - Unique job identifier
   * @param {object} metadata - Optional job metadata
   */
  add(jobId, metadata = {}) {
    this.seenJobs.set(jobId, {
      firstSeen: new Date().toISOString(),
      ...metadata
    });
    
    // Save periodically (every 10 new jobs)
    if (this.seenJobs.size % 10 === 0) {
      this.save();
    }
  }

  /**
   * Clean up old entries (older than 30 days)
   */
  cleanup(maxAgeDays = 30) {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - maxAgeDays);
    
    let removed = 0;
    for (const [key, value] of this.seenJobs.entries()) {
      const seenDate = new Date(value.firstSeen);
      if (seenDate < cutoff) {
        this.seenJobs.delete(key);
        removed++;
      }
    }
    
    if (removed > 0) {
      console.log(`🧹 Cleaned up ${removed} old job entries`);
      this.save();
    }
    
    return removed;
  }

  /**
   * Get stats about stored jobs
   */
  stats() {
    return {
      total: this.seenJobs.size,
      bySource: this.getStatsBySource()
    };
  }

  getStatsBySource() {
    const stats = {};
    for (const value of this.seenJobs.values()) {
      const source = value.source || 'unknown';
      stats[source] = (stats[source] || 0) + 1;
    }
    return stats;
  }

  /**
   * Mark all current jobs as seen (useful for initial setup)
   */
  markAllAsSeen(jobs) {
    let added = 0;
    for (const job of jobs) {
      const jobId = this.generateJobId(job);
      if (!this.has(jobId)) {
        this.add(jobId, { source: job.source, title: job.title });
        added++;
      }
    }
    this.save();
    console.log(`📌 Marked ${added} existing jobs as seen (no alerts for these)`);
    return added;
  }

  generateJobId(job) {
    // Create unique ID from source + company + title + location
    const normalized = `${job.source}:${job.company}:${job.title}:${job.location}`
      .toLowerCase()
      .replace(/\s+/g, '_')
      .replace(/[^a-z0-9_:-]/g, '');
    return normalized;
  }
}

module.exports = { JobStorage };

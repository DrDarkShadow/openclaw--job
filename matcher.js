/**
 * Job Matching Engine
 * Filters and scores jobs based on user preferences
 */

class JobMatcher {
  constructor(config) {
    this.config = config;
    this.search = config.search;
    this.filters = config.filters;
  }

  /**
   * Check if job matches user criteria
   * @param {object} job - Job object from scraper
   * @returns {object|null} - Match result with score or null if rejected
   */
  match(job) {
    const checks = [];
    let score = 0;
    let maxScore = 0;

    // Check exclude keywords first (hard filter)
    if (this.search.excludeKeywords?.length > 0) {
      const hasExcluded = this.search.excludeKeywords.some(kw => 
        this.containsIgnoreCase(job.title, kw) ||
        this.containsIgnoreCase(job.description, kw)
      );
      if (hasExcluded) {
        return null;
      }
    }

    // Check search keywords
    maxScore += 30;
    const keywordMatch = this.search.keywords.some(kw =>
      this.containsIgnoreCase(job.title, kw) ||
      this.containsIgnoreCase(job.description, kw)
    );
    if (keywordMatch) {
      score += 30;
      checks.push('keyword match');
    }

    // Check skills
    maxScore += 40;
    if (job.skills?.length > 0) {
      const matchingSkills = this.search.skills.filter(skill =>
        job.skills.some(jobSkill => 
          this.containsIgnoreCase(jobSkill, skill)
        )
      );
      const skillScore = Math.min(40, (matchingSkills.length / this.search.skills.length) * 40);
      score += skillScore;
      if (skillScore > 0) {
        checks.push(`${matchingSkills.length} skills match`);
      }
    } else if (this.search.skills.some(skill =>
      this.containsIgnoreCase(job.description, skill)
    )) {
      score += 20;
      checks.push('skills mentioned');
    }

    // Check location
    maxScore += 15;
    const locationMatch = this.search.locations.some(loc =>
      this.containsIgnoreCase(job.location, loc) ||
      (loc.toLowerCase() === 'remote' && this.isRemoteJob(job))
    );
    if (locationMatch) {
      score += 15;
      checks.push('location match');
    }

    // Check job type
    maxScore += 10;
    if (this.search.jobTypes?.length > 0 && job.jobType) {
      const typeMatch = this.search.jobTypes.some(type =>
        this.containsIgnoreCase(job.jobType, type)
      );
      if (typeMatch) {
        score += 10;
        checks.push('job type match');
      }
    }

    // Check experience level
    if (this.search.experience && job.experience) {
      const jobExp = this.parseExperience(job.experience);
      if (jobExp !== null) {
        const userMin = this.search.experience.min || 0;
        const userMax = this.search.experience.max || 20;
        if (jobExp >= userMin && jobExp <= userMax) {
          score += 5;
          checks.push('experience match');
        }
      }
    }

    // Check salary if available
    if (this.filters.minSalary && job.salary) {
      const jobSalary = this.parseSalary(job.salary);
      if (jobSalary !== null && jobSalary >= this.filters.minSalary) {
        score += 5;
        checks.push('salary meets minimum');
      }
    }

    // Check remote only preference
    if (this.filters.remoteOnly) {
      if (!this.isRemoteJob(job)) {
        return null;
      }
    }

    // Check posted date
    if (this.filters.postedWithinDays && job.postedDate) {
      const daysAgo = this.getDaysAgo(job.postedDate);
      if (daysAgo > this.filters.postedWithinDays) {
        return null; // Too old
      }
    }

    // Check excluded companies
    if (this.filters.excludeCompanies?.length > 0) {
      const isExcluded = this.filters.excludeCompanies.some(comp =>
        this.containsIgnoreCase(job.company, comp)
      );
      if (isExcluded) {
        return null;
      }
    }

    const matchPercentage = Math.round((score / maxScore) * 100);

    return {
      matched: matchPercentage >= (this.config.notifications?.rateLimit?.minMatchScore || 50),
      score: matchPercentage,
      checks,
      job
    };
  }

  /**
   * Filter multiple jobs
   * @param {array} jobs - Array of job objects
   * @returns {array} - Array of matched jobs with scores
   */
  filterJobs(jobs) {
    const results = [];
    for (const job of jobs) {
      const match = this.match(job);
      if (match && match.matched) {
        results.push(match);
      }
    }
    
    // Sort by score (highest first)
    return results.sort((a, b) => b.score - a.score);
  }

  // Helper methods
  containsIgnoreCase(text, search) {
    if (!text || !search) return false;
    return text.toLowerCase().includes(search.toLowerCase());
  }

  isRemoteJob(job) {
    const remoteTerms = ['remote', 'work from home', 'wfh', 'anywhere'];
    const text = `${job.title} ${job.location} ${job.description || ''}`;
    return remoteTerms.some(term => text.toLowerCase().includes(term));
  }

  parseExperience(expText) {
    if (!expText) return null;
    
    // Handle formats like "3-5 years", "5+ years", "2 Yrs"
    const match = expText.match(/(\d+)(?:\s*-\s*(\d+))?/);
    if (match) {
      const min = parseInt(match[1], 10);
      return min;
    }
    return null;
  }

  parseSalary(salaryText) {
    if (!salaryText) return null;
    
    // Extract numbers from salary text
    const matches = salaryText.match(/(\d+(?:,\d+)*)/g);
    if (matches) {
      // Take the first/largest number
      const num = parseInt(matches[matches.length - 1].replace(/,/g, ''), 10);
      return num;
    }
    return null;
  }

  getDaysAgo(dateText) {
    if (!dateText) return 0;
    
    // Handle relative dates
    if (dateText.includes('day') || dateText.includes('hour')) {
      const dayMatch = dateText.match(/(\d+)\s*day/);
      if (dayMatch) return parseInt(dayMatch[1], 10);
      return 0; // Hours = today
    }
    
    // Try parsing as date
    const date = new Date(dateText);
    if (!isNaN(date)) {
      const diff = Date.now() - date.getTime();
      return Math.floor(diff / (1000 * 60 * 60 * 24));
    }
    
    return 0;
  }
}

// Test function
function test() {
  const config = {
    search: {
      keywords: ['software engineer', 'developer'],
      skills: ['JavaScript', 'Node.js', 'React'],
      locations: ['Remote', 'Bangalore'],
      excludeKeywords: ['senior principal']
    },
    filters: {
      minSalary: 1000000,
      postedWithinDays: 7,
      remoteOnly: false
    },
    notifications: {
      rateLimit: { minMatchScore: 60 }
    }
  };

  const matcher = new JobMatcher(config);

  const testJobs = [
    {
      title: 'Software Engineer - Full Stack',
      company: 'TechCorp',
      location: 'Remote',
      description: 'Looking for JavaScript and Node.js developers',
      skills: ['JavaScript', 'Node.js', 'MongoDB'],
      salary: '₹15,00,000 - ₹25,00,000',
      experience: '2-4 years',
      postedDate: '2 days ago',
      source: 'linkedin',
      url: 'https://example.com/job1'
    },
    {
      title: 'Senior Principal Architect',
      company: 'BigCorp',
      location: 'Mumbai',
      description: '10+ years experience required',
      salary: '₹50,00,000',
      experience: '10+ years',
      postedDate: '1 day ago',
      source: 'naukri',
      url: 'https://example.com/job2'
    },
    {
      title: 'React Developer',
      company: 'StartupXYZ',
      location: 'Bangalore',
      description: 'Frontend developer with React experience',
      skills: ['React', 'JavaScript', 'CSS'],
      salary: 'Not disclosed',
      experience: '1-3 years',
      postedDate: '3 days ago',
      source: 'linkedin',
      url: 'https://example.com/job3'
    }
  ];

  console.log('\n🧪 Testing Job Matcher\n');
  
  for (const job of testJobs) {
    const result = matcher.match(job);
    console.log(`\n📋 ${job.title} at ${job.company}`);
    if (result) {
      console.log(`   Score: ${result.score}% | Matched: ${result.matched ? '✅' : '❌'}`);
      console.log(`   Checks: ${result.checks.join(', ')}`);
    } else {
      console.log('   Rejected by filter ❌');
    }
  }

  const filtered = matcher.filterJobs(testJobs);
  console.log(`\n📊 Total jobs: ${testJobs.length}, Matched: ${filtered.length}`);
}

module.exports = { JobMatcher, test };

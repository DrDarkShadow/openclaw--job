#!/usr/bin/env node
/**
 * Job Search Automation System
 * Main monitoring and scraping module
 * 
 * Usage:
 *   node scraper.js              - Run single check
 *   node scraper.js --daemon     - Run continuously with interval
 *   node scraper.js --dry-run    - Test without sending notifications
 *   node scraper.js --init       - Mark all current jobs as seen (setup)
 */

const fs = require('fs');
const https = require('https');
const { JobStorage } = require('./storage');
const { JobMatcher } = require('./matcher');
const { Notifier } = require('./notifier');

class JobMonitor {
  constructor() {
    this.config = this.loadConfig();
    this.storage = new JobStorage(this.config.monitoring?.storageFile);
    this.matcher = new JobMatcher(this.config);
    this.notifier = new Notifier(this.config);
    this.dryRun = false;
    this.stats = {
      checked: 0,
      new: 0,
      matched: 0,
      errors: 0
    };
  }

  loadConfig() {
    try {
      const configPath = process.env.JOB_CONFIG || './config.json';
      const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      return config;
    } catch (error) {
      console.error('❌ Failed to load config:', error.message);
      process.exit(1);
    }
  }

  /**
   * Main execution
   */
  async run(args = {}) {
    console.log('\n🔍 Job Search Automation Starting...');
    console.log(`⏰ ${new Date().toLocaleString()}`);
    console.log(`📊 Storage: ${this.storage.seenJobs.size} previously seen jobs\n`);

    if (args.init) {
      return await this.initialize();
    }

    this.dryRun = args.dryRun || false;
    
    try {
      const allJobs = [];

      // Scrape each enabled source
      if (this.config.sources?.linkedin?.enabled) {
        const jobs = await this.scrapeLinkedIn();
        allJobs.push(...jobs);
        await this.delay(this.config.respectful?.delayBetweenRequestsMs || 2000);
      }

      if (this.config.sources?.naukri?.enabled) {
        const jobs = await this.scrapeNaukri();
        allJobs.push(...jobs);
      }

      this.stats.checked = allJobs.length;
      console.log(`\n📥 Found ${allJobs.length} total jobs from all sources`);

      // Find new jobs (not seen before)
      const newJobs = allJobs.filter(job => {
        const jobId = this.storage.generateJobId(job);
        return !this.storage.has(jobId);
      });

      this.stats.new = newJobs.length;
      console.log(`🆕 ${newJobs.length} new jobs`);

      // Match against criteria
      const matches = this.matcher.filterJobs(newJobs);
      this.stats.matched = matches.length;

      console.log(`🎯 ${matches.length} jobs match your criteria`);

      if (matches.length > 0) {
        // Add to storage
        for (const match of matches) {
          const jobId = this.storage.generateJobId(match.job);
          this.storage.add(jobId, {
            source: match.job.source,
            title: match.job.title,
            score: match.score
          });
        }

        // Notify
        if (!this.dryRun) {
          await this.notifier.notify(matches);
        } else {
          console.log('🔕 Dry run mode - no notifications sent');
          this.notifier.notifyConsole(matches);
        }
      }

      // Save storage
      this.storage.save();

      // Cleanup old entries periodically
      if (Math.random() < 0.1) { // 10% chance
        this.storage.cleanup();
      }

      this.logSummary();
      return matches;

    } catch (error) {
      console.error('❌ Monitor failed:', error.message);
      this.stats.errors++;
      this.notifier.log('ERROR', `Monitor crash: ${error.message}`);
      throw error;
    }
  }

  /**
   * LinkedIn Job Scraping
   * Note: Uses public job search URLs with query parameters
   */
  async scrapeLinkedIn() {
    console.log('🔍 Checking LinkedIn...');
    const jobs = [];
    const maxRetries = this.config.respectful?.maxRetries || 3;
    
    for (const keyword of this.config.search.keywords.slice(0, 2)) { // Limit keywords
      let retries = 0;
      let success = false;

      while (retries < maxRetries && !success) {
        try {
          const searchUrl = this.buildLinkedInUrl(keyword);
          const html = await this.fetchWithRespect(searchUrl);
          const parsed = this.parseLinkedInJobs(html, keyword);
          jobs.push(...parsed);
          success = true;
        } catch (error) {
          retries++;
          console.warn(`⚠️ LinkedIn attempt ${retries} failed: ${error.message}`);
          if (retries < maxRetries) {
            await this.delay(this.config.respectful?.retryDelayMs || 5000);
          }
        }
      }
    }

    console.log(`   ✅ LinkedIn: ${jobs.length} jobs`);
    return jobs;
  }

  buildLinkedInUrl(keyword) {
    const geoId = this.config.sources.linkedin.geoId || '102713006'; // India default
    const f_TPR = this.config.sources.linkedin.f_TPR || 'r604800'; // Past week
    
    return `https://www.linkedin.com/jobs/search?` +
           `keywords=${encodeURIComponent(keyword)}&` +
           `location=${encodeURIComponent('India')}&` +
           `geoId=${geoId}&` +
           `f_TPR=${f_TPR}&` +
           `position=1&pageNum=0`;
  }

  parseLinkedInJobs(html, keyword) {
    const jobs = [];
    
    // LinkedIn uses specific data structures
    // Look for JSON-LD job data or specific HTML patterns
    try {
      // Extract job listings from embedded JSON
      const jsonLdMatch = html.match(/<script type="application\/ld\+json">(.*?)<\/script>/gs);
      if (jsonLdMatch) {
        for (const script of jsonLdMatch) {
          try {
            const jsonStr = script.replace(/<script[^>]*>|<\/script>/g, '');
            const data = JSON.parse(jsonStr);
            
            if (data['@type'] === 'JobPosting') {
              jobs.push({
                title: data.title || 'Unknown',
                company: data.hiringOrganization?.name || 'Unknown',
                location: data.jobLocation?.address?.addressLocality || 
                          data.jobLocation?.address?.addressCountry || 'Remote',
                description: data.description || '',
                url: data.url || '',
                postedDate: data.datePosted || 'Unknown',
                source: 'linkedin',
                skills: this.extractSkills(data.description || ''),
                jobType: data.employmentType || 'Full-time'
              });
            }
          } catch (e) {
            // Continue on parse error
          }
        }
      }

      // Fallback: Parse HTML structure if JSON-LD not found
      if (jobs.length === 0) {
        const jobCards = html.match(/<div[^>]*class="[^"]*job-search-card[^"]*"[^>]*>.*?<\/div>/gs) || [];
        
        for (const card of jobCards.slice(0, this.config.monitoring?.maxJobsPerCheck || 25)) {
          const titleMatch = card.match(/<h3[^>]*>(.*?)<\/h3>/s);
          const companyMatch = card.match(/<h4[^>]*>(.*?)<\/h4>/s);
          const locationMatch = card.match(/<span[^>]*class="[^"]*job-search-card__location[^"]*"[^>]*>(.*?)<\/span>/s);
          const linkMatch = card.match(/href="(\/jobs\/view\/[^"]+)"/);

          if (titleMatch) {
            jobs.push({
              title: this.cleanHtml(titleMatch[1]),
              company: companyMatch ? this.cleanHtml(companyMatch[1]) : 'Unknown',
              location: locationMatch ? this.cleanHtml(locationMatch[1]) : 'Unknown',
              description: '',
              url: linkMatch ? `https://www.linkedin.com${linkMatch[1]}` : '',
              postedDate: 'Recently',
              source: 'linkedin',
              skills: [],
              jobType: 'Full-time'
            });
          }
        }
      }
    } catch (error) {
      console.warn('⚠️ LinkedIn parsing error:', error.message);
    }

    return jobs.slice(0, this.config.monitoring?.maxJobsPerCheck || 25);
  }

  /**
   * Naukri.com Scraping
   */
  async scrapeNaukri() {
    console.log('🔍 Checking Naukri...');
    const jobs = [];
    const maxRetries = this.config.respectful?.maxRetries || 3;
    
    for (const keyword of this.config.search.keywords.slice(0, 2)) {
      let retries = 0;
      let success = false;

      while (retries < maxRetries && !success) {
        try {
          const searchUrl = this.buildNaukriUrl(keyword);
          const html = await this.fetchWithRespect(searchUrl);
          const parsed = this.parseNaukriJobs(html, keyword);
          jobs.push(...parsed);
          success = true;
        } catch (error) {
          retries++;
          console.warn(`⚠️ Naukri attempt ${retries} failed: ${error.message}`);
          if (retries < maxRetries) {
            await this.delay(this.config.respectful?.retryDelayMs || 5000);
          }
        }
      }
    }

    console.log(`   ✅ Naukri: ${jobs.length} jobs`);
    return jobs;
  }

  buildNaukriUrl(keyword) {
    const location = this.config.search.locations[0] || '';
    return `https://www.naukri.com/${encodeURIComponent(keyword.replace(/\s+/g, '-'))}-jobs` +
           (location ? `-in-${encodeURIComponent(location.replace(/\s+/g, '-'))}` : '');
  }

  parseNaukriJobs(html, keyword) {
    const jobs = [];
    
    try {
      // Naukri job cards have specific class names
      const jobCards = html.match(/<article[^>]*class="[^"]*job-card[^"]*"[^>]*>.*?<\/article>/gs) || [];
      
      for (const card of jobCards.slice(0, this.config.monitoring?.maxJobsPerCheck || 25)) {
        const titleMatch = card.match(/<a[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)<\/a>/s);
        const companyMatch = card.match(/<a[^>]*class="[^"]*comp-name[^"]*"[^>]*>(.*?)<\/a>/s);
        const locationMatch = card.match(/<span[^>]*class="[^"]*loc[^"]*"[^>]*>(.*?)<\/span>/s);
        const expMatch = card.match(/<span[^>]*class="[^"]*exp[^"]*"[^>]*>(.*?)<\/span>/s);
        const salaryMatch = card.match(/<span[^>]*class="[^"]*salary[^"]*"[^>]*>(.*?)<\/span>/s);
        const linkMatch = card.match(/<a[^>]*href="(https:\/\/www\.naukri\.com\/[^"]+)"/);

        if (titleMatch) {
          jobs.push({
            title: this.cleanHtml(titleMatch[1]),
            company: companyMatch ? this.cleanHtml(companyMatch[1]) : 'Unknown',
            location: locationMatch ? this.cleanHtml(locationMatch[1]) : 'India',
            description: '',
            url: linkMatch ? linkMatch[1] : '',
            postedDate: 'Recently',
            experience: expMatch ? this.cleanHtml(expMatch[1]) : '',
            salary: salaryMatch ? this.cleanHtml(salaryMatch[1]) : 'Not disclosed',
            source: 'naukri',
            skills: this.extractSkills(card),
            jobType: 'Full-time'
          });
        }
      }

      // Alternative: Parse JSON embedded in page
      if (jobs.length === 0) {
        const jsonMatch = html.match(/window\.__INITIAL_STATE__\s*=\s*({.*?});/s);
        if (jsonMatch) {
          try {
            const data = JSON.parse(jsonMatch[1]);
            const jobListings = data?.jobSearch?.jobList || [];
            
            for (const job of jobListings.slice(0, 25)) {
              jobs.push({
                title: job.title || job.jobTitle || 'Unknown',
                company: job.companyName || 'Unknown',
                location: job.location || job.placeholders?.[0]?.label || 'India',
                description: job.jobDescription || '',
                url: job.jdURL || job.absoluteURL || '',
                postedDate: job.postDate || job.postedOn || 'Recently',
                experience: job.experience || '',
                salary: job.salary || 'Not disclosed',
                source: 'naukri',
                skills: job.skills || [],
                jobType: 'Full-time'
              });
            }
          } catch (e) {
            // JSON parse failed
          }
        }
      }
    } catch (error) {
      console.warn('⚠️ Naukri parsing error:', error.message);
    }

    return jobs.slice(0, this.config.monitoring?.maxJobsPerCheck || 25);
  }

  /**
   * Fetch with respectful delays and headers
   */
  async fetchWithRespect(url) {
    return new Promise((resolve, reject) => {
      const userAgent = this.config.monitoring?.userAgent || 
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';
      
      const client = url.startsWith('https') ? https : require('http');
      
      const options = {
        headers: {
          'User-Agent': userAgent,
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.5',
          'Accept-Encoding': 'gzip, deflate, br',
          'DNT': '1',
          'Connection': 'keep-alive'
        },
        timeout: 30000
      };

      const req = client.get(url, options, (res) => {
        if (res.statusCode === 301 || res.statusCode === 302) {
          reject(new Error(`Redirect to ${res.headers.location}`));
          return;
        }
        
        if (res.statusCode !== 200) {
          reject(new Error(`HTTP ${res.statusCode}`));
          return;
        }

        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => resolve(data));
      });

      req.on('error', reject);
      req.on('timeout', () => {
        req.destroy();
        reject(new Error('Request timeout'));
      });
    });
  }

  extractSkills(text) {
    const commonSkills = [
      'JavaScript', 'Python', 'Java', 'C++', 'C#', 'Go', 'Rust', 'Ruby', 'PHP',
      'Node.js', 'React', 'Angular', 'Vue', 'Next.js', 'Express',
      'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Elasticsearch',
      'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform',
      'Git', 'Jenkins', 'CI/CD', 'Linux', 'REST', 'GraphQL',
      'TypeScript', 'HTML', 'CSS', 'Sass', 'Tailwind'
    ];

    return commonSkills.filter(skill => 
      text.toLowerCase().includes(skill.toLowerCase())
    );
  }

  cleanHtml(html) {
    return html
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Initialize mode - mark all current jobs as seen
   */
  async initialize() {
    console.log('🚀 Initialization mode - collecting current jobs as baseline...\n');
    
    const allJobs = [];
    
    if (this.config.sources?.linkedin?.enabled) {
      const jobs = await this.scrapeLinkedIn();
      allJobs.push(...jobs);
      await this.delay(2000);
    }

    if (this.config.sources?.naukri?.enabled) {
      const jobs = await this.scrapeNaukri();
      allJobs.push(...jobs);
    }

    console.log(`\n📊 Found ${allJobs.length} current jobs`);
    const marked = this.storage.markAllAsSeen(allJobs);
    
    console.log(`✅ Setup complete! ${marked} jobs marked as seen.`);
    console.log('💡 Run without --init flag to start monitoring for NEW jobs only.');
    
    return allJobs;
  }

  logSummary() {
    console.log('\n📈 Session Summary:');
    console.log(`   Checked: ${this.stats.checked} jobs`);
    console.log(`   New: ${this.stats.new} jobs`);
    console.log(`   Matched: ${this.stats.matched} jobs`);
    console.log(`   Errors: ${this.stats.errors}`);
    console.log(`\n⏭️  Next check in ${this.config.monitoring?.checkIntervalHours || 4} hours\n`);
  }
}

// CLI handling
async function main() {
  const args = process.argv.slice(2);
  const options = {
    init: args.includes('--init') || args.includes('init'),
    dryRun: args.includes('--dry-run') || args.includes('--test'),
    daemon: args.includes('--daemon') || args.includes('-d'),
    help: args.includes('--help') || args.includes('-h')
  };

  if (options.help) {
    console.log(`
Job Search Automation System

Usage:
  node scraper.js [options]

Options:
  --init        Mark all current jobs as seen (first-time setup)
  --dry-run     Test run without sending notifications
  --daemon, -d  Run continuously with configured interval
  --help, -h    Show this help

Environment:
  JOB_CONFIG    Path to config file (default: ./config.json)

Examples:
  node scraper.js --init        # Setup: mark existing jobs as seen
  node scraper.js               # Single check
  node scraper.js --daemon      # Continuous monitoring
`);
    process.exit(0);
  }

  const monitor = new JobMonitor();

  if (options.daemon) {
    console.log('👁️ Daemon mode - will run continuously\n');
    
    // Run immediately
    await monitor.run(options);
    
    // Schedule next runs
    const intervalHours = monitor.config.monitoring?.checkIntervalHours || 4;
    const intervalMs = intervalHours * 60 * 60 * 1000;
    
    console.log(`⏰ Scheduled to run every ${intervalHours} hours`);
    
    setInterval(async () => {
      console.log(`\n⏰ Scheduled run at ${new Date().toLocaleString()}`);
      await monitor.run(options);
    }, intervalMs);
    
    // Keep process alive
    process.stdin.resume();
  } else {
    await monitor.run(options);
  }
}

// Run if executed directly
if (require.main === module) {
  main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

module.exports = { JobMonitor };

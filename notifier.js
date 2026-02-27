/**
 * Notification System
 * Sends alerts for matching jobs via multiple channels
 */

const fs = require('fs');

class Notifier {
  constructor(config) {
    this.config = config;
    this.notifications = config.notifications || { enabled: true, channels: ['console'] };
    this.rateLimit = this.notifications.rateLimit || { maxPerHour: 10, minMatchScore: 70 };
    this.recentNotifications = [];
    this.logFile = config.monitoring?.logFile || './job-monitor.log';
  }

  /**
   * Send notification for matching jobs
   * @param {array} matches - Array of job match results
   */
  async notify(matches) {
    if (!this.notifications.enabled || matches.length === 0) {
      return;
    }

    // Rate limiting
    const now = Date.now();
    const oneHourAgo = now - (60 * 60 * 1000);
    this.recentNotifications = this.recentNotifications.filter(t => t > oneHourAgo);
    
    if (this.recentNotifications.length >= this.rateLimit.maxPerHour) {
      console.log(`⏳ Rate limit reached (${this.rateLimit.maxPerHour}/hour). Skipping notifications.`);
      this.log('RATE_LIMIT', `Skipped ${matches.length} matches due to rate limit`);
      return;
    }

    // Filter by min match score
    const qualifiedMatches = matches.filter(m => m.score >= this.rateLimit.minMatchScore);
    
    if (qualifiedMatches.length === 0) {
      console.log(`📉 All matches below minimum score (${this.rateLimit.minMatchScore}%)`);
      return;
    }

    // Send through each enabled channel
    for (const channel of this.notifications.channels) {
      try {
        switch (channel) {
          case 'console':
            await this.notifyConsole(qualifiedMatches);
            break;
          case 'webhook':
            await this.notifyWebhook(qualifiedMatches);
            break;
          case 'file':
            await this.notifyFile(qualifiedMatches);
            break;
          case 'email':
            await this.notifyEmail(qualifiedMatches);
            break;
          default:
            console.warn(`Unknown notification channel: ${channel}`);
        }
      } catch (error) {
        console.error(`❌ Notification failed for ${channel}:`, error.message);
        this.log('ERROR', `Notification failed: ${error.message}`);
      }
    }

    // Track notification
    this.recentNotifications.push(now);
    this.log('NOTIFY', `Sent ${qualifiedMatches.length} job notifications`);
  }

  /**
   * Console output notification
   */
  async notifyConsole(matches) {
    console.log('\n' + '='.repeat(60));
    console.log(`🎯 ${matches.length} NEW JOB MATCH${matches.length > 1 ? 'ES' : ''} FOUND!`);
    console.log('='.repeat(60));

    for (const match of matches) {
      const job = match.job;
      console.log(`\n📌 ${job.title}`);
      console.log(`   🏢 ${job.company} | 📍 ${job.location}`);
      console.log(`   🔗 ${job.url}`);
      console.log(`   📊 Match Score: ${match.score}%`);
      console.log(`   ✅ ${match.checks.join(' | ')}`);
      if (job.salary) console.log(`   💰 ${job.salary}`);
      if (job.experience) console.log(`   📅 ${job.experience}`);
      console.log(`   📰 Source: ${job.source} | Posted: ${job.postedDate || 'Unknown'}`);
      console.log('-'.repeat(50));
    }

    console.log('\n💡 Run `node scraper.js apply <job-number>` to see application info\n');
  }

  /**
   * Webhook notification (Discord, Slack, etc.)
   */
  async notifyWebhook(matches) {
    const webhookUrl = this.notifications.webhookUrl;
    if (!webhookUrl) {
      console.warn('⚠️ Webhook URL not configured');
      return;
    }

    const payload = {
      text: `🎯 ${matches.length} new job matches found!`,
      jobs: matches.map(m => ({
        title: m.job.title,
        company: m.job.company,
        location: m.job.location,
        url: m.job.url,
        score: m.score,
        source: m.job.source
      }))
    };

    try {
      const https = require('https');
      const url = new URL(webhookUrl);
      
      const options = {
        hostname: url.hostname,
        path: url.pathname + url.search,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      };

      await new Promise((resolve, reject) => {
        const req = https.request(options, (res) => {
          if (res.statusCode === 200 || res.statusCode === 204) {
            resolve();
          } else {
            reject(new Error(`Webhook returned ${res.statusCode}`));
          }
        });

        req.on('error', reject);
        req.write(JSON.stringify(payload));
        req.end();
      });

      console.log('📤 Webhook notification sent');
    } catch (error) {
      throw new Error(`Webhook failed: ${error.message}`);
    }
  }

  /**
   * File-based notification (write to alerts file)
   */
  async notifyFile(matches) {
    const timestamp = new Date().toISOString();
    const alertFile = './job-alerts.log';
    
    let content = `\n[${timestamp}] NEW JOB MATCHES\n`;
    content += '='.repeat(60) + '\n';

    for (const match of matches) {
      const job = match.job;
      content += `\nTitle: ${job.title}\n`;
      content += `Company: ${job.company}\n`;
      content += `Location: ${job.location}\n`;
      content += `URL: ${job.url}\n`;
      content += `Score: ${match.score}%\n`;
      content += `Source: ${job.source}\n`;
      content += '-'.repeat(40) + '\n';
    }

    fs.appendFileSync(alertFile, content);
    console.log(`📝 Alerts written to ${alertFile}`);
  }

  /**
   * Email notification (placeholder - requires SMTP config)
   */
  async notifyEmail(matches) {
    if (!this.notifications.email?.enabled) {
      console.warn('⚠️ Email notifications not configured');
      return;
    }

    // This would require nodemailer or similar
    console.log('📧 Email notification (not implemented - configure SMTP first)');
    this.log('WARN', 'Email notifications requested but not configured');
  }

  /**
   * Log activity
   */
  log(level, message) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [${level}] ${message}\n`;
    
    console.log(logEntry.trim());
    
    try {
      fs.appendFileSync(this.logFile, logEntry);
    } catch (error) {
      // Silent fail for logging
    }
  }

  /**
   * Generate application preparation info
   */
  generateApplicationPrep(match) {
    const job = match.job;
    const config = this.config;

    const prep = {
      job,
      suggestedResumePoints: [],
      coverLetterTips: [],
      questionsToAsk: [
        'What does a typical day look like in this role?',
        'What are the biggest challenges the team is currently facing?',
        'How is success measured in this position?'
      ],
      researchTasks: [
        `Review ${job.company}'s recent products/news`,
        'Check company culture on Glassdoor',
        'Look up interviewers on LinkedIn'
      ]
    };

    // Match skills from config to job
    if (job.skills) {
      const matchingSkills = config.search.skills.filter(skill =>
        job.skills.some(js => js.toLowerCase().includes(skill.toLowerCase()))
      );
      prep.suggestedResumePoints = matchingSkills.map(s => `Highlight ${s} experience`);
    }

    if (this.isRemoteJob(job)) {
      prep.coverLetterTips.push('Mention remote work experience and communication skills');
    }

    return prep;
  }

  isRemoteJob(job) {
    const remoteTerms = ['remote', 'work from home', 'wfh'];
    const text = `${job.title} ${job.location}`;
    return remoteTerms.some(term => text.toLowerCase().includes(term));
  }
}

module.exports = { Notifier };

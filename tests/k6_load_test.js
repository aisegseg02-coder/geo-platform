import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '30s', target: 20 },   // Ramp up to 20 users
    { duration: '1m', target: 50 },    // Spike to 50 users (Load Test)
    { duration: '30s', target: 100 },  // Stress Test
    { duration: '30s', target: 0 },    // Scale down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests should be < 2s
    errors: ['rate<0.05'],             // Error rate should be < 5%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // 1. Test the Health Endpoint
  let resHealth = http.get(`${BASE_URL}/health`);
  let checkHealth = check(resHealth, {
    'Health is 200': (r) => r.status === 200,
  });
  errorRate.add(!checkHealth);

  // 2. Test Crawl API (Creates a Job)
  const crawlPayload = JSON.stringify({
    url: 'https://example.com',
    org_name: 'TestLoadBrand',
    org_url: 'https://example.com',
    max_pages: 1
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
  };

  let resCrawl = http.post(`${BASE_URL}/api/jobs`, crawlPayload, params);
  
  let checkCrawl = check(resCrawl, {
    'Crawl job accepted (200)': (r) => r.status === 200,
    'Returned Job ID': (r) => JSON.parse(r.body).job_id !== undefined,
  });
  errorRate.add(!checkCrawl);

  // If a job was returned, track its status
  if (checkCrawl) {
    let jobId = JSON.parse(resCrawl.body).job_id;
    let resJob = http.get(`${BASE_URL}/api/jobs/${jobId}`);
    check(resJob, {
      'Job Status Check ok': (r) => r.status === 200,
    });
  }

  // Sleep randomly to mimic user reading/typing
  sleep(Math.random() * 3 + 1); 
}

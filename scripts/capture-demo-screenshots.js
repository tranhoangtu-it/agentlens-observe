/**
 * Capture demo screenshots of AgentLens dashboard for README.
 * Run: node scripts/capture-demo-screenshots.js
 * Requires: server on :8002 with demo data + static dashboard built
 */

const puppeteer = require('puppeteer');
const path = require('path');
const { execSync } = require('child_process');

const BASE_URL = 'http://localhost:8002';
const OUT_DIR = path.join(__dirname, '..', 'docs', 'screenshots');

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function getFirstTraceId() {
  const response = execSync(`curl -s ${BASE_URL}/api/traces`);
  const data = JSON.parse(response.toString());
  return data.traces && data.traces.length > 0 ? data.traces[0].id : null;
}

async function main() {
  const firstTraceId = await getFirstTraceId();
  console.log(`First trace ID: ${firstTraceId}`);

  const browser = await puppeteer.launch({
    headless: true,
    defaultViewport: { width: 1280, height: 800 },
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();

  // 1. Trace list page — main dashboard with sidebar + trace list table
  console.log('1/3 Capturing trace list...');
  await page.goto(`${BASE_URL}/#/`, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await sleep(3000);
  await page.screenshot({ path: path.join(OUT_DIR, '01-trace-list.png'), fullPage: false });
  console.log('  ok 01-trace-list.png');

  // 2. Trace detail page — topology graph with nodes
  console.log('2/3 Capturing trace detail (topology graph)...');
  const traceDetailUrl = `${BASE_URL}/#/traces/${firstTraceId}`;
  await page.goto(traceDetailUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await sleep(3000);
  await page.screenshot({ path: path.join(OUT_DIR, '02-trace-detail.png'), fullPage: false });
  console.log('  ok 02-trace-detail.png');

  // 3. Span detail — same trace detail URL, but click on a graph node to open span detail panel
  console.log('3/3 Capturing span detail panel...');
  const nodes = await page.$$('.react-flow__node');
  console.log(`  Found ${nodes.length} graph nodes`);
  if (nodes.length > 1) {
    // Click the second node (a child span — tool_call or llm_call)
    await nodes[1].click();
    await sleep(1500);
    await page.screenshot({ path: path.join(OUT_DIR, '03-span-detail.png'), fullPage: false });
    console.log('  ok 03-span-detail.png');
  } else if (nodes.length > 0) {
    await nodes[0].click();
    await sleep(1500);
    await page.screenshot({ path: path.join(OUT_DIR, '03-span-detail.png'), fullPage: false });
    console.log('  ok 03-span-detail.png');
  } else {
    console.log('  warning: No graph nodes found, capturing as-is');
    await page.screenshot({ path: path.join(OUT_DIR, '03-span-detail.png'), fullPage: false });
  }

  await browser.close();
  console.log(`\nDone! Screenshots saved to ${OUT_DIR}/`);
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});

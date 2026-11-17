// Screenshots of the built site, named by page and width.
//
//   npm run build
//   npm i --no-save playwright        # not a dependency of this site
//   npm run shots                     # into site/shots/
//   npm run shots -- --out ~/Desktop/sg-mockgun-site
//
// It serves build/ itself, so nothing else has to be running, and it prints every network request
// the page made. A request to any host other than the one it serves from is a failure.

import { createReadStream, existsSync, mkdirSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { dirname, extname, join, normalize } from 'node:path';
import { homedir } from 'node:os';
import { fileURLToPath } from 'node:url';

const siteDir = dirname(dirname(fileURLToPath(import.meta.url)));

const TYPES = {
	'.html': 'text/html',
	'.js': 'text/javascript',
	'.css': 'text/css',
	'.json': 'application/json',
	'.svg': 'image/svg+xml',
	'.png': 'image/png',
	'.jpg': 'image/jpeg',
	'.webm': 'video/webm',
	'.mp4': 'video/mp4',
	'.woff2': 'font/woff2'
};

function arg(name, fallback) {
	const at = process.argv.indexOf(`--${name}`);
	return at === -1 ? fallback : process.argv[at + 1];
}

const root = join(siteDir, 'build');
const out = (arg('out', join(siteDir, 'shots')) ?? '').replace(
	/^~/,
	homedir()
);

if (!existsSync(root)) {
	console.error('No build/. Run: npm run build');
	process.exit(1);
}
mkdirSync(out, { recursive: true });

const server = createServer((request, response) => {
	const path = normalize(decodeURIComponent(new URL(request.url, 'http://x').pathname));
	let file = join(root, path);
	if (existsSync(file) && statSync(file).isDirectory()) file = join(file, 'index.html');
	if (!file.startsWith(root) || !existsSync(file)) {
		response.writeHead(404).end('not found');
		return;
	}
	response.writeHead(200, { 'content-type': TYPES[extname(file)] ?? 'application/octet-stream' });
	createReadStream(file).pipe(response);
});

await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;

let chromium;
try {
	({ chromium } = await import('playwright'));
} catch {
	console.error('playwright is not installed here. Run: npm i --no-save playwright');
	server.close();
	process.exit(1);
}

// landing.png is the card sg-suite shows.
const SHOTS = [
	{ name: 'landing', page: '/', at: 'hero', width: 1440, height: 900 },
	{ name: 'home_full_1440', page: '/', at: 'full', width: 1440, height: 900 },
	{ name: 'home_full_375', page: '/', at: 'full', width: 375, height: 780 },
	{ name: 'docs_modelled_1440', page: '/docs/modelled/', at: 'full', width: 1440, height: 900 },
	{ name: 'docs_migrate_375', page: '/docs/migrate/', at: 'full', width: 375, height: 780 }
];

const browser = await chromium.launch();
const requests = new Set();
const overflow = [];

for (const shot of SHOTS) {
	const context = await browser.newContext({
		viewport: { width: shot.width, height: shot.height },
		colorScheme: 'dark',
		deviceScaleFactor: 2
	});
	const page = await context.newPage();
	page.on('request', (request) => requests.add(request.url()));
	await page.goto(origin + shot.page, { waitUntil: 'networkidle' });
	await page.waitForTimeout(500);

	// Anything but 'hero' and 'full' names a section id on the page.
	if (shot.at !== 'hero' && shot.at !== 'full') {
		await page.locator(`#${shot.at}`).scrollIntoViewIfNeeded();
		await page.waitForTimeout(900);
	}

	if (shot.at === 'full') {
		// Sections fade in when they are scrolled to. Walk the page down and back so a full-page
		// screenshot holds the state a reader would have reached.
		const height = await page.evaluate(() => document.body.scrollHeight);
		for (let y = 0; y < height; y += shot.height) {
			await page.evaluate((to) => window.scrollTo(0, to), y);
			await page.waitForTimeout(180);
		}
		await page.evaluate(() => window.scrollTo(0, 0));
		await page.waitForTimeout(600);
	}

	const wide = await page.evaluate(
		() => document.documentElement.scrollWidth - document.documentElement.clientWidth
	);
	if (wide > 0) overflow.push(`${shot.page} at ${shot.width}px scrolls ${wide}px sideways`);

	await page.screenshot({
		path: join(out, `${shot.name}.png`),
		fullPage: shot.at === 'full'
	});
	await context.close();
}

await browser.close();
server.close();

const foreign = [...requests].filter((url) => !url.startsWith(origin));
console.log(`\n${SHOTS.length} screenshots in ${out}`);
console.log(`\n${requests.size} network requests, all from the page itself:`);
for (const url of [...requests].sort()) console.log(`  ${url.replace(origin, '')}`);
if (foreign.length) {
	console.error(`\nRequests that left the origin:\n  ${foreign.join('\n  ')}`);
	process.exitCode = 1;
}
if (overflow.length) {
	console.error(`\nHorizontal scroll:\n  ${overflow.join('\n  ')}`);
	process.exitCode = 1;
}

import { docs, repo } from '$lib/site.js';

/** The canonical origin. The sitemap, llms.txt and the share tags use absolute URLs. */
export const origin = 'https://sg-mockgun.vercel.app';

export const siteName = 'sg-mockgun';

/** Every page, as served: the landing page, the docs index, the docs pages. */
export function pages() {
	return ['/', '/docs/', ...docs.map((d) => `/docs/${d.slug}/`)];
}

export function sitemap() {
	const urls = pages()
		.map((path) => `\t<url><loc>${origin}${path}</loc></url>`)
		.join('\n');
	return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
}

export function robots() {
	return `User-agent: *
Allow: /

Sitemap: ${origin}/sitemap.xml
`;
}

/** What an LLM client reads first: what the package is, then one line per page. */
export function llmsTxt() {
	const lines = [
		'# sg-mockgun',
		'',
		'sg-mockgun replaces shotgun_api3.lib.mockgun with an in-memory Flow Production Tracking mock',
		'that answers as a live site answers over api3.',
		'',
		'Install: pip install sg-mockgun. Requires Python 3.9 and shotgun-api3 3.10.5.',
		`Source, BSD-3-Clause: ${repo}. Issues: ${repo}/issues.`,
		'',
		'## Docs',
		'',
		...docs.map((d) => `- [${d.title}](${origin}/docs/${d.slug}/): ${d.blurb}`),
		'',
		'## Reference',
		'',
		`- Coverage table: ${repo}/blob/main/docs/coverage.md`,
		`- api3 answers, one file per probe: ${repo}/blob/main/docs/api3/README.md`,
		`- Changelog: ${repo}/blob/main/CHANGELOG.md`,
		''
	];
	return lines.join('\n');
}

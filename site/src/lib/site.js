export const repo = 'https://github.com/ksallee/sg-mockgun';
export const pypi = 'https://pypi.org/project/sg-mockgun/';
export const licence = `${repo}/blob/main/LICENSE`;
export const changelog = `${repo}/blob/main/CHANGELOG.md`;
export const coverage = `${repo}/blob/main/docs/coverage.md`;
export const api3 = `${repo}/blob/main/docs/api3`;

/** The docs pages, in reading order. The footer, the sidebar and /docs list these. */
export const docs = [
	{ slug: 'migrate', title: 'Install and migrate', blurb: 'Install, the import swap, differences from upstream mockgun.' },
	{ slug: 'pytest', title: 'Testing with pytest', blurb: 'The sg fixture, seed files, snapshot and restore.' },
	{ slug: 'server', title: 'HTTP server', blurb: 'sg-mockgun serve, for a shotgun_api3 client in another process.' },
	{ slug: 'modelled', title: 'What is modelled', blurb: 'Behaviour by area, with the api3 answer each part follows.' }
];

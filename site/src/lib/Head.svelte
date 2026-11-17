<script>
	import { page } from '$app/state';
	import { origin, siteName } from '$lib/seo.js';

	/** The title, the description and the canonical URL of one page. */
	let { title, description } = $props();

	const url = $derived(origin + page.url.pathname);
</script>

<svelte:head>
	<title>{title}</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={url} />
	<meta property="og:type" content="website" />
	<meta property="og:site_name" content={siteName} />
	<meta property="og:title" content={title} />
	<meta property="og:description" content={description} />
	<meta property="og:url" content={url} />
	<meta name="twitter:card" content="summary" />
	<meta name="twitter:title" content={title} />
	<meta name="twitter:description" content={description} />
</svelte:head>

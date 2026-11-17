<script>
	import Head from '$lib/Head.svelte';
	import Markdown from '$lib/Markdown.svelte';
	import source from '$lib/content/server.md?raw';
</script>

<svelte:head>
	<Head title="HTTP server. sg-mockgun" description="sg-mockgun serve runs one mock instance behind the api3 JSON protocol." />
</svelte:head>

<h1>HTTP server</h1>
<Markdown {source} />

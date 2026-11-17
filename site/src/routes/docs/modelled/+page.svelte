<script>
	import Head from '$lib/Head.svelte';
	import Markdown from '$lib/Markdown.svelte';
	import source from '$lib/content/modelled.md?raw';
</script>

<svelte:head>
	<Head title="What is modelled. sg-mockgun" description="sg-mockgun behaviour by area, with the api3 answer each part follows." />
</svelte:head>

<h1>What is modelled</h1>
<Markdown {source} />

<script>
	import Head from '$lib/Head.svelte';
	import Markdown from '$lib/Markdown.svelte';
	import source from '$lib/content/pytest.md?raw';
</script>

<svelte:head>
	<Head title="Testing with pytest. sg-mockgun" description="The sg fixture, seed files, snapshot and restore." />
</svelte:head>

<h1>Testing with pytest</h1>
<Markdown {source} />

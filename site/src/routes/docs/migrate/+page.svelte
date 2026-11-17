<script>
	import Head from '$lib/Head.svelte';
	import Markdown from '$lib/Markdown.svelte';
	import source from '$lib/content/migrate.md?raw';
</script>

<svelte:head>
	<Head title="Install and migrate. sg-mockgun" description="Install sg-mockgun, swap the import from shotgun_api3.lib.mockgun, and the differences from upstream." />
</svelte:head>

<h1>Install and migrate</h1>
<Markdown {source} />

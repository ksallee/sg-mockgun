<script>
	import Head from '$lib/Head.svelte';
	import { api3, coverage, docs, repo } from '$lib/site.js';

	const install = 'pip install sg-mockgun';

	const quickStart = `from sg_mockgun import Shotgun, schemas

Shotgun.set_schema_paths(*schemas.paths())
sg = Shotgun("https://mock.example.com", script_name="x", api_key="y")
sg.create("Project", {"name": "Demo"})`;

	const swap = `# from shotgun_api3.lib import mockgun
import sg_mockgun as mockgun`;

	const fixture = `def test_publish(sg):
    sg.load("tests/seed.json")
    sg.create("Version", {"code": "v001", "entity": {"type": "Shot", "id": 1001}})`;
</script>

<svelte:head>
	<Head title="sg-mockgun: a Flow Production Tracking mock that answers as a live site" description="sg-mockgun replaces shotgun_api3.lib.mockgun with an in-memory Flow Production Tracking mock that answers as a live site answers over api3." />
</svelte:head>

<!-- 1. Hero -->
<section class="hero">
	<div class="page">
		<p class="mono-label">Python 3.9 to 3.14. BSD-3-Clause.</p>
		<h1>A Flow Production Tracking mock that answers as a live site.</h1>
		<p class="lede">
			sg-mockgun replaces <code>shotgun_api3.lib.mockgun</code> with an in-memory mock that answers
			as a live site answers over api3.
		</p>
		<div class="actions">
			<a class="button" href="#install">Install</a>
			<a class="button quiet" href="/docs/">Read the docs</a>
		</div>
	</div>
</section>

<!-- 2. Install and quick start -->
<section class="band" id="install">
	<div class="page two">
		<div>
			<h2>Install</h2>
			<p class="lede">Requires Python 3.9 and <code>shotgun-api3</code> 3.10.5.</p>
			<pre><code>{install}</code></pre>
			<h3>Switch from upstream mockgun</h3>
			<pre><code>{swap}</code></pre>
			<p><a href="/docs/migrate/">Differences from upstream</a></p>
		</div>
		<div>
			<h2>Quick start</h2>
			<p class="lede">The bundled schema is a Flow PT 8.91 site's: 95 entity types, 1471 fields.</p>
			<pre><code>{quickStart}</code></pre>
			<h3>In pytest</h3>
			<pre><code>{fixture}</code></pre>
			<p><a href="/docs/pytest/">Testing with pytest</a></p>
		</div>
	</div>
</section>

<!-- 3. How behaviour is measured -->
<section class="band" id="measured">
	<div class="page">
		<h2>How behaviour is measured</h2>
		<ol class="steps">
			<li>A probe asks a live Flow PT 8.91 site one question over api3.</li>
			<li>The answer is recorded in <a href="{api3}/README.md" rel="external"><code>docs/api3/</code></a>, with ids and names replaced by placeholders.</li>
			<li>The mock code and its test cite the answer: <code># api3 030</code>.</li>
			<li>REST rules come from the <a href="https://github.com/ksallee/sg-groundtruth" rel="external">sg-groundtruth</a> corpus, cited as <code># finding NNN</code>.</li>
		</ol>
		<ul class="facts">
			<li>Upstream mockgun's test suite passes on sg-mockgun.</li>
			<li>tk-core's test suite passes on sg-mockgun, with the event log off and on.</li>
			<li>CI runs on Python 3.9 to 3.14, on Linux, macOS and Windows.</li>
			<li>Per-call results are in the <a href={coverage} rel="external">coverage table</a>.</li>
		</ul>
	</div>
</section>

<!-- 4. Docs -->
<section class="band" id="docs">
	<div class="page">
		<h2>Docs</h2>
		<ul class="cards">
			{#each docs as doc (doc.slug)}
				<li>
					<a href="/docs/{doc.slug}/">
						<span class="title">{doc.title}</span>
						<span class="blurb">{doc.blurb}</span>
					</a>
				</li>
			{/each}
		</ul>
		<p class="more"><a href={repo} rel="external">Source on GitHub</a></p>
	</div>
</section>

<style>
	.hero {
		padding-block: clamp(4rem, 10vw, 8rem) var(--band);
	}

	.hero h1 {
		margin: 1rem 0 1.25rem;
		max-width: 18ch;
	}

	.hero .lede {
		font-size: 1.1875rem;
		max-width: 52ch;
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-top: 2rem;
	}

	.two {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 4rem);
	}

	h2 {
		margin-bottom: 1rem;
	}

	h3 {
		margin: 2rem 0 0.75rem;
	}

	.steps,
	.facts {
		margin-top: 1.5rem;
	}

	.facts {
		color: var(--muted);
	}

	.cards {
		list-style: none;
		margin: 2rem 0 0;
		padding: 0;
		max-width: none;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1rem;
	}

	.cards li {
		margin: 0;
	}

	.cards a {
		display: grid;
		gap: 0.35rem;
		height: 100%;
		border: 1px solid var(--line);
		border-radius: var(--r);
		background: var(--surface);
		padding: 1.15rem 1.25rem;
		text-decoration: none;
		color: var(--ink);
		transition: border-color 0.2s var(--ease);
	}

	.cards a:hover {
		border-color: var(--muted);
	}

	.title {
		font-weight: 560;
		letter-spacing: -0.012em;
	}

	.blurb {
		color: var(--muted);
		font-size: 0.9375rem;
	}

	.more {
		margin-top: 2rem;
	}

	@media (max-width: 860px) {
		.two {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>

# Competitor Landscape: Consistent Characters and Multi-Step / Multi-Model Workflows (as of late Oct 2026)

Research date: 2026-10-29. Most sources are vendor docs, changelogs, vendor blogs and affiliate-style review sites. Where a claim is vendor-only or the sources conflict, it is flagged. Reddit threads didn't come up in search (two attempts), so the evidence on user complaints leans on Trustpilot and blogs.

## Q1. How does each platform define a character, how many models can use it, how is consistency enforced, and what does it cost?

### Takeaway
By late 2026, "save a character once, @mention it in any prompt" is table stakes. Kling, Runway, Google Flow, OpenArt, Mage, LTX and Higgsfield all ship some version of it. The approaches split into three families:
- **Reference-image "elements".** Zero training. Kling, Runway, Flow, OpenArt, Mage, LTX.
- **Fast per-person fine-tunes.** Higgsfield Soul ID, Leonardo, Civitai, SeaArt and Tensor LoRAs.
- **Video/voice-bound identities.** Kling 3.0 Omni video elements with voice, Hedra.

In every case the character is locked to one platform and usually to a subset of that platform's models. None of them exports a portable identity.

### Platform-by-platform summary (sub-heading for organization)

| Platform | How a character is defined | Which models can use it | How consistency is enforced | Price notes |
|---|---|---|---|---|
| Higgsfield Soul ID | Fine-tune on 20+ photos of one person (up to 80); trains in "a few minutes" | Soul image family; auto-appears as an Element in Seedance video; "connected tools" like Marketing Studio | Trained identity selected in a Character tab; one person per Soul ID; multi-char scenes use Elements | Training credit cost not stated in help center |
| Higgsfield Popcorn | Prompt + up to 4 reference images | Storyboard of up to 8 frames, which hand off as start frames to Kling/Veo | Single multi-frame generation holds identity, lighting, atmosphere | ~1.5 credits/image (3rd-party, checked Sep 3 2026) |
| Kling Elements (3.0 / Omni / O1) | Multi-image element (1 main + 1–3 extra angles), or 3–8 s video element; optional voice binding (5–30 s audio) | Video 3.0, 3.0 Omni, O1 Video, Image 3.0 Omni, Image O1 | @-reference or "Bind elements"; up to 3 elements bound to start/end frames; 7 refs per video gen (4 if video input); 10 per image gen | Creating elements free; AI multi-view 5 credits after 3 free/day; library cap 30–500 by tier |
| Runway References | Upload reference images, @-mention in prompt | Gen-4 / Gen-4.5 image & video; Seedream 5.0 takes up to 14 refs inside Runway | Reference conditioning; Act-Two transfers performance onto a character image (1 character/gen, ≤30 s) | Paid plans from $12/mo (3rd-party) |
| Google Flow "Ingredients" | Up to 3 ingredient images per prompt (characters, objects, settings); Nano Banana Pro images recommended | Veo 3.1 (earlier Veo 2 only) | Ingredients to Video; saved project assets @-mentioned (3rd-party) | Tier access conflicting across sources |
| OpenArt Characters | From description, 1 image, or multiple images; Character 2.0 needs 1 image | Nano Banana/Pro, Seedream 4.0/4.5 (Character 2.0); reused in video, Smart Shot, Story, Director | @Character in prompts; Multi-View 9-angle sheet; Smart Shot plans multi-shot with consistent chars | Commercial rights from $34 tier (3rd-party) |
| LTX Studio Elements | Character Element from up to 10 refs; Multi-Image Ref (Feb 25 2026); auto-extracted from script by Storyboard Generator | Image/storyboard; reportedly NOT supported in video-gen prompts | Saved Elements guide later generations | Standard plan or higher |
| Mage Characters | Single portrait upload, @charactername | Mango V2, Mango 3S, Cherry, Cherry Pro (video), Raspberry; not Blueberry 2 | Multi-Characters in one scene; Pear Motion Control drives locked character | Unlimited on Pro Plus $60/mo, Max $200/mo |
| Leonardo.ai | Custom LoRA from 10–20 images | Leonardo's own models | LoRA fine-tune | Apprentice $12 (1 training/mo), Artisan $30 (5), Maestro $60 (20) — 3rd-party |
| Civitai | LoRA trainer (SD1.5/SDXL/Flux) | Any compatible base on-site or downloadable | LoRA | ~500 Buzz (~$0.50) SD/SDXL; 2,000 Buzz Flux; membership $10–50/mo |
| SeaArt / Tensor.art | LoRA training (20–30 images); cloud ComfyUI-style workflows | On-site models; SeaArt up to 10 LoRAs at once | LoRA | Stamina/credits; details unverified |
| Hedra Character-3 | One image + audio | Character-3 only | Image-anchored talking-head generation | 6 Hedra credits/sec (3rd-party) |
| Freepik Spaces | "Character Reference" node feeding scene nodes | Whatever image/video nodes are wired | Graph wiring; no dedicated identity object documented | Free: 3 Spaces, limited credits |

### Cited Findings
**Higgsfield**
- Soul ID training uses 20+ photos (up to 80) and "takes a few minutes". One Soul ID holds one person; multi-character scenes use Elements. Results are "clearly the same person", not pixel-identical. The trained character is not exportable as a standalone file. Trained Soul characters appear automatically in Seedance's "My Elements". The help article was published 2026-08-01 and modified 2026-09-02. — [Higgsfield Help Center](https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-create-and-use-a-soul-id-character)
- An earlier third-party test described 10 photos (up to 70), which suggests the requirements were raised over time. — [302.AI on Medium](https://medium.com/@302.AI/higgsfield-soul-id-test-how-realistic-is-the-character-consistency-1bc8b3250bca)
- Higgsfield's own content claims a single reference anchors one generation but drifts across many. It positions Soul ID as most of a LoRA's consistency "with none of the pipeline", and it recommends Flux.2 fine-tuning for 20+ clip projects. — [Higgsfield blog](https://higgsfield.ai/blog/tools-for-consistent-ai-characters)
- Popcorn generates storyboards of up to 8 frames from a prompt plus up to 4 references, with consistent identity and lighting. It has Manual and Auto modes, and frames can be used as start frames for Kling or Veo. — [Higgsfield Help Center: Popcorn](https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-popcorn)
- A third-party review lists Popcorn at 1.5 credits/image (checked Sep 3, 2026) and a third "Instadump" mode, which the help center does not mention. — [GlobalGPT review](https://www.glbgpt.com/hub/higgsfield-popcorn-review/)

**Kling**
- The Element Library guide is dated Feb 5, 2026. Multi-image elements take 2–4 images. Video character elements take 3–8 s clips, and voice binding takes 5–30 s of audio.
  - Elements work in Video 3.0, 3.0 Omni, O1 Video, Image 3.0 Omni and Image O1.
  - Per-generation limits: up to 7 refs for video (4 if the input includes a video) and up to 10 for image.
  - Library caps by tier: 30 (non-member), 50 (Standard), 150 (Pro/Premier), 500 (Ultra).
  - Creating an element is free. AI multi-view completion costs 5 credits beyond 3 free uses/day.
  - Elements can't be shared to Explore.
  — [Kling Element Library guide](https://kling.ai/quickstart/klingai-element-library-3-user-guide)
- Kling's "Bind Subject" in Video 3.0 is pitched as keeping a character stable through camera moves. Third-party guides rank video elements above stills for recurring characters. — [Kling blog: subject binding](https://kling.ai/blog/kling-3-subject-binding-character-consistency); [Flick guide](https://flick.art/blog/kling-character-consistency)

**Runway**
- Changelog dates:
  - Gen-4 References launched Apr 30, 2025 and improved Jun 25, 2025.
  - Act-Two added full-body and hand tracking on Jul 17, 2025, and Voices on Aug 20, 2025.
  - Gen-4.5 launched Dec 11, 2025.
  - Seedream 5.0 inside Runway accepts up to 14 reference images (Jul 15, 2026).
  - Agent sessions can use Brand Kits and style references without re-uploading (Aug 11, 2026).
  - "Runway Characters" (Mar 9, 2026) are real-time conversational avatars, not a reusable identity for generation.
  — [Runway changelog](https://runway.com/changelog)
- Act-Two handles one character per generation and a maximum of 30 s. Multi-character dialogues are assembled from separate runs. — [Runway Help: Multi-Character Dialogues](https://help.runwayml.com/hc/en-us/articles/41748090660499-Creating-Multi-Character-Dialogues-with-Act-Two)

**Google Flow / Veo**
- Veo 3.1 "Ingredients to Video" keeps characters consistent across changing settings. Google recommends Nano Banana Pro images as ingredients. — [Google blog: Veo 3.1 Ingredients](https://blog.google/innovation-and-ai/technology/ai/veo-3-1-ingredients-to-video/); [CineD](https://www.cined.com/google-veo-3-1-ingredients-to-video-update-adds-native-vertical-format-4k-upscaling-and-enhanced-character-consistency/)
- Ingredients to Video came to Google Vids in Nov 2025. — [Workspace Updates, Nov 2025](https://workspaceupdates.googleblog.com/2025/11/google-vids-veo-ingredients-to-video.html)
- An earlier Google tips post said the feature worked only with Veo 2, which conflicts with the current Veo 3.1 support. Tier access also conflicts across sources: Ultra-only in an older review, free tier in a 2026 guide. — [Google Flow tips](https://blog.google/innovation-and-ai/products/flow-video-tips/); [TechNave](https://technave.com/gadget/How-to-get-consistent-characters-with-Google-Veo-3-and-Flow-43421.html)

**OpenArt**
- Characters (Beta) launched 2025-01-26, from a description, one image or several images. Multiple consistent characters per prompt arrived 2025-03-21.
- Character 2.0 (2025-12-24) needs one reference image, supports non-humans and works with Nano Banana/Pro and Seedream 4.0/4.5, with a vendor claim of "10x more consistency".
- OpenArt Suite (2026-02-23) lets users save characters, objects, backgrounds and styles and @-reference them.
- The page notes "this version of OpenArt is discontinued on November 1, 2026", with users moved to a new workspace.
— [OpenArt What's New](https://openart.ai/whats-new)
- A July 2026 review found stills consistent across locations, but image-to-video "considerably tougher". — [PicLumen review](https://www.piclumen.com/blog/openart-review/) (competitor-hosted; treat with caution)

**LTX Studio**
- Multi-Image Ref for Elements was announced Feb 25, 2026. — [Creators Toolbox on X](https://x.com/Creator_Toolbox/status/2026922567211380819)
- The Storyboard Generator now pulls characters and objects from a script and saves them as Elements. — [LTX blog](https://ltx.io/blog/ltx-storyboard-generator-update)
- Brand Kit is available for Enterprise customers (Feb 2026 release notes). — [LTX release notes](https://ltx.io/release-notes)
- One third-party guide says Elements take up to 10 refs, require Standard or higher, and are "not supported in video generation prompts" per LTX's help center. This is unverified against the primary source. — [fast.io](https://fast.io/resources/best-ai-character-generators-2026/)

**Mage (for baseline)**
- Characters launched in beta around Jan 2026: one reference image, initially Mango V2 only. — [mage.space on X](https://x.com/MageSpace_/status/2011147780694110535)
- By May 22, 2026, Characters worked with Mango V2, Mango 3S, Cherry, Cherry Pro and Raspberry, but not Blueberry 2, which uses First & Last Frames instead.
  - Multi-Characters supports several locked characters per scene.
  - Pear Motion Control drives a character from a reference video.
  - Unlimited generations are on Pro Plus ($60/mo) and Max ($200/mo).
  — [Mage blog](https://blog.mage.space/article/best-ai-video-generators-consistent-characters-2026/9459a229-806d-4a73-8abf-a19db645a248)
- Mage's blog also references a Mage Agent (dated Sep 25, 2026) for characters, scenes and video, and a Video Character Swap app. — [Mage blog index](https://blog.mage.space/)

**Leonardo, Civitai, SeaArt, Tensor.art**
- Leonardo: Apprentice $12/mo with 1 LoRA training/month, Artisan $30 with 5, Maestro $60 with up to 20. Training needs 10–20 images. — [SmartRemoteGigs](https://smartremotegigs.com/software/leonardo-ai/)
- A third-party comparison rates Leonardo's consistent-character support "Limited". — [PhotoAI compare](https://photoai.com/compare/leonardo-ai-vs-civitai)
- Civitai training: ~500 Buzz for SD1.5/SDXL and 2,000 Buzz for Flux, at 1,000 Buzz ≈ $1.
  - A rebuilt Training Studio entered beta Sep 23, 2026.
  - The site has been inaccessible in Australia since Mar 16, 2026.
  - Its rules prohibit real-person likeness content.
  — [iimagined guide](https://iimagined.ai/blog/civitai-lora-training)
- Civitai membership runs $10–50/mo. — [aitrendtool](https://aitrendtool.com/tools/civitai)
- SeaArt: character LoRAs from 20–30 images, browser ComfyUI, up to 10 LoRAs at once. — [techtip.blog](https://techtip.blog/seaart-ai-review-2026-features-pricing-lora-guide/)
- Tensor.art: on-site LoRA training and a cloud node workflow. A claimed 2025 restriction on LoRA access is unverified. — [tooldirectory](https://tooldirectory.ai/compare/seaart-ai-digital-art-creation-vs-tensor-art)

**Hedra and Pika**
- Hedra Character-3 turns one image plus audio into a talking or singing video. Reported specs: up to 10 min, 1080p in some sources and 720p in others, 6 credits/sec after the Avatar and Omnia models were folded in "on 29 July". — [Filmora](https://filmora.wondershare.com/video-editor-review/hedra-ai-review.html); [droidcrunch](https://droidcrunch.com/hedra-review/)
- Pika: reviewers report no lip-sync, with 2.5 focused on short creative clips and SFX. — [versely.studio](https://www.versely.studio/blog/best-ai-lip-sync-tools-2026-hedra-vs-sync-vs-heygen-comparison)

**Freepik Spaces**
- Spaces is a node canvas launched Nov 4, 2025. Inputs include "AI characters". Free users get 3 Spaces. — [Business Wire](https://www.businesswire.com/news/home/20251104023735/en/Freepik-Launches-Freepik-Spaces-to-Power-AI-Visual-Creation-and-Collaboration-in-Real-Time); [VP Land](https://www.vp-land.com/p/freepik-launches-ai-canvas-for-teams)
- A guide suggests a "Character Reference" node fanning out to several scene nodes. — [Chase Jarvis](https://chasejarvis.com/blog/freepik-spaces/)

### Inferences
- Reference-image elements (zero training, @-mention) are now the default UX everywhere. Training-based identity (Soul ID, LoRA) persists as a premium "higher fidelity" tier, mainly for real-person and influencer use cases.
- Identity is siloed by platform and often by model family. Mage's Characters skip Blueberry 2. Soul ID works in Soul and Seedance but isn't exportable. LTX Elements reportedly don't work in video prompts. Within-platform cross-model coverage is a selling point, and competitors list exactly which models support it.
- The frontier is moving from face-only identity toward identity bundles of face, outfit, voice and motion. Kling binds voice to Elements, Flow ties vocal identity to characters (3rd-party claim), and Runway Act-Two and Mage Pear Motion handle performance.
- Multi-view sheet generation (OpenArt Multi-View with 9 angles, Kling AI multi-view completion) is becoming a standard preprocessing step that turns one upload into a robust reference set.

### Gaps
- Leonardo's current character-reference feature (non-LoRA) wasn't found in a primary source.
- Pika's 2026 character features weren't researched in depth. Only "no lip-sync" was found.
- Exact credit costs for Soul ID training and Runway References weren't found in primary sources.
- Whether LTX Elements really don't work in video prompts remains unconfirmed against LTX's help center.
- Google Flow's current tier gating and the Flow Agent's character memory come from third-party sources only.

## Q2. What does workflow chaining look like (node canvas vs templates vs agent/chat), and how are failures, retries and cost surfaced?

### Takeaway
In 2025–2026 the market converged on a three-layer stack:
- **Node canvas** for power users: Runway Workflows (Oct 2025), Krea Nodes, Freepik Spaces (Nov 2025), Figma Weave/Weavy, Flora, fal Workflows, ComfyUI/Comfy Cloud, SeaArt/Tensor.
- **"Publish graph as App"** for end users: Krea Node App Builder (Dec 2025), Runway Apps (Dec 2025), Weavy app mode, Higgsfield apps/effects.
- **An agent that writes or runs the graph from chat**, the dominant 2026 trend: Krea Prompt-to-Workflow (Feb 2026) and Node Agent, Runway Agent (May 2026) with Workflows-in-Agent (Jul 2026), Glif 2.0 (Apr 2026), fal Agent (Aug 2026), Higgsfield Supercomputer (May/Jun 2026), OpenArt Director (Jun 2026), Google Flow Agent (~May 2026), Mage Agent (Sep 2026), ComfyUI agent (Oct 2026).

Pre-run cost estimates are emerging (Krea per-node breakdown, Runway Task Cost API). Failure and retry handling is thin: mostly auto-fixing bad graph connections and capacity fallbacks. Nobody documents quality-based retries.

### Cited Findings
**Runway**
- Workflows (node editor) launched Oct 24, 2025, with input, media-model and LLM nodes. It was initially limited to Creative Partners and Enterprise. — [AlternativeTo](https://alternativeto.net/news/2025/10/runway-launches-node-based-workflows-for-building-custom-ai-creative-pipelines/); [Runway changelog](https://runway.com/changelog)
- Changelog dates:
  - Audio and upscaling nodes: Nov 21, 2025.
  - Workflows publishable as Apps: Dec 4, 2025.
  - Runway Agent launched: May 13, 2026.
  - Agent Skills (multi-step tasks from a single command): Jul 2, 2026.
  - Agent builds and runs full Workflows from plain language: Jul 23, 2026.
  - Compositing nodes: Aug 18, 2026.
  - MCP agents can list, edit and run workflows: Aug 20, 2026.
  - Seedance 2.5 Draft mode (cheap 480p drafts) in Agent: Oct 2, 2026.
  - App Studio builds hosted apps from plain language: Oct 26, 2026.
  — [Runway changelog](https://runway.com/changelog)
- Cost, failure and routing items in the changelog:
  - Model Routers pick the video model by cost, latency or quality: Jul 21, 2026.
  - Opt-in capacity fallbacks route to another model instead of queuing: Jul 30, 2026.
  - Task Cost API returns estimated and final credit cost per task: Jul 30, 2026.
  - Routing history in the dev portal: Aug 3, 2026.
  - Enterprise project credit caps that pause generation: Oct 9, 2026.
  - There are no entries on retries or general failure handling beyond the routing fallbacks.
  — [Runway changelog](https://runway.com/changelog)
- Third-party coverage says LLM nodes cost 3–4 credits per execution. Early users report agent-generated graphs are harder to debug than hand-built ones. — [AlphaSignal](https://alphasignal.ai/news/runway-agent-builds-entire-ai-video-pipelines-from-plain-language)

**Krea**
- Nodes covers image, video, edit, enhance, 3D, motion transfer, lipsync, audio and utility nodes, with up to 10 outgoing connections per node. Models rotate quarterly. Docs were updated Apr 13, 2026.
  - The App Builder exposes chosen params as a form, supports public or private apps, and has an API endpoint to execute a Node App.
  - The Node Agent proposes a multi-stage plan, lets users swap models or drop stages before approval, auto-fixes missing params and incompatible connections, and **shows a per-node cost breakdown before anything runs**. Later edits rerun only downstream nodes.
  - Plans: Pro (~$30/mo), and Max ($105/mo, 60k compute units, unlimited concurrency).
  — [Krea Nodes docs](https://www.krea.ai/docs/user-guide/features/nodes)
- Prompt-to-Workflow launched Feb 10, 2026. — [Krea on X](https://x.com/krea_ai/status/2021249046049182024); [Krea blog](https://www.krea.ai/blog/prompt-to-workflow)
- Node App Builder: Dec 3, 2025. — [Launch Archive](https://launcharchive.ai/launches/krea-launches-prompt-to-workflow-in-krea-nodes--x_2021249046049182024)
- The Krea Agents beta (waitlist) orchestrates 60+ models. Its launch date is unconfirmed. — [AlphaSignal](https://alphasignal.ai/news/krea-agents-opens-beta-to-replace-node-wiring-with-plain-english-prompts)

**Other node canvases**
- Figma acquired Weavy (Tel Aviv) on Oct 30, 2025, reportedly valued at more than $200M, and is rebranding it as Figma Weave, a node canvas with a dozen-plus third-party models. — [TechCrunch](https://techcrunch.com/2025/10/30/figma-acquires-ai-powered-media-generation-company-weavy); [SiliconANGLE](https://siliconangle.com/2025/10/30/figma-acquires-ai-design-startup-weavy-reported-200m/)
- Weave/Weavy has an "app mode" that publishes a graph as a simplified UI and runs on fal's model library. It is said to have no stable public API. Flora focuses on real-time multi-user editing, version history and "Flows" templates, with API access on Enterprise. fal Workflows is API-first, combining an editor, a playground and API calls in one view. — [Chase Jarvis](https://chasejarvis.com/blog/best-generative-ai-canvas-apps/); [flux-1.ai](https://flux-1.ai/weavy-vs-flora-ai-for-api-access/); [Krea blog: fal vs Flora](https://www.krea.ai/blog/fal-vs-flora) (vendor-authored comparisons)
- fal Agent launched Aug 13, 2026 to orchestrate image, video and 3D workflows (details "not yet officially confirmed" per the reporting outlet). A workflow marketplace is reported from Sep 2026. — [TechnoSports](https://technosports.co.in/fal-agent-orchestrate-image-video/); [Sacra](https://sacra.com/c/fal-ai/)
- Replicate is positioned as 50k+ community models with dedicated Deployments. No 2026 "pipelines" launch was found. — [DEV benchmark](https://dev.to/artem_varganich/falai-vs-replicate-vs-together-ai-serverless-generative-media-llm-inference-benchmark-2026-4gcm)

**Comfy Cloud / ComfyUI**
- Comfy Cloud is billed on active GPU time only. Idle editing time is free.
  - Standard $20/mo ($16 yearly), Creator $35, Pro $100. Credits: 4,200 / 7,400 / 21,100.
  - Team pricing conflicts ($200 vs $700/mo).
  — [Comfy pricing](https://comfy.org/pricing/); [Scopeful](https://www.scopeful.org/tools/comfyui-cloud)
- ComfyUI got an AI assistant/agent for building workflows (Oct 9, 2026). — [Digital Production](https://digitalproduction.com/2026/10/09/comfy-agent-ai-comfyui-workflows/)

**Freepik Spaces**
- Infinite canvas with upload, prompt, image/video generation and Magnific upscale nodes. Designed for team collaboration, launched Nov 4, 2025. — [VP Land](https://www.vp-land.com/p/freepik-launches-ai-canvas-for-teams); [Forbes](https://www.forbes.com/sites/ronschmelzer/2025/11/04/freepiks-spaces-makes-ai-a-team-sport-for-creators/)

**Agent / story products**
- Glif relaunched as a single agent, with Glif 2.0 on Apr 23, 2026. It plans and runs steps across 100+ models, and its launch videos were made with Kling o3, GPT Image 2 and ElevenLabs. — [Glif changelog](https://glif.app/changelog/2026-04-23-glif-v2-launch)
- Higgsfield Supercomputer:
  - Original version (~May 13, 2026): a cloud agent on the Hermes Agent framework, with 40+ tools, Slack/Figma/Drive/Notion integrations, 3 memory layers and Telegram access.
  - Supercomputer 2.0 (Jun 19 or 24, 2026; sources conflict): an autonomous marketing agent built with NVIDIA, on Team and Enterprise plans.
  - Projects added Aug 23, 2026 and a Blender add-on Aug 25, 2026.
  — [The Next Web](https://thenextweb.com/news/higgsfield-supercomputer-enterprise-marketing-nvidia); [aiclaudius](https://aiclaudius.com/article/higgsfield-supercomputer-self-learning-agent-may-2026); [explainx](https://explainx.ai/blog/higgsfield-supercomputer-2-enterprise-marketing-agent-nvidia-2026)
- OpenArt's chat and story products:
  - One-Click Story (2025-07-15): idea, script or character into a ~1-min video.
  - Smart Shot (2026-04-24): builds a shot plan, then a multi-shot video with consistent characters.
  - Director (2026-06-21/23): direct videos via chat. Cheaper "Lite" qualities came 2026-06-29.
  — [OpenArt What's New](https://openart.ai/whats-new)
- Google Flow reportedly added a Gemini-powered Flow Agent with project memory around I/O, May 2026 (third-party). — [aiflowmatrix](https://aiflowmatrix.com/google-flow-explained/); [vidau](https://www.vidau.ai/google-flow-ai-update-2026-complete-guide/)
- ElevenLabs 2026 releases: Studio 4.0 (video/audio editor, Sep 21), Image and Video APIs (Sep 26), Eleven v4 (Sep 28), ElevenAgents Architect (Oct 6). No "Captions video agent" was confirmed. — [ScriptByAI timeline](https://www.scriptbyai.com/elevenlabs-timeline/)
- The ElevenLabs Studio Agent launch is dated May 7, 2026. — [doomers.ai](https://doomers.ai/launches/elevenlabs-studio-agent)
- Short-drama generators (invideo, revid, Anijam, SceneMixer and others) use a script breakdown → series bible / character sheets → storyboard → routing to Veo, Kling or Seedance pipeline.
  - Reviewers warn costume consistency across many episodes works only if it is in the reference, not the prompt.
  - Many tools output clips that still need timeline assembly.
  — [ScreenWeaver](https://www.screenweaver.ai/blog/ai-short-drama-generator); [revid](https://www.revid.ai/tools/ai-short-drama-generator)

### Inferences
- "Agent that builds an editable node graph" is the 2026 consensus pattern. Krea, Runway and ComfyUI all keep the graph inspectable rather than a black box, so a side project shouldn't compete on "chat → video" alone.
- Cost transparency is becoming a differentiator. Krea shows per-node cost pre-run, Runway has a Task Cost API and credit caps, and Runway and OpenArt offer cheap draft modes. Draft-then-finalize (480p preview, then full render) is an emerging norm.
- Failure handling is still mostly infrastructure-level: capacity fallbacks, routing, auto-fixed connections. No platform documents output-quality checks (e.g., "identity drift detected, re-roll this shot") inside a workflow.
- Most consumer platforms are pivoting their agents toward marketing and enterprise (Higgsfield Supercomputer 2.0, Runway Agent 2.0 campaigns, Brand Kits), leaving prosumer storytellers somewhat under-served by agent features.

### Gaps
- Pika, Hedra, Leonardo and Civitai workflow and agent features (e.g., Leonardo Flow State/Blueprints) weren't researched.
- Higgsfield's consumer "apps/effects" catalog and Higgsfield Canvas weren't documented from primary sources.
- Retry semantics (e.g., whether failed generations refund credits) weren't found for any platform.
- Katalist and Captions weren't covered.

## Q3. What do users complain about, and what's trending in 2026?

### Takeaway
Recurring complaints:
- Identity drift across many clips, especially image-to-video and accumulated drift over a series.
- Credit burn from re-rolling.
- "Unlimited" plans that are restricted or throttled.
- Slow queues.
- Non-rolling credits and refunds.

Trends:
- Agents that write graphs.
- Video elements plus voice binding.
- Draft modes.
- Multi-model routing.
- Temporary "unlimited model X" promos as a growth tactic.

### Cited Findings
- **Higgsfield (Trustpilot):**
  - Unlimited perks apply only on higgsfield.ai, not in MCP, Supercomputer or CLI. Higgsfield's own notice confirms Unlimited mode isn't planned for those tools.
  - Generations stall for hours or days (one over 12 hours), and Ultra's unlimited Seedance took a day for 3 scenes.
  - Credits don't roll over, and refunds are denied.
  - Rating ~4.0/5 across 4,224 reviews with 19% one-star (as of Sep 8, 2026, per a third party). Counts vary by Trustpilot page.
  — [Trustpilot](https://www.trustpilot.com/review/higgsfield.ai); [aifunnelinsider](https://aifunnelinsider.com/higgsfield-ai-review-2026/); [Ima Studio](https://imastudio.com/blog/higgsfield-unlimited-explained)
- The most negative Higgsfield sources come from a competitor's blog and an anti-Higgsfield site, so they are biased. — [RepublicLabs blog](https://blog.republiclabs.ai/2026/02/the-downfall-of-higgsfield-ai-exposing.html); [higgsfieldscammedme.com](https://higgsfieldscammedme.com/)
- **Drift:**
  - Most text-to-video models generate each clip in isolation with no memory of prior shots. Paraphrased descriptions ("black" vs "dark" jacket) trigger drift. — [Medium / James Palm](https://james-palm.medium.com/how-to-keep-your-character-consistent-across-5-different-ai-video-clips-the-2026-guide-nobodys-bd39a5234ecf); [Magic Hour](https://magichour.ai/blog/how-to-keep-characters-consistent-in-ai-video)
  - Subtle shifts accumulate across dozens of videos. — [DEV Community](https://dev.to/weizhang_dev/the-character-consistency-problem-why-every-ai-video-tool-still-fails-at-the-one-thing-that-3386)
  - Contradicting this, a mid-2026 recap claims drift "stopped being a complaint" by May 2026. That is a vendor blog claim. — [Genra](https://genra.ai/blog/ai-video-six-shifts-mid-2026)
- **Credit burn:** the re-roll cycle of spend, near-miss, tweak, spend. One creator reported $60 wasted in two weeks of testing. — [aivideos.eu](https://aivideos.eu/blog/stop-wasting-ai-video-credits)
- **Kling and Runway downsides (per Mage's blog):** Runway has strict moderation and costly credit-based iteration. Kling has regional and tier moderation and per-generation costs. — [Mage blog](https://blog.mage.space/article/best-ai-video-generators-consistent-characters-2026/9459a229-806d-4a73-8abf-a19db645a248)
- **Act-Two constraints:** the face must stay visible, framing no wider than waist-up, and there is a tradeoff between expression intensity and consistency. — [fuser.studio](https://fuser.studio/articles/runway-act-two-guide)
- **Unlimited promos:** OpenArt runs rolling time-boxed unlimited promos (Seedance 2.5, Wan 3.0, FLUX 3, Aug–Oct 2026), a sign that "unlimited" is a competitive lever against Mage's unlimited positioning. — [OpenArt What's New](https://openart.ai/whats-new)
- **Model churn:** Krea rotates models quarterly. Seedance 2.5, Kling 3.0/o3, Veo 3.1, Nano Banana Pro/2, GPT Image 2, Seedream 5.0 and FLUX 3 are the 2026 headline models across platforms. — [Krea docs](https://www.krea.ai/docs/user-guide/features/nodes); [Runway changelog](https://runway.com/changelog); [Glif changelog](https://glif.app/changelog/2026-04-23-glif-v2-launch)

### Inferences
- Users' real pain is the *cost of verifying consistency*: re-rolls and manual eyeballing, not the absence of a character feature.
- "Unlimited" plans create trust problems when throttled or limited to the web, an opening for transparent quota and queue ETA displays.
- Model churn every quarter makes any workflow or character tied to one model fragile, which argues for model-agnostic identity and workflow definitions.

### Gaps
- No first-hand Reddit threads (r/StableDiffusion, r/aivideo, r/comfyui) were retrieved. The complaint evidence is skewed toward Trustpilot and blogs.
- No quantitative drift-rate comparison between platforms was found.

## Q4. Where are the clear gaps a side project could fill?

### Takeaway
No platform found offers:
- (1) Automatic identity-consistency scoring, such as an ArcFace-style face-similarity check per shot, surfaced to users or used to auto-retry.
- (2) A/B or eval testing of workflows across models.
- (3) A portable, cross-platform character definition (Soul ID is explicitly non-exportable, Kling elements can't be shared).
- (4) Quality-aware retries in workflows.

The research tooling for (1) exists and is open: VBench-2.0, the Face Consistency Benchmark and FaceSim-Arc.

### Cited Findings
- Soul ID "isn't exportable as a standalone file". — [Higgsfield Help Center](https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-create-and-use-a-soul-id-character)
- Kling elements can't be shared to Explore, and library size is capped by tier. — [Kling guide](https://kling.ai/quickstart/klingai-element-library-3-user-guide)
- Runway's changelog covers routing fallbacks, cost estimates and credit caps, but no retries or quality checks. — [Runway changelog](https://runway.com/changelog)
- The Krea Node Agent auto-fixes connection and parameter errors and shows pre-run cost. No output-quality validation is documented. — [Krea docs](https://www.krea.ai/docs/user-guide/features/nodes)
- **Open identity metrics:**
  - VBench-2.0 scores identity with RetinaFace detection plus ArcFace embeddings across frames (single-person scenes). — [VBench-2.0](https://arxiv.org/html/2503.21755v1)
  - The Face Consistency Benchmark (FCB) uses ArcFace, VGG-Face, Facenet, SFace and GhostFaceNet via DeepFace, with reference-based and reference-free modes. — [FCB arXiv 2505.11425](https://arxiv.org/pdf/2505.11425)
  - FaceSim-Arc is the cosine similarity of ArcFace embeddings between reference and generated frames. — [Concat-ID](https://arxiv.org/pdf/2503.14151); [Proteus-ID](https://arxiv.org/pdf/2506.23729)
- Only one hands-on Soul ID review was found, with no detailed consistency benchmark. Claims of "best" tool are marketing. — [302.AI on Medium](https://medium.com/@302.AI/higgsfield-soul-id-test-how-realistic-is-the-character-consistency-1bc8b3250bca)
- Saved references "cannot guarantee perfect consistency" (LTX review). — [Luma's LTX review](https://lumalabs.ai/news/ltx-studio-review)
- Short-drama tools often produce clips that still need assembly, and costume consistency depends on references. — [ScreenWeaver](https://www.screenweaver.ai/blog/ai-short-drama-generator)

### Inferences (candidate side-project wedges)
1. **Identity QA layer.** Score every generated shot against the character's reference set (face embedding similarity, plus optional outfit and CLIP similarity). Flag drift, auto-re-roll below a threshold, and show a per-character "consistency score" across a storyboard. No consumer platform surfaces this today. *Strongest gap.*
2. **Cross-model character portability.** A canonical "character pack" (multi-view sheet, description, voice sample, optional LoRA) that compiles into each model's native input: Kling element, Veo ingredients, Runway reference, Seedance element. This would let users move characters across platforms and survive quarterly model churn.
3. **Workflow A/B / eval harness.** Run the same storyboard through 2–3 model routes and compare identity score, cost and latency side by side. Runway's Model Router optimizes cost and latency but not *identity fidelity*, and nobody exposes comparative evals to creators.
4. **Cost-before-commit plus draft-then-final for whole storyboards.** Krea shows per-node cost and Runway has draft modes, but an end-to-end "this 12-shot episode will cost X; preview at 480p first" planner with consistency gating is not standard.
5. **Avoid:** a generic node canvas or a generic chat-to-video agent. Both are crowded (Runway, Krea, Freepik, Figma Weave, Flora, fal, Comfy, Glif, Higgsfield, OpenArt, Flow) and well-funded.
6. **Mage-specific angle:** Mage's Characters cover most but not all of its models (not Blueberry 2), and its pitch is unlimited generations. That makes an automatic consistency scorer plus auto-re-roll especially attractive, since re-rolls cost the user nothing on unlimited tiers. This is an inference, not a validated finding.

### Gaps
- It's not confirmed that no platform has hidden internal identity scoring. Absence is inferred from public docs and changelogs only.
- Licensing and ToS constraints on face-embedding scoring of real people (e.g., Civitai's real-likeness ban) weren't researched.
- No data was found on willingness to pay for QA/eval tooling among prosumer creators.

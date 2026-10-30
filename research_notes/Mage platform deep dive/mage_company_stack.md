# Mage (mage.space / Ollano, Inc.): company, team, funding, growth, and infra stack

Research date: 2026-10-29. Every claim is dated where the source gives a date. "Mage" here always means mage.space (Ollano, Inc., NYC). It is NOT Mage.ai (Tommy Dang's data-pipeline startup, which raised a $6.3M seed led by Gradient Ventures in 2021). Several aggregators mix the two companies up; see the funding section.

## Who are the founders and CEO? Backgrounds, prior companies, and public statements

### Takeaway
Mage has two co-founders. Roi Lee is CEO and handles business, fundraising, and the investor network. Gregory "Greg" Hunkins is CTO and the technical founder: he posts on HN as "hunkins", calls himself "the creator", and writes the engineering job posts. Both previously worked together under Ollano, an earlier company. Neither has done long-form interviews or podcasts that I could find. Most of their public statements are HN comments, LinkedIn hiring posts, and quotes in a 2023 404 Media article.

### Cited Findings
**Roi Lee (Co-founder & CEO)**
- CB Insights lists Roi Lee as current Founder and CEO of mage.space — [CB Insights people page](https://www.cbinsights.com/company/magespace/people) (via search snippet)
- Caplight lists "Roi Lee, Co-founder & CEO" and "Gregory Hunkins, Co-Founder & CTO" — [Caplight](https://www.caplight.com/company/mage-space)
- An AeroLeads profile lists him as Co-Founder & CEO at Mage from Sep 2022 to present, and previously Co-Founder & CEO at Ollano. The Mage entry is described as a "consumer platform to create and share AI content", NYC area — [AeroLeads](https://aeroleads.com/in/roilee) (search snippet only; page returned 403)
- LinkedIn (logged-out view): NYC area, about 3K followers. Education: Boston University Questrom School of Business, 2008–2012 — [LinkedIn: Roi Lee](https://www.linkedin.com/in/roilee)
- Earlier background, per an unsourced wiki: he built an online eco-fashion company and co-founded Angela Roi, a vegan luxury accessories brand. Ollano was described as a visual search and discovery platform for fashion — [Miraheze AI wiki](https://ai.miraheze.org/wiki/Mage.space); same claim in [search snippet citing Crunchbase/ZoomInfo/wiki](https://www.crunchbase.com/organization/mage-4eb2)
- His LinkedIn activity shows close ties to GFR Fund. He reposted GFR's Mage profile about two years ago. That profile said Mage was founded in 2022, focused on "AI enthusiasts making fantasy content with fine-tuned models and LoRAs", and grew through community building. He also appeared at GFR's fourth LP summit in Tokyo (about October 2026), was featured in GFR's Consumer AI Report (about February 2026), and has hosted GFR NYC office hours and a Korean startup ecosystem lunch at NY Tech Week — [LinkedIn: Roi Lee](https://www.linkedin.com/in/roilee)
- The GFR Consumer AI Report he appeared in names speed, cost, and infrastructure maturity as the main constraints, and says open- vs closed-source models are shaping images, video, and avatars — [LinkedIn: Roi Lee (activity summary)](https://www.linkedin.com/in/roilee)
- In the 2023 NSFW controversy he was quoted saying "We deeply value freedom of expression" and that Mage had "implemented active detection technology" — [404 Media, 2023-09-14](https://www.404media.co/mage-space-new-restrictions-non-consensual-porn-celebrities/)

**Gregory Hunkins (Co-founder & CTO)**
- LinkedIn: current company Mage (NYC). University of Rochester, 2017–2018, Machine Learning & AI (graduate year), plus 2013–2017 undergrad (likely Rochester). Former TA at Rochester. Eagle Scout. About section: "Just do it." One recommendation calls him "one of the most talented ML engineers" the writer has worked with — [LinkedIn: Gregory Hunkins](https://www.linkedin.com/in/gregoryhunkins)
- An unsourced wiki says he was previously an AI developer at Lifion by ADP and had experience at Applecart — [Miraheze AI wiki](https://ai.miraheze.org/wiki/Mage.space)
- HN user "hunkins" identifies as "the creator" of mage.space (2022-09-17). He posted Show HNs: "Mage: Create Anything. Yes Anything." (2022-09-17), "Show HN: Mage, Unlimited 50 Top AI Text-to-Image and GIF Models" (2023-04-20), "Model Creators Program: Mage Announces AI Creators Revenue Sharing" (2023-03-18), "Unlimited Stable Diffusion Models" (2023-10-23), and "Free and Unlimited Flux Is Live on Mage" (2024-08-03) — [HN Algolia search](https://hn.algolia.com/api/v1/search?query=mage.space&tags=(story,comment)&hitsPerPage=40)
- On HN (2023-05-23) he called himself a biased NYC founder. He praised Manhattan and Brooklyn talent and pushed back on the idea that you must build in SF — [HN Algolia, hunkins comments](https://hn.algolia.com/api/v1/search?query=mage&tags=comment,author_hunkins&hitsPerPage=50)
- In 2023 he told 404 Media "We're a team of two." He contrasted Mage with Leonardo AI's 20–30 person team and said "None of these technologies are going to be perfect" (about abuse detection) — [404 Media, 2023-09-14](https://www.404media.co/mage-space-new-restrictions-non-consensual-porn-celebrities/)
- His LinkedIn reactions include Redpoint's post on Modal's $750M Series D (which says Modal has passed $1B run-rate) and Cognition's SWE-2 launch on Modal sandboxes — [LinkedIn: Gregory Hunkins](https://www.linkedin.com/in/gregoryhunkins)

**Product strategy, from public company material (2026)**
- Homepage (fetched 2026-10-29) positions Mage around:
  - Consistent characters: upload one reference image, then use the character by its @handle across image and video
  - Motion Control
  - In-house "fruit" model families: Mango 3, Cherry 2 Pro, Guava 2 Pro, Lemon, Kiwi, Blueberry, Raspberry, Berry, Melon, Plum, SDXL Plus
  - About 20 third-party models: Nano Banana 2, GPT Image 2, Grok Image/Video, Flux 2, Krea 2, Wan 2.2, LTX, HiDream, Chroma, Z-Image, SD 1.5/XL/3.5, Seed Audio, Eleven Speech/Music
  - 19 "Mage Apps" (Face Swap, Lipsync, Scene Builder, Character Sheet, Relight, etc.)
  - Private-by-default creations, commercial-use rights, and a developer API, SDKs, and MCP server
  - [mage.space homepage](https://www.mage.space/)
- LinkedIn company "About" (2026) describes Mage as "many frontier models in one place" with its own model families, a developer API, ComfyUI nodes, and an MCP server for Claude/ChatGPT — [LinkedIn: Mage](https://www.linkedin.com/company/magespace)

### Inferences
- Hunkins is almost certainly the hiring manager or technical interviewer for an AI Infrastructure role. He wrote both the 2025 ML Engineer post and the 2026 AI Infra post. The ML-heavy background (Rochester ML master's, ex-ADP Lifion AI dev) suggests he built the original GPU backend himself.
- Lee's network runs through GFR Fund (Japan/US consumer, gaming, and genAI VC), Korean-American founder circles, and NY Tech Week. Expect business conversations framed around consumer growth and profitability rather than enterprise.
- Strategy has moved from "unlimited free Stable Diffusion" (2022) to a community model hub with LoRAs and creator rev-share (2023), then to a multi-model aggregator with proprietary fine-tuned "fruit" families, character consistency, and video (2024–25), and now to a developer API, MCP, and agent skills (2026). The last step means the inference platform now serves external API customers as well as the consumer app.
- The fruit-named "exclusive" models are most plausibly fine-tunes or LoRA-merged checkpoints on open-weight bases (SDXL, Flux, Wan, Hunyuan, etc.) rather than models trained from scratch. This is inference: no source states their bases.

### Gaps
- No podcasts, long-form interviews, or conference talks by either founder were found.
- X/Twitter accounts for the founders and @magespace were not reviewed. The homepage links an X profile, but its handle and content were not checked.
- Roi Lee's Ollano and Angela Roi history comes only from an unsourced wiki and aggregator snippets.
- Hunkins' ADP/Applecart history is from the same unsourced wiki. His LinkedIn view did not show job titles.

## Team size, notable engineers, and hiring posts

### Takeaway
Mage is tiny. It was "a team of two" in September 2023, and LinkedIn showed about 9 employees in October 2026. It hires for in-person NYC roles with high cash plus meaningful equity, and pitches itself as "pre-seed size with Series B revenue."

### Cited Findings
- 2023-09: "We're a team of two" (Hunkins) — [404 Media](https://www.404media.co/mage-space-new-restrictions-non-consensual-porn-celebrities/)
- 2026-10: LinkedIn company page shows the 2–10 band and "Discover all 9 employees". Founded 2022, HQ New York (10019), 125 followers — [LinkedIn: Mage](https://www.linkedin.com/company/magespace)
- Caplight lists 8 employees — [Caplight](https://www.caplight.com/company/mage-space)
- An unsourced wiki claims about 54 employees and about $7.2M revenue in 2024. This conflicts with LinkedIn and the 404 Media quote and is likely a scraped estimate — [Miraheze AI wiki](https://ai.miraheze.org/wiki/Mage.space)
- **HN "Who is hiring? (February 2025)", posted by hunkins on 2025-02-03 (summary, not verbatim):**
  - Role: "Mage.Space | Machine Learning Engineer | NYC | Full-time (In-Person)", $150K–$250K plus 0.50%–1% equity. Remote contract work also available.
  - Company: seed-stage with seven-figure ARR, shipping daily to millions of users.
  - Wants entrepreneurial hackers experienced with Diffusers, Torch, Transformers, vLLM, and Ray.
  - The engineer would own the ML backend on a "global distributed GPU cluster" serving "tens of thousands of base models and hundreds of thousands of auxiliary models", and integrate the latest open-source models.
  - [HN item 42920890](https://hn.algolia.com/api/v1/items/42920890)
- **LinkedIn post, about June 2026 ("4mo" before 2026-10-29), by Hunkins, reposted by Mage and Roi Lee:** hiring an AI Infrastructure Engineer. Claims: "Ship daily to 1.4MM MAU", about 30% month-over-month growth, profitable, "pre-seed size with Series B-level revenue and impact". Referral bonus offered. 28 reactions, 4 comments — [LinkedIn: Mage](https://www.linkedin.com/company/magespace); [LinkedIn: Gregory Hunkins](https://www.linkedin.com/in/gregoryhunkins); [LinkedIn: Roi Lee](https://www.linkedin.com/in/roilee)
- About 2025 (LinkedIn "1 year ago"): a Jeff Smith post listed Mage among startups hiring frontend and ML engineers for its genAI platform — [LinkedIn: Roi Lee](https://www.linkedin.com/in/roilee)
- The mage.space homepage has no careers link — [mage.space](https://www.mage.space/). /careers returned 404 — [mage.space/careers](https://www.mage.space/careers)

### Inferences
- With about 9 people and 1.4M MAU, an infra hire would likely be one of 2–4 engineers touching the GPU backend. Expect broad ownership: scheduling, model loading and caching, cost, reliability, and now the external API.
- The 2025 JD scale ("tens of thousands of base models, hundreds of thousands of auxiliary models", meaning user-imported checkpoints and LoRAs) points to a core infra problem of multi-tenant model and LoRA hot-swapping and weight caching across a GPU fleet, not serving a few fixed models.
- The 2025 JD comp ($150–250K plus 0.5–1% equity) is a reasonable anchor for a 2026 senior infra offer. The 2026 posting's comp was not visible.

### Gaps
- The full text of the 2026 "AI Infrastructure Engineer" or "Senior AI Infrastructure Engineer — Generative Model Platform" posting was not found on Ashby, Lever, Wellfound, or YC. Mage is not a YC company as far as I found.
- No named non-founder engineers were identified.
- I did not check whether Mage posted in later HN Who's Hiring threads (2025-03 onward).

## Funding, revenue, traffic, and growth signals

### Takeaway
Mage raised a small seed, about $2.8M, reported around late 2023 from consumer and gaming VCs (GFR Fund, Sfermion, Untapped Capital). Since then it says it is profitable and growing about 30% MoM, with seven-figure ARR as of February 2025. Semrush traffic roughly quadrupled from about 1M visits per month in late 2025 to about 4M in August–September 2026, which supports the growth claims.

### Cited Findings
- CB Insights: Seed stage, investors Untapped Capital, Sfermion, and GFR Fund. HQ New York. Lists "founded 2019", probably the Ollano entity date. Competitors include OpenArt, Wombo, Lexica, NightCafe, and Playground — [CB Insights](https://www.cbinsights.com/company/magespace)
- About $2.8M seed, reported November–December 2023 for a NYC "consumer platform for creating entertaining content using Generative AI", with investors including GFR Fund and Sfermion — [VCBacked snippet via search](https://www.vcbacked.co/company/mage); [TopReviewed](https://topreviewed.ai/companies/mage-space) (aggregator)
- **Conflation warning:** Caplight shows "$6.3M seed led by Gradient Ventures, Oct 2021" (Neo, GREE VR Capital, Essence VC, Xoogler, Worklife, Designer Fund). The Gradient-led $6.3M round matches Mage.ai, not mage.space. GREE VR Capital, GFR Fund's former name, appears in that list, so the record is mixed — [Caplight](https://www.caplight.com/company/mage-space). The VCBacked page fetched was a Turkish game-studio "Mage", also unrelated — [VCBacked](https://www.vcbacked.co/company/mage)
- GFR Fund is a SF-based consumer tech VC (gaming, genAI, creator economy), formerly GREE VR Capital. Fund III was $53.5M, closed 2024 — [ecosystem.fi / f4.fund snippets](https://f4.fund/firms/gfr-fund); [Road to VR](https://roadtovr.com/?p=167398). Sfermion is a Chicago NFT/metaverse fund — [Cointelegraph](https://regional-front.cointelegraph.com/news/sfermion-raises-100m-for-nft-and-metaverse-ventures)
- Revenue: "seven-figure ARR", seed-stage, "millions of users" (2025-02-03) — [HN item 42920890](https://hn.algolia.com/api/v1/items/42920890)
- Growth, profitability, and users: 1.4MM MAU, about 30% MoM, profitable (about June 2026) — [LinkedIn: Mage](https://www.linkedin.com/company/magespace)
- Homepage, self-reported (2026-10-29): "10M+ users", "1B+ creations", about 300K images and 30K videos per day — [mage.space](https://www.mage.space/)
- Historical MAU, from the unsourced wiki: over 300K MAU at end of 2022 and 1M MAU by May 2023 — [Miraheze AI wiki](https://ai.miraheze.org/wiki/Mage.space)
- Semrush, last updated 2026-10-13:
  - Visits: 3.36M (July 2026), 4.02M (August 2026), 4.06M (September 2026)
  - Top country US at 30% (66% mobile), then Germany 6.5%, UK 6.4%, India 5.3%, Bangladesh 3.6%
  - Avg visit 21:10, 7.22 pages/visit, bounce rate 34%
  - 78.8% direct traffic, zero paid search
  - Top next destinations: google.com and stripe.com
  - Listed competitors: raphael.app, flatai.org
  - [Semrush](https://www.semrush.com/website/mage.space/overview)
- Semrush, updated 2025-11-12: 925.5K visits (August 2025), 693K (September 2025), 970K (October 2025), with average session 10:15 — [Semrush snippet](https://cw.semrush.com/website/mage.space/overview)
- Pricing (2026-10): Free (300 sign-up Gems), Basic $10, Pro $30 ("most popular"), Pro Plus $60, Max $200 per month. Gems are the credit currency. The API is pay-per-generation in Gems — [mage.space](https://www.mage.space/)
- Payments are through Stripe (subscriptions managed via the Stripe Portal) — [mage.space/terms](https://www.mage.space/terms). Hunkins asked Stripe in 2023-05 to bring PayPal to US merchants, calling it the most-requested feature after the January 2023 premium launch — [HN Algolia, hunkins comments](https://hn.algolia.com/api/v1/search?query=mage&tags=comment,author_hunkins&hitsPerPage=50)

### Inferences
- Traffic grew about 4.2x year over year (October 2025 about 0.97M to September 2026 about 4.06M on Semrush). That fits sustained double-digit MoM growth through the first half of 2026. Growth looks flat from August to September 2026 (+1%), so "30% MoM" may describe revenue, or an earlier window.
- At $10–$200 per month with seven-figure ARR in early 2025 and about 30% MoM since, 2026 ARR could plausibly be high seven to low eight figures. That is speculative; there is no revenue figure for 2026.
- High direct-traffic share, long sessions, and Stripe as a top exit point point to a sticky, subscription-heavy consumer user base. That means latency and queue fairness across tiers matter commercially.
- I found no evidence of a priced round since 2023. "Profitable" suggests they are funding GPU spend from revenue, so cost per generation is likely a central infra metric.

### Gaps
- No Similarweb number was retrieved.
- No app store listing was confirmed. The wiki mentions an iOS app, but the homepage has no app links.
- No Crunchbase or PitchBook funding detail was retrieved (403).
- No confirmation of round size or date from a primary source such as an investor portfolio page or press release.

## Tech stack hints (inference, orchestration, infra)

### Takeaway
Public evidence shows a Python and PyTorch open-source ML stack on a "global distributed GPU cluster". It launched in 2022 on Banana.dev serverless A100s rather than self-managed Kubernetes. It serves tens of thousands of base models and hundreds of thousands of LoRAs and auxiliary models. Since 2026 it also offers an async-job public REST API (api.mage.space/v1), Python and TS SDKs, ComfyUI nodes, and an MCP server. I found no public confirmation of Modal, Cloud Run, GCS, FastAPI, or Redis. The CTO's LinkedIn activity shows interest in Modal, but that is not evidence they use it.

### Cited Findings
- 2022-09-17: Hunkins said he launched the Stable Diffusion app at mage.space on Banana (serverless GPU). He said serverless GPUs were much easier than a Kubernetes cluster with GPU node pools and cheaper than dedicated GPUs. The same day he cited about 5-second generations on A100s with unlimited generations — [HN Algolia, hunkins comments](https://hn.algolia.com/api/v1/search?query=mage&tags=comment,author_hunkins&hitsPerPage=50)
- 2023-07-25: launched Mage Animate based on AnimateDiff for 80+ SD models, with LoRA support coming — [HN Algolia, hunkins comments](https://hn.algolia.com/api/v1/search?query=mage&tags=comment,author_hunkins&hitsPerPage=50)
- 2023-10-23: "Unlimited Stable Diffusion Models" (user model import at /models/import). 2024-08-03: free and unlimited Flux — [HN Algolia search](https://hn.algolia.com/api/v1/search?query=mage.space&tags=(story,comment)&hitsPerPage=40)
- 2025-02 JD: Diffusers, Torch, Transformers, vLLM, Ray. ML backend on a "global distributed GPU cluster" with tens of thousands of base models and hundreds of thousands of auxiliary models — [HN item 42920890](https://hn.algolia.com/api/v1/items/42920890)
- Unsourced wiki: queue-based system with a free community queue and priority queues for paid tiers. ControlNet (Canny/Pose/Depth), inpainting, img2img, upscaling. Up to 5 stacked LoRAs on Pro Plus, custom model import on paid tiers, advanced Wan LoRA stacking on Max — [Miraheze AI wiki](https://ai.miraheze.org/wiki/Mage.space)
- **GitHub org [github.com/mage-space](https://github.com/mage-space)** (NYC; 6 repos, all updated October 2026; no public members):
  - mage-python: sync and asyncio SDK
  - mage-typescript: SDK
  - ComfyUI-Mage: ComfyUI nodes that run Mage models via the API without a local GPU
  - skills: agent skills for Claude, Codex, and Cursor via the Mage MCP server (product photoshoots, ads, UGC videos, thumbnails)
  - plugin-marketplace: a fork of xai-org's plugin marketplace, for submitting a Mage plugin
  - .github
  - [GitHub: mage-space](https://github.com/mage-space)
- **Public API**, per [docs.mage.space](https://docs.mage.space/api/overview):
  - Base `https://api.mage.space/v1`, with per-model endpoints such as `/v1/flux2/generate` and `/v1/mango/generate`
  - Bearer `MAGE_API_KEY` auth
  - Async submit returns `request_id`, `status` (e.g. `in_progress`), `status_url`, and `cancel_url`. Clients poll; the docs mention no webhooks
  - Responses include `architecture`, `model_id`, `billing` {mode: gems, gems_charged}, `result`, and `error`
  - SDKs send idempotency keys so retries don't double-charge
  - Inputs can be URLs, data URLs, or uploads. Inputs and results are retained for 30 days
  - Versioned API; docs hosted on Mintlify
- Developer surfaces: [mage.space/developers](https://www.mage.space/developers), [MCP](https://www.mage.space/developers/mcp), [model reference](https://www.mage.space/developers/models), and [skills](https://www.mage.space/skills) — [mage.space](https://www.mage.space/)
- Hunkins' LinkedIn reactions include Modal's Series D and Cognition on Modal sandboxes. Search snippets also tied his profile to a Merge Gateway announcement that adds Modal as a model vendor (2026-07-31), but the fetched profile did not show it — [LinkedIn: Gregory Hunkins](https://www.linkedin.com/in/gregoryhunkins); [Merge changelog 2026-07-31](https://www.merge.dev/changelog/july-31-2026-gateway)
- Searches for a Modal case study, blog, or tweet naming Mage or Ollano returned nothing. Modal's public inference page names customers such as Runway and Decagon, not Mage — [Modal inference](https://modal.com/products/inference)

### Inferences
- **Lineage:** they started on serverless GPU (Banana) because they did not want to run Kubernetes GPU node pools. That preference most likely carried over to another serverless or managed GPU platform, such as Modal, RunPod, Baseten, or multi-cloud spot. "Global distributed GPU cluster" suggests multi-region and possibly multi-provider capacity. The briefing's mention of Modal, Cloud Run, and GCS is plausible but not publicly confirmed; ask in the interview.
- **Model catalog problem:** tens of thousands of checkpoints and hundreds of thousands of LoRAs (2025) points to:
  - a model registry with lazy weight loading from object storage
  - local NVMe/RAM caching tiers
  - LoRA hot-swap and stacking on warm base-model workers
  - affinity routing (send a job to a worker that already has the base model loaded)
  - cold-start mitigation such as snapshots or preloaded images

  These are likely core interview topics.
- **Queues and tiers:** free-community vs priority-paid queues, Gems billing, async request_id/status_url polling, cancel, and idempotency keys imply a central job queue and state store (Redis or Postgres plausible but unconfirmed), per-tier admission control, and a billing ledger tied to job completion.
- **vLLM/Transformers in the JD** suggests LLM serving for prompt enhancement, the "Mage Assistant" chatbot, captioning, or safety classifiers. **Ray** suggests distributed batch or multi-GPU orchestration, for example video models like Wan or Hunyuan that need multi-GPU or sequence parallelism.
- **The 2026 API, MCP, and agent-skills push** (including an xAI plugin-marketplace fork) means the platform now has B2B and agent traffic. That brings SLAs, rate limits, idempotency, and per-key metering into the infra role's scope.
- **Mix of third-party and in-house models:** closed models (Nano Banana, GPT Image, Grok, Veo, Eleven) are probably proxied to provider APIs. Open-weight and "fruit" models are self-served on GPUs. So the orchestrator likely routes across both self-hosted workers and external APIs under one request schema (note the `architecture` field in API responses).
- **Safety:** after 2023 they added deepfake and celebrity-NSFW detection, so there is likely a moderation and classifier stage in the generation pipeline.

### Gaps
- No confirmation of the cloud provider, GPU vendor or platform after Banana, storage/CDN for outputs, web framework, queue technology, or ComfyUI use internally. ComfyUI-Mage is a client integration, not evidence of a ComfyUI backend.
- Banana.dev reportedly shut down its serverless GPU product around 2024. I did not verify this in this session; if true, Mage must have migrated.
- No engineering blog, conference talk, or Hugging Face org for Mage was found. HF was not specifically searched.
- The docs' /api/requests page, covering job states, limits, and errors, was not fetched.

## History, pivots, controversies, and legal

### Takeaway
Mage launched in mid-September 2022 as one of the first free and unlimited hosted Stable Diffusion UIs, run by Ollano, Inc. (the founders' earlier entity, about 2019). It then evolved into a model hub with creator rev-share, a premium tier (January 2023), video (Animate, July 2023), and a multi-model character and video platform. Its main controversy was 404 Media's August–September 2023 reporting on non-consensual porn and celebrity deepfakes made on the site while Stripe processed its NSFW subscriptions. That led to tightened rules. I found no evidence specific to Mage of being hit by the 2025 Visa/Mastercard adult-content crackdown.

### Cited Findings
- Legal entity: Ollano, Inc., 368 9th Ave, 6th Floor, New York, NY 10001. Trade names: Mage, Mage Space, mage.space. The site explicitly states it is not Mage AI (mage.ai) — [mage.space](https://www.mage.space/); [mage.space/terms](https://www.mage.space/terms)
- First HN launch post, "Mage: Create Anything. Yes Anything.", dated 2022-09-17 — [HN Algolia search](https://hn.algolia.com/api/v1/search?query=mage.space&tags=(story,comment)&hitsPerPage=40)
- Premium launched in January 2023 (per Hunkins, 2023-05-26). Model Creators revenue-share program announced 2023-03-18. Show HN for 50+ models plus GIFs on 2023-04-20 — [HN Algolia, hunkins comments](https://hn.algolia.com/api/v1/search?query=mage&tags=comment,author_hunkins&hitsPerPage=50)
- 2023-09-14, 404 Media (Emanuel Maiberg):
  - After its investigation found widespread non-consensual sexual images, Mage deleted NSFW Discord channels and began refusing sexual prompts that name celebrities
  - Mage announced deepfake NSFW detection
  - Pre-existing non-consensual images remained on the site, and lesser-known celebrities could still be used
  - A day earlier, 404 Media had reported that Stripe was processing Mage's NSFW subscription payments, after which the founders requested a call
  - [404 Media](https://www.404media.co/mage-space-new-restrictions-non-consensual-porn-celebrities/)
- Current Terms (last updated April 2024) prohibit pornography, explicit sexual acts, and commercial porn. They allow non-sexual nudity (e.g. breastfeeding), and the Community Guidelines allow artistic nudity. Any sexual content involving minors is banned. Payments go through Stripe — [mage.space/terms](https://www.mage.space/terms)
- Context: in mid-2025 Visa and Mastercard pressure, via processors such as Stripe, led Steam and itch.io to pull adult games — [PinkNews, 2025-08-04](https://www.thepinknews.com/2025/08/04/visa-mastercard-adult-purchases/); [PC Gamer](https://pcgamer.com/games/mastercard-deflects-blame-for-nsfw-games-being-taken-down-but-valve-says-payment-processors-specifically-cited-a-mastercard-rule-about-damaging-the-brand). No source links this to Mage.

### Inferences
- The 2023 shift from explicit NSFW subscriptions to "no pornography" terms was probably partly about protecting the Stripe relationship. Stripe is still the processor in 2026 (stripe.com is a top exit destination on Semrush). Content moderation in the generation path is therefore business-critical infrastructure, not an afterthought.
- Semrush lists competitors such as flatai.org and AI-girlfriend sites among referral sources. That suggests part of Mage's audience overlaps with adult-adjacent and character AI, which keeps policy and payment risk relevant.

### Gaps
- No lawsuits or regulatory actions involving Mage or Ollano were found.
- No evidence was found either way on whether Mage was affected by the 2025 card-network crackdown.
- The exact first launch date (before 2022-09-17) and Ollano's incorporation date are unconfirmed.

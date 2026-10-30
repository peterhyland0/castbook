# Mage (mage.space, Ollano, Inc.) — Product Deep Dive, as of 2026-10-29

Scope note: this covers mage.space (AI image/video/audio generator), not Mage.ai (data pipelines). Primary sources are mage.space, docs.mage.space (Mintlify docs, which have a changelog only from May 2026), and the Mage blog (mage.space/blog and blog.mage.space, with dated posts back to May 2025). Several blog dates come from page structured-data metadata, not visible text. These are flagged where relevant.

## 1. What features exist today, and how does the "Character" system work?

### Takeaway
Mage is now a browser-based, multi-model image, video, and audio studio. Its center is a reusable **Character**: one reference portrait, saved under a name, called in any prompt with `@handle`, and accepted by about 30 image and video models (Mage's own plus OpenAI, xAI, and Google models). Around it sit References, Character Voices, Multi-Characters, Motion Control, and about 20 single-purpose "Apps" (swaps, lipsync, enhancers, scene builder). Characters are reference-image conditioning. Users do not train a LoRA.

### Cited Findings
**Character creation and reuse**
- To create a Character, the user uploads one clear, well-lit, front-facing portrait, names it (the name becomes the `@handle`), and saves it. Docs say it is then "available on every supported model." — [Mage docs: Characters](https://docs.mage.space/features/characters)
- Usage example from the docs: `@sasha standing at a kitchen counter, morning light through the window, 35mm`. — [Mage docs: Characters](https://docs.mage.space/features/characters)
- Characters control **face only**. Outfit, pose, and location come from separate "References." A portrait gives a reliable face but less reliable full-body proportions, so docs suggest adding a full-body image as a Reference. — [Mage docs: Characters](https://docs.mage.space/features/characters)
- The docs make no mention of LoRA training for Characters. The mechanism is reference images, and each model has a cap on how many it accepts. — [Mage docs: Characters](https://docs.mage.space/features/characters)
- Models that accept Characters, with per-model reference-image caps:
  - **Video:** Berry/Berry 2 (9), Cherry Mini/Cherry/Cherry Pro (8), **Cherry 2 Pro (50)**, Grok Video (5), Lemon (10), Melon/Melon Pro (7), MiniMax-H3 Turbo/H3 (9), Plum/Plum Max/Plum Fast (9), Raspberry (5).
  - **Image:** GPT Image 2/2.5 Flare/2.5 Sunburst (15), Grok Image variants (3), Guava family (3), Mango 2/3S/3 (10), Nano Banana 2/2.1 (14).
  - Pear accepts a Character as a Motion Control target. — [Mage docs: Characters](https://docs.mage.space/features/characters)
- On Berry, Lemon, Melon, MiniMax-H3, and Plum, Character references and First/Last Frames are mutually exclusive modes in a single generation. — [Mage docs: Characters](https://docs.mage.space/features/characters)
- Characters are private until published. A published Character gets its own page and can enter a **leaderboard**. — [Mage docs: Characters](https://docs.mage.space/features/characters); launch posts "NEW: Publish Your Characters" (Jan 30, 2026) and "NEW: Character Pages & Leaderboard" (Feb 5, 2026) — [Mage blog index](https://blog.mage.space/)
- Character creation is "unlimited from Pro" ($30/mo). — [Mage docs: Characters](https://docs.mage.space/features/characters); [Mage pricing](https://www.mage.space/pricing)
- Characters can also be made without a photo:
  - **Character Builder: Attributes** builds one from preset traits.
  - **Character Builder: Muse** refines a character from starter images or face presets.
  - **Character Sheet** turns one image into a full reference sheet. — [Mage homepage](https://www.mage.space/); [Mage docs index](https://docs.mage.space/llms.txt)
- **Original launch:** "New: Create & Use Characters (Beta)", Jan 9, 2026. Steps were: Create New → upload a single portrait → name it → use it from the Prompt Bar. At launch it worked **only with Mango V2**. The post says only that the goal was to "keep your character consistent across all AI image and video creations." — [Mage blog, Jan 9 2026](https://blog.mage.space/article/new-create-use-characters/674f8c62-d68c-4d2d-908d-c9fc01ad0b62)
- **Multi-Characters** ("Multi-Characters Feature Is Here", Jan 24, 2026) puts several consistent characters in the same image or video. It launched in beta on Mango V2. — [Mage blog index](https://blog.mage.space/); [Mage on X](https://x.com/MageSpace_/status/2018376804919128114) (X page itself not fetchable; text from search snippet). It now works on any model that accepts more than one reference image. — [Mage docs: Characters](https://docs.mage.space/features/characters)
- **Character Voices** (launched May 15, 2026 with Scene Builder) attaches a voice to a Character, so the same voice is used whenever that Character speaks.
  - Supported on: Cherry line, Lemon, MiniMax-H3, Plum family, Raspberry. Not on Blueberry or Seed Audio.
  - **Audio References** (May 8, 2026) are a separate, per-generation audio steer. — [Mage docs: Character Voices](https://docs.mage.space/features/character-voices); [Mage release notes](https://docs.mage.space/release-notes.md)
- **Character Motion Control** (Feb 11, 2026) applies a reference video's movement to a Character, via the "Pear" model. It is unlimited on Max. — [Mage blog index](https://blog.mage.space/); [Mage pricing](https://www.mage.space/pricing)
- **References** (Mar 5, 2026) are reusable saved images (objects, places, poses, outfits) called with `@` handles, like Characters. **Moodboards** (Apr 3, 2026) guide a generation with a set of images. — [Mage blog index](https://blog.mage.space/); [Mage docs index](https://docs.mage.space/llms.txt)

**Other features and apps (current)**
- **Apps:**
  - Swaps: Face Swap, Video Face Swap, Video Character Swap, Character Swap, Outfit Swap.
  - Editing: Inpaint, Refine, Relight, Angles (new camera angle).
  - Enhancers: Image Enhancer (up to 6K), Video Enhancer (up to 1080p), Skin Enhancer.
  - Video: Video Editor (prompt-based), Lipsync, Music Video (characters sing and dance to a track), Scene Builder (two-character video scenes).
  - Characters: Character Builder: Muse, Character Builder: Attributes, Character Sheet, Recreate. — [Mage homepage](https://www.mage.space/); [Mage docs index](https://docs.mage.space/llms.txt)
- Apps rolled out in stages:
  - Enhancers: Mar 20, 2026.
  - Inpaint, Face Swap, Character Swap, Outfit Swap: Mar 27, 2026.
  - Video Editor: Jul 31, 2026.
  - Video Face Swap: Aug 18, 2026.
  - Video Character Swap: Aug 28, 2026. — [Mage blog index](https://blog.mage.space/); [Mage release notes](https://docs.mage.space/release-notes.md)
- Classic SD-style tooling remains: LoRAs and textual inversions (stack 1 / 2 / 5 by tier), ControlNet (Pro+), negative prompts, and custom model import on Pro Plus and Max (SD1.5, SDXL, Pony, Illustrious, LoRA, TI, LyCORIS, video LoRA). — [Mage pricing](https://www.mage.space/pricing)
- **Audio:** Audio generation launched Jul 9, 2026 on Seed Audio (voices, music, SFX, up to 120 s). Eleven v4 (TTS, 90+ languages) and Eleven Music v2.5 (tracks up to 5 min) were added Oct 24, 2026. — [Mage docs: Character Voices](https://docs.mage.space/features/character-voices); [Mage blog, Oct 24 2026](https://www.mage.space/blog/new-mage-design-moss-image-eleven-v4-eleven-music-v25-plum-video-fast)
- **Social:**
  - Private by default. Nothing reaches "Mage Social" unless the user posts it.
  - Private Messages were added Jun 27 / Jul 4, 2026.
  - Character pages and a leaderboard exist. — [Mage docs: content rules](https://docs.mage.space/policy/content-rules.md); [Mage blog index](https://blog.mage.space/)
- Other assistants: "Mage Chat Assistant" (May 1, 2026) and "Mage Agent (Beta)" (Sep 5 / Sep 11, 2026). See section 2. — [Mage blog index](https://blog.mage.space/)

### Inferences
- The "character" that the CEO described works across many models. The docs confirm it: one saved `@handle` is accepted by Mage's own image and video models and by GPT Image, Grok, and Nano Banana. Per-model reference caps suggest Mage passes the stored portrait as a reference-image input to each model's native multi-reference conditioning. It is not a trained identity adapter. This is inferred from the "reference images" framing and the per-model caps.
- The timeline fits the growth story: Characters launched Jan 9, 2026 and then shipped publish, leaderboard, multi-character, motion control, voices, Scene Builder, and Character Stories within about 4 months. It looks like the organizing primitive of 2026.

### Gaps
- No public metrics tie Characters to user growth. The CEO claim is not independently verifiable.
- The docs do not say whether Characters are stored as raw images, embeddings, or something else, or how the face is preserved on models without native reference support.
- No public statement on face-verification or consent checks at Character creation, beyond the policy text.

## 2. Chaining / workflows: can users pipe outputs between models? Is there a pipeline builder?

### Takeaway
Mage has **no visual node or pipeline builder in the consumer app**. Chaining happens in three ways:
1. Reusable assets (Characters, References, Voices) that persist across models.
2. Multi-step "story" tools (Storyboard, Story Studio, Autocreate) and purpose-built Apps that take existing media as input.
3. Since Sep 2026, a conversational **Mage Agent** with **Projects**, plus API, MCP, agent "Skills", and a ComfyUI node integration for developers who want real pipelines.

### Cited Findings
- **Storyboard** (Jan 13, 2026) arranges generated video clips into one sequence, previews it, and exports. Docs recommend First and Last Frames for continuous cuts. — [Mage docs: Storyboard/Story Studio/Autocreate](https://docs.mage.space/features/storyboard-story-studio-autocreate.md); [Mage blog index](https://blog.mage.space/)
- **Story Studio** (Jun 12, 2026) turns one story prompt into a connected sequence of **5–20 video scenes** with **up to 3 Characters**. Docs warn that consistency is less reliable over long sequences and suggest generating key scenes individually and assembling them in Storyboard. — [Mage docs](https://docs.mage.space/features/storyboard-story-studio-autocreate.md)
- **Autocreate** (Jun 5 / Jun 12, 2026) expands one prompt into a campaign of variations: up to 100 creations, with a minimum of 20 for images and 10 for video. — [Mage docs](https://docs.mage.space/features/storyboard-story-studio-autocreate.md)
- "Character Stories" appear in posts dated May 23 and Jun 5, 2026. — [Mage blog index](https://blog.mage.space/)
- **First and Last Frames** pins a clip's opening and closing frames. It is the mechanism for image → video and for clip-to-clip continuity. — [Mage docs index](https://docs.mage.space/llms.txt)
- Single-step media-in apps are de facto chain steps. Examples: Video Editor (video + prompt + reference images → edited video), Video Character Swap (clip → your Character), Lipsync (portrait + voice → talking), Music Video (Characters + track), Scene Builder (two Characters → scene). — [Mage skills docs](https://docs.mage.space/api/integrations/skills.md); [Mage homepage](https://www.mage.space/)
- **Mage Agent (Beta)** is at mage.space/agent. The post says to "simply tell it what you want to create, and it will handle the rest." It has a "Low (Free)" tier and a "High" tier, and outputs are Gems-only for now. The post does not describe pipeline steps. — [Mage blog: Mage Agent, Sep 11 2026](https://www.mage.space/blog/mage-agent)
- **Projects** (Sep 26, 2026) store Characters and References, Project Instructions (creative direction and style), and Default Settings (model, aspect ratio, resolution), so Agent "starts each session with the same context." Quote: "Set up your creative project once and keep building through conversation." — [Mage blog: Mage API, MCP & Projects](https://www.mage.space/blog/mage-api-mcp-projects)
- A guide titled "How to Use Mage Agent: Characters, Scenes, Video and More" is listed for Sep 25, 2026. The URL I guessed returned 404, so I did not read its contents. — [Mage blog index](https://blog.mage.space/)
- Other workflow guides on the blog: "How to Turn an AI Character Into a Video (Step by Step)" and "How To Create An AI Influencer On Mage: The Full 2026 Workflow" (Aug 6, 2026). Also "The Fanvue Creator's AI Workflow: Consistent Characters, Creative Freedom" (Sep 11, 2026). Titles only; not read. — [Mage blog index](https://blog.mage.space/)
- **Developer-side chaining:** open-source agent **Skills** ([github.com/mage-space/skills](https://github.com/mage-space/skills), MIT, beta 0.x) for Claude, Claude Code, Codex, and Cursor.
  - Skills include `/mage-characters`, `/mage-ugc-video` (product → creator-style video with scripted hook and spoken lines), `/mage-faceless-video` (topic → researched, narrated video), `/mage-ad-multiplier`, `/mage-ad-resizer`, `/mage-ad-localizer`, `/mage-music-video`, `/mage-scene-builder`, and others.
  - Saved Characters are reused across skills.
  - MCP tools: `list_models`, `get_model`, `estimate_cost`, `generate`, `get_request`, `create_upload`. — [Mage docs: Skills](https://docs.mage.space/api/integrations/skills.md)
- **ComfyUI integration:** "Mage models as ComfyUI nodes, for node-based workflows." — [Mage docs index](https://docs.mage.space/llms.txt)
- Pro Plus and Max can queue up to 10 generations at once. — [Mage pricing](https://www.mage.space/pricing)

### Inferences
- The "chaining workflows" the CEO mentioned most plausibly means three things: (a) carrying one Character, Voice, and References through image → edit/swap → video → lipsync/music video → Storyboard, (b) Story Studio and Autocreate as automated multi-step generation, and (c) Agent + Projects. Agent shipped in Sep 2026, so it is too recent to have driven earlier growth. The Character + Apps + Story tools from Jan–Jun 2026 are the likelier growth drivers.
- Skills like UGC Video and Faceless Video are multi-model pipelines (script → image → video → voice) packaged as agent instructions. The ad and marketplace skills suggest Mage is pushing beyond hobbyist and NSFW use toward creator, e-commerce, and marketing users.

### Gaps
- No screenshots or docs of an in-app "send to video / animate this / use as reference" button. Whether one-click output-to-input exists in the UI is unverified. The docs say nothing either way.
- I could not read the details of Mage Agent's internal planning (which models it chooses, multi-step plans).

## 3. Exactly which models are offered (image, video, audio)?

### Takeaway
The current catalog has about 35 model families in three groups:
- **Mage-branded "fruit" models**, whose underlying models are not disclosed.
- **Third-party lab-hosted models**: OpenAI GPT Image, xAI Grok, Google Nano Banana.
- **Open-weights models on Mage GPUs**: SD1.5/SDXL/SD3.5, Pony, Illustrious, Flux 2, Chroma, Krea 2, Z-Image, MOSS-Image, HiDream, Anima, Wan 2.2, LTX, MiniMax-H3.

Kling, Veo, Seedance, and Hailuo were offered by name in 2025 but **no longer appear by name** in the current catalog.

### Cited Findings
- **Mage's own models:**
  - Image: Mango (Mango, Mango 2, Mango 3S, Mango 3, Mango 3 Turbo); Guava (Guava, Pro, Pro 1.5, 2, 2 Pro); SDXL Plus.
  - Video: Cherry (Mini, Cherry, Pro, 2 Pro); Plum (Plum, Max, Fast); Lemon; Melon (Melon, Pro; anime); Berry (Berry, Berry 2); Blueberry (Blueberry, Blueberry 2); Raspberry; Kiwi; Pear (motion control).
  - The overview page says "Some are Mage's own models" and gives no base model or hosting detail. — [Mage docs: Models overview](https://docs.mage.space/models/overview.md); Mango 3 Turbo: [Mage blog index](https://blog.mage.space/)
- **Third-party models** ("run by the lab that built them and reached through Mage, and those carry that lab's safety filter"): GPT Image 2 / 2.5 Flare / 2.5 Sunburst; Grok Image / Image Quality / Image 2.0 / Grok Video; Nano Banana 2 / 2.1. — [Mage docs: Models overview](https://docs.mage.space/models/overview.md)
- **Open weights on Mage GPUs:** SD v1.5, SDXL, SD v3.5 Large, Illustrious family, Pony family, Flux 2, Chroma, Krea 2 Turbo, Z-Image, MOSS-Image, HiDream, Anima, Wan Video v2.2 (and Lightning), LTX Video Distilled/Dev, MiniMax-H3 Turbo/H3. — [Mage docs: Models overview](https://docs.mage.space/models/overview.md)
- **Audio:** Seed Audio, Eleven v4 (Eleven Speech), Eleven Music v2.5. — [Mage docs: Models overview](https://docs.mage.space/models/overview.md)
- **Mango origin:** at launch (Oct 21, 2025), Mango was described as "a brand new Image model architecture" **developed by a partner**. It specialized in stylized art and fantasy/romance themes, offered "high-quality image editing with multi-image capability," and was unlimited for Pro and Pro Plus (2K and 4K respectively). — [Mage blog: Introducing Mango](https://www.mage.space/blog/introducing-mango-our-new-image-model)
- Mango today: character, scene-merging, and editing family. Up to 10 reference images. Mango 3 at 1K/2K, Mango 3S up to 3K, Mango 2 up to 4K. Characters work on Mango 2, 3S, and 3 (not the original). — [Mage docs: Mango](https://docs.mage.space/models/mango.md)
- **2025 model history (dated):**
  - **Jul 8, 2025:** Gems-only "top external video models": Seedance Lite/Pro, Kling v1.6 Standard/Pro, Kling v2.1 Master, Hailuo v2.0 Standard/Pro, Veo3. — [Mage blog, Jul 8 2025](https://www.mage.space/blog/introducing-top-external-video-models)
  - **Jun 21 / Jun 30, 2025:** Flux Kontext; Kontext Dev unlimited. — [Mage blog index](https://blog.mage.space/)
  - **Jul 30 and Aug 18, 2025:** Unlimited Wan 2.2, then Lightning Wan. — [Mage blog index](https://blog.mage.space/)
  - **Aug 1, 2025:** Flux Krea. — [Mage blog index](https://blog.mage.space/)
  - **May 18, 2025:** FramePack image-to-video. — [Mage blog index](https://blog.mage.space/)
  - **Nov 20, 2025:** Unlimited Qwen Image, Qwen Image Lighting, Qwen Image Edit Plus (Pro and Pro Plus), plus Chroma V1 HD. — [Mage blog, Nov 20 2025](https://www.mage.space/blog/introducing-unlimited-qwen-models-chroma-v1-hd)
  - **Nov 25 – Dec 6, 2025:** Flux 2 (Nov 25), Z-Image (Nov 28), Peach Video with LoRA support for Z-Image and Qwen (Dec 6). — [Mage blog index](https://blog.mage.space/)
  - **Dec 9 – Dec 30, 2025:** Mango V2 (Dec 9), Kiwi Video (Dec 11), Blueberry Video (Dec 30). — [Mage blog index](https://blog.mage.space/)
- **2026 model launches (dated):**
  - Peach Max Video (Jan 6).
  - Z-Image Base (Jan 28).
  - Mango 3S (Feb 25).
  - Guava / Guava Pro (Mar 6).
  - Unlimited Nano Banana 2 (Mar 13).
  - SDXL Plus with ADetailer and 6K (Apr 2).
  - Unlimited Veo 3.1 Lite + Moodboards (Apr 3).
  - Cherry (Apr 10).
  - Blueberry 2 + Raspberry (Apr 18).
  - Unlimited GPT Image 2 + new Character Builder (Apr 24).
  - Anima + Berry (May 23).
  - Guava Pro 1.5, Grok Image, Grok Video / "Unlimited Grok Imagine" (May 29).
  - Melon (Jun 19).
  - Cherry Mini + 4K video (Jun 27).
  - Mango 3 (Jul 9).
  - Berry 2 (Jul 23).
  - Krea 2 (Jul 31).
  - Plum (Aug 5).
  - Guava 2 / 2 Pro (Aug 7).
  - Cherry 2 Pro (Aug 12; 1080p Aug 18).
  - Grok Image 2 unlimited (Aug 14).
  - Lemon (Aug 28; up to 30 s clips).
  - MiniMax H3 (Sep 5).
  - GPT Image 2.5 + Plum Max (Sep 9).
  - Mango 3 Turbo (Oct 2).
  - Unlimited Nano Banana 2.1 (Oct 9).
  - MOSS-Image, Plum Fast, Eleven v4, Eleven Music v2.5 (Oct 24). — [Mage blog index](https://blog.mage.space/); [Mage release notes](https://docs.mage.space/release-notes.md); [Mage docs index](https://docs.mage.space/llms.txt)
- Homepage "New on Mage" banner: Cherry 2 Pro is billed as the flagship video model ("most reference images and characters with voices"). Mango 3 is the flagship image model. — [Mage homepage](https://www.mage.space/)
- Mage published "Mage Exclusive Fruit Video Models Comparison" on Feb 24, 2026. — [Mage blog index](https://blog.mage.space/)

### Inferences
- The "fruit" names (Peach, Kiwi, Blueberry, Cherry, Berry, Plum, Lemon, Melon, Pear, Raspberry) appeared after Mage stopped listing Kling, Veo, Seedance, and Hailuo by name. Mango was explicitly "developed by a partner." So the fruit models are plausibly white-labeled or partner-supplied models, possibly from Chinese video labs, some perhaps fine-tuned. This is **speculation**: no source names the underlying models. Reasons to rebrand might include pricing flexibility, vendor swapping, and a unified Character interface across vendors.
- Qwen Image models (Nov 2025) no longer appear in the current docs catalog. They seem to have been retired or folded into other offerings. This is inferred from their absence.
- Peach / Peach Max (Dec 2025 – Jan 2026) also no longer appear in the current catalog.

### Gaps
- The base models behind Mango, Guava, Cherry, Plum, Lemon, Berry, Kiwi, Melon, Blueberry, Raspberry, and Pear are not disclosed anywhere I found.
- I did not confirm when Kling, Veo, Seedance, and Hailuo were removed. Veo 3.1 Lite was still offered as "unlimited" on Apr 3, 2026.
- HunyuanVideo: no evidence found that it is offered.

## 4. Pricing tiers, credits/"unlimited", free vs paid, fast mode

### Takeaway
There are five tiers: Free ($0, 300 signup Gems), Basic $10, Pro $30, Pro Plus $60, and Max $200. Each paid tier makes a set of models "unlimited" at base settings and includes monthly Gems. Gems pay for everything else: premium models above the user's tier, higher resolution or longer duration, Fast Mode, API calls, and Agent outputs. Prices rose in Feb 2026, and Gems became usable on every model in Jul 2026.

### Cited Findings
| Tier | Price | Monthly Gems | What it adds |
|---|---|---|---|
| Free | $0 | 300 signup bonus | Limited feature access |
| Basic | $10 | 500 | Unlimited on select models; LoRAs and TIs (1 each); inpainting; refine |
| Pro | $30 | 1,500 | Premium base models; unlimited video; unlimited character creation; Enhance 2K; LoRAs 2x; ControlNet; Animate; unlimited Mango |
| Pro Plus | $60 | 3,500 | Premium video models; Enhance 4K; LoRAs 5x; custom model import; queue 10 at once |
| Max | $200 | 15,000 | Unlimited motion control; HD and longer premium video; video LoRAs 2x; unlimited Cherry 2 Pro |

Sources: [Mage pricing](https://www.mage.space/pricing); [Mage homepage](https://www.mage.space/)

- Base models by tier:
  - Basic: SD1.5, SDXL, SD3.5, Flux 2, Chroma, Z-Image Turbo, Krea 2, MOSS-Image, GPT Image 2/2.5 (Low).
  - Pro adds: HiDream, Mango, Guava, Anima, Grok Image.
  - Pro Plus and Max add: Nano Banana 2/2.1. — [Mage pricing](https://www.mage.space/pricing)
- Docs rule: a model included in a plan is unlimited "at its base settings," within that model's resolution and duration ceilings. Add-ons (LoRAs, extra references) can raise the price and push a run to a higher plan or to Gems. "Every model accepts Gems." — [Mage docs: Models overview](https://docs.mage.space/models/overview.md)
- **Gem top-ups:**
  - $10 = 10,000
  - $20 = 20,500
  - $40 = 42,000
  - $100 = 110,000
- **Gem rules:**
  - Membership Gems expire after 30 days; purchased Gems after 90 days.
  - Failed generations refund Gems.
  - Accounts are capped at 300,000 Gems.
  - Free users can spend Gems.
  - Referral: 5,000 Gems each.
  - Auto Top-Up exists (Aug 28, 2026). — [Mage pricing](https://www.mage.space/pricing); [Mage docs: Settings](https://docs.mage.space/start/settings.md)
- **Fast Mode** is a paid priority queue on any model, run on Gems, with 1×/2×/4× speed options. It is advertised as "5–15× faster." — [Mage pricing](https://www.mage.space/pricing); [Mage docs index](https://docs.mage.space/llms.txt)
- **Feb 19, 2026 Membership Update:**
  - Pro went from $25 to $30 and Pro Plus from $50 to $60. Max ($200) was added.
  - Unlimited Blueberry became Max-only. Unlimited Kiwi became Pro Plus and Max only.
  - Monthly Gems were added to all memberships.
  - Rationale given: the cost of unlimited premium and external models, plus infrastructure.
  - Grace period ran until Mar 20, 2026. — [Mage blog: Membership Update](https://www.mage.space/blog/membership-update)
- **Gems history:**
  - Gems were introduced Jun 21, 2025, alongside Flux Kontext.
  - "Power Packs" came Jun 6, 2025.
  - In Jul 2025, Gems required an active membership.
  - "Gems Now Work Everywhere" followed on Jul 23, 2026. — [Mage blog index](https://blog.mage.space/); [Mage blog, Jul 8 2025](https://www.mage.space/blog/introducing-top-external-video-models)
- Refunds are generally not offered "because of the unlimited plans." Automation of the web app (bots, scripts) is prohibited, and users must use the API instead. — [Mage pricing](https://www.mage.space/pricing)

### Inferences
- The business model is a hybrid: flat-rate "unlimited" for cheap or owned models, and metered Gems for expensive partner models, high resolution, and speed. Rising video costs plausibly explain the 2026 price increase and the Max tier.

### Gaps
- Per-generation Gem prices are not on the pricing page. They are said to be available through the API's "List architectures" endpoint, which I did not fetch.
- Free-tier specifics (which models, daily caps, queue priority) are not spelled out. One Trustpilot reviewer (Aug 31, 2026) complained the free tier was "removed," which may reflect a free-tier reduction. Unconfirmed.

## 5. Content policy, NSFW stance, and moderation

### Takeaway
Mage permits mature content through a user-side **Mature Mode** toggle. It prohibits CSAM, non-consensual sexual content, likenesses of real people without consent, and voice cloning without consent. Third-party models carry their lab's filters. Moderation is described only as happening "at several layers." User complaints focus on over-blocking and sudden bans, so moderation precision and false positives are a live product problem.

### Cited Findings
- Prohibited on every model and plan:
  - Sexual content involving minors (real or generated).
  - Non-consensual sexual content, including generated likenesses of real people.
  - Harassment.
  - Illegal content. — [Mage docs: Content rules](https://docs.mage.space/policy/content-rules.md)
- Real people: generating a recognizable real person without consent is not allowed. **Building a Character from a non-consenting real person's photo** falls under the same rule, as does cloning a voice. — [Mage docs: Content rules](https://docs.mage.space/policy/content-rules.md)
- **Mature Mode** is a toggle under Settings → Content that "controls what can be shown to you." The docs do not list age, plan, or verification requirements. A "verification status" field exists in Account settings. — [Mage docs: Settings](https://docs.mage.space/start/settings.md)
- Third-party models (GPT Image, Grok, Nano Banana) carry their lab's safety filter, which Mage "can't override." — [Mage docs: Content rules](https://docs.mage.space/policy/content-rules.md); [Mage docs: Models overview](https://docs.mage.space/models/overview.md)
- Moderation "at several layers" is unspecified. There is a reporting and contest-removal flow ("Likeness, consent, and reported content"). A troubleshooting page distinguishes failed generations from refused or blocked ones. — [Mage docs: Content rules](https://docs.mage.space/policy/content-rules.md); [Mage docs index](https://docs.mage.space/llms.txt)
- The pricing FAQ allows "a certain level of creative freedom of expression." Mage's own SEO blog targets "creative freedom" queries: "The 4 Best AI Image Generators for Creative Freedom in 2026" (Oct 28, 2026), Fanvue-creator guides (Sep 2026), and MOSS-Image "designed for creative freedom." — [Mage pricing](https://www.mage.space/pricing); [Mage blog index](https://blog.mage.space/); [Mage blog, Oct 24 2026](https://www.mage.space/blog/new-mage-design-moss-image-eleven-v4-eleven-music-v25-plum-video-fast)
- Third-party SEO and affiliate pages market Mage as "uncensored." Trustpilot users dispute this, with complaints that filters trigger on harmless prompts, users were flagged for "real people" that were their own AI creations, and "sudden bans / hidden rules." — [Terabox insights](https://insights.terabox.com/hub/how-to-use-magespace-for-uncensored-ai-image-and-video-generation); [Trustpilot](https://www.trustpilot.com/review/mage.space)

### Inferences
- The likeness rule matters most for moderation: once a Character can be made from any single uploaded photo, the main risk becomes deepfakes and NCII of real people. Moderation likely includes face or real-person detection at Character upload and at generation time. This would explain user reports of AI-generated faces being flagged as real people. This is inferred, not documented.
- Mage's audience includes AI-influencer and Fanvue (adult-adjacent creator) users, per Mage's own content marketing. That suggests a meaningful NSFW share of usage.

### Gaps
- Moderation stack details (classifiers, human review, appeal SLAs) are not public.
- Mature Mode eligibility (age verification, region gating) is not documented in the pages read.

## 6. Public API / developer offering

### Takeaway
Yes. Since **Sep 26, 2026** (beta), Mage has offered:
- An async REST API paid per generation in Gems (any signed-in account; no subscription needed).
- An MCP server at `mcp.mage.space/mcp` for Claude, ChatGPT, Grok, and Cursor.
- TypeScript and Python SDKs (Oct 2, 2026).
- Open-source agent Skills.
- ComfyUI nodes.

Characters and References are first-class API resources.

### Cited Findings
- Mage API (beta) and Mage MCP (beta) launched Sep 26, 2026 (mage.space/api, mage.space/mcp). The MCP "supports all LLMs" and works with Claude, ChatGPT, and Grok. — [Mage blog: Mage API, MCP & Projects](https://www.mage.space/blog/mage-api-mcp-projects)
- SDKs and "MCP Skills" followed Oct 2, 2026, and "More MCP Skills" Oct 9, 2026. — [Mage blog index](https://blog.mage.space/)
- API endpoints:
  - Generation: generate, get request status, cancel request.
  - Discovery and account: list architectures (models, fields, prices), get account (Gem balance), create upload (signed URLs up to 100 MB).
  - Characters: list, create (from a portrait), delete.
  - References: list, create (image or audio), delete.
  - Docs also cover idempotency, rate limits and concurrency, and a versioning and deprecation policy, with an OpenAPI spec. — [Mage docs index](https://docs.mage.space/llms.txt)
- Any signed-in account can create an API key and pay per generation in Gems. Automation of the web app is banned in favor of the API. — [Mage pricing](https://www.mage.space/pricing)
- Mage's blog runs SEO content aimed at developers: "Best Image Generator MCP Servers for Claude" (Oct 8, 2026), "Best Claude Connectors for Video Generation in 2026: 6 MCP Servers Compared" and "Best Image Generation APIs in 2026" (Oct 16, 2026). — [Mage blog index](https://blog.mage.space/)

### Inferences
- The API, MCP, and Skills mark a strategic expansion from a consumer web app toward being a model-aggregator backend for agents. It also moves bot traffic, which the web app's anti-automation rule targets, onto metered rails.

### Gaps
- API per-model prices, rate-limit numbers, and adoption figures were not retrieved.

## 7. How the product changed over 2025–2026 (timeline)

### Takeaway
In 2025 Mage was an SD/Flux-era "unlimited generations" site with LoRAs, Gems-metered external video (Kling/Veo/Seedance/Hailuo), and open-weights video (Wan 2.2, FramePack). From late 2025 it shifted to proprietary-branded "fruit" models. On **Jan 9, 2026** it pivoted around **Characters**. Through 2026 it layered on apps, story tools, voices and audio, an Agent, Projects, and an API/MCP, and shipped a full redesign in Oct 2026.

### Cited Findings
**2025**
- May 4: "Introducing Mage V3".
- May 2025: profile organization, Spotlight search, FramePack image-to-video (May 18), Huge LoRA Update (May 23).
- Jun 6: Power Packs.
- Jun 13: Chroma, OmniA, V-Pred.
- Jun 21: Gems + Flux Kontext.
- Jul 8: external video models.
- Jul 30: unlimited Wan 2.2.
- Aug 1: Flux Krea.
- Aug 18: Lightning Wan.
- Oct 7: Community Update.
- Oct 21: Mango (partner-developed).
- Nov 19: UI and performance improvements.
- Nov 20: Qwen.
- Nov 24: faster Mango.
- Nov 25: Flux 2.
- Nov 28: Z-Image.
- Dec 6: Peach Video.
- Dec 9: Mango V2.
- Dec 11: Kiwi.
- Dec 24: New Mage Design (Beta).
- Dec 30: Blueberry. — [Mage blog index](https://blog.mage.space/)

**2026**
- Jan 6: Peach Max.
- **Jan 9: Characters (Mango V2 only).**
- Jan 13: Storyboard.
- Jan 15: "New Mage Is Live".
- Jan 24: Multi-Characters.
- Jan 30: Publish Characters.
- Feb 5: Character Pages & Leaderboard.
- Feb 11: Character Motion Control.
- Feb 19: price increase and Max tier.
- Feb 23: How To Import Models (guide).
- Mar 5: References.
- Mar 20 – Mar 27: Apps.
- Apr: Cherry, Blueberry 2, Raspberry, GPT Image 2, new Character Builder, Moodboards, SDXL Plus.
- May 1: Chat Assistant + Recreate.
- May 8: Audio References.
- May 15: Character Voice + Scene Builder.
- May 23 – Jun 5: Character Stories.
- Jun 12: Autocreate + Story Studio.
- Jul 9: Mango 3 + Audio generation.
- Jul 23: Gems on every model.
- Jul 31: Video Editor + referral program.
- Aug: Plum, Guava 2, Cherry 2 Pro, video swap apps, Lemon, Auto Top-Up.
- Sep 5 / 11: Mage Agent.
- Sep 26: API, MCP, Projects.
- Oct 2: SDKs + Mango 3 Turbo.
- Oct 9: Nano Banana 2.1 unlimited.
- Oct 17: New Mage Design (Beta).
- Oct 24: new design live + MOSS-Image, Plum Fast, Eleven v4, Eleven Music v2.5. — [Mage blog index](https://blog.mage.space/); [Mage release notes](https://docs.mage.space/release-notes.md)
- The Oct 24, 2026 post says only "Mage's new design is now live!" and that it "improved many details based on your suggestions." No specifics on UI changes. — [Mage blog, Oct 24 2026](https://www.mage.space/blog/new-mage-design-moss-image-eleven-v4-eleven-music-v25-plum-video-fast)
- Cadence: about weekly release posts through 2026. Mage also publishes a high volume of SEO "Best X in 2026" comparison articles (several per week since May 2026). — [Mage blog index](https://blog.mage.space/)

### Inferences
- The CEO's narrative of stagnant users followed by a reframe around Characters and workflows fits the record. Late 2025 was a commodity "many models, unlimited" positioning. From Jan 2026 nearly every release is character-centric (publish, leaderboard, multi-character, motion control, voices, scene builder, character stories, swap apps) or workflow-centric (Storyboard, Story Studio, Autocreate, Agent, Projects, Skills).
- The Feb 2026 price hike and new $200 Max tier, aimed at video, suggest that monetization moved toward heavy video users once characters made video series viable.

### Gaps
- No user-count, revenue, or traffic data was found to quantify the growth claim.
- Contents of the Jan 15, 2026 "New Mage Is Live" and Oct 7, 2025 "Community Update" posts were not read.

## 8. User sentiment

### Takeaway
Independent review data is thin and skews negative on Trustpilot (2.4/5, 32 reviews). Praise covers breadth of models, unlimited tiers, custom imports, multi-character casting, and the new UI. Complaints cover censorship and bans, confusing "unlimited vs Gems" billing, prompt and reference adherence, slow video, and weak support. I found no substantive Reddit threads.

### Cited Findings
- Trustpilot: TrustScore 2.4/5 from 32 reviews in the last 12 months (59% 1-star, 22% 5-star). — [Trustpilot](https://www.trustpilot.com/review/mage.space)
- Praise:
  - Unlimited generations and custom model imports (Oct 26, 2026).
  - Casting up to eight characters and unlimited short clips on a top plan (Jul 7, 2026).
  - Model variety and free upscales (Jul 1, 2026).
  - New UI easy to use, fast on most models. — [Trustpilot](https://www.trustpilot.com/review/mage.space)
- Complaints:
  - Over-restrictive filters (Jun 23, Oct 19, Aug 3, 2026).
  - AI creations flagged as real people (Jul 15).
  - Sudden bans and hidden rules (Sep 4).
  - "Unlimited" plans still needing Gems, and expensive video (Jul 14, Aug 22, Oct 21).
  - Credits spent on bad outputs (Aug 1, Sep 30).
  - Free tier removed (Aug 31).
  - Prompt and reference mismatch (Jul 31 – Oct 21); one user estimated about 10 usable images out of 134.
  - Slow video (Jul 15).
  - Site and support email down after payment (Oct 23).
  - Canned support replies. — [Trustpilot](https://www.trustpilot.com/review/mage.space)
- A Trustpilot reviewer reported a temporary ban for "botting" after heavy queueing on Pro Plus or Max (per search snippet). — [Trustpilot NZ](https://nz.trustpilot.com/review/mage.space)
- Toolradar: 1 review (5/5). It notes support via Discord and email, and that externally hosted models keep vendor filters. AI Tools Recap gives an editorial 8.8/10, calling Mage a Midjourney alternative with 20+ models (per search snippet). — [Toolradar](https://toolradar.com/tools/mage-space/reviews); [AI Tools Recap](https://aitoolsrecap.com/Product/mage)
- One 2026 affiliate review claims Mage has no character system. That contradicts the official docs and is likely stale. — [ai-girlfriend-review.com](https://ai-girlfriend-review.com/mage-space/)

### Inferences
- The strongest pain points map onto moderation (false positives on real-person detection, ban transparency) and the clarity of billing and entitlements (unlimited vs Gems). Both are relevant to a moderation-focused engineering role.

### Gaps
- No Reddit (r/StableDiffusion, r/mage_space), Discord, YouTube, or Product Hunt sentiment was retrieved. The searches returned mostly SEO and affiliate pages. The Trustpilot sample is small and self-selected.

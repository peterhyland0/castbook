# Multi-Model "Character -> Shots -> Video" Pipelines: Model Techniques and Serving/Orchestration Infra (state as of late Oct 2026)

Research notes for a side project: a multi-step pipeline (character sheet -> per-shot keyframes -> video clips -> audio/lip sync -> stitch) served on Modal behind a FastAPI API.

Method note: 18 tool calls (web search + fetch), run 2026-10-29. Many 2026 sources are SEO or vendor blogs that contradict each other. I mark conflicts inline. Items labelled "[background knowledge, not re-verified this session]" come from my training data (cutoff mid-2026). They are useful starting points but have no fetched citation, so check them before you rely on them.

---

## 1. Character identity techniques and the best current open models

### Takeaway
For still keyframes of a consistent character, the practical late-2026 stack is a multi-image reference editor. Use Qwen-Image-Edit-2511 if you want open weights, or Nano Banana Pro / Seedream 4.x if you will pay for an API. Generate a character sheet once, then compose each shot from the sheet plus pose/scene references. Add a per-character LoRA only when training-free drift is unacceptable. Among face-ID adapters on Flux, InfiniteYou measures slightly better than PuLID-Flux on identity, and IP-Adapter for Flux is weak on faces.

### Cited Findings
- **Qwen-Image-Edit-2511** (an upgrade of 2509): the official model card says character consistency is "significantly improved". 2509 already handled single subjects, and 2511 adds merging two separate person images into a coherent group shot. The weights are open on Hugging Face. — [HF model card](https://huggingface.co/Qwen/Qwen-Image-Edit-2511)
- ComfyUI has an official native workflow for Qwen-Image-Edit-2511 "consistent image editing". — [ComfyUI docs](https://docs.comfy.org/tutorials/image/qwen/qwen-image-edit-2511)
- Community multi-reference workflows combine up to 3 references with 2511 plus the Lightning (few-step) LoRA: face from image 1, wardrobe from image 2, scene from image 3. The author says complex 3-image composites with mismatched lighting need more iteration. — [Civitai article](https://civitai.com/articles/29885/combine-multiple-reference-images-into-one-edit-with-qwen-image-edit-2511-lightning); outfit-swap tutorial: [Next Diffusion](https://www.nextdiffusion.ai/tutorials/consistent-outfit-changes-with-multi-qwen-image-edit-2511-in-comfyui)
- Replicate hosts 2511 as an API and advises spelling out in the prompt what should change and what should stay the same. — [Replicate](https://replicate.com/qwen/qwen-image-edit-2511)
- **InfiniteYou vs PuLID-FLUX** (self-reported by the InfiniteYou authors): ID Loss 0.209 vs 0.225 (lower is better), CLIPScore 0.318 vs 0.286, PickScore 0.221 vs 0.212. In a 16-person user study, 72.8% preferred InfiniteYou. The paper also says the FLUX.1-dev IP-Adapter is not tailored to human faces and scores much worse on identity. — [InfiniteYou arXiv 2503.16418](https://arxiv.org/html/2503.16418v1)
- **Nano Banana Pro, Qwen-Edit, Seedream, LongCat** all preserve identity well in edits (cosine similarity between source and edited faces), but give weak expression changes. This is a practical concern when a shot needs emotion. — [PixelSmile arXiv 2603.25728](https://arxiv.org/html/2603.25728v1)
- A July 2026 paper on holistic identity (face + body + clothing) reports a "Face" score of 0.7522 for InfiniteYou vs 0.4948 for Nano Banana. The metric is not clearly ArcFace, so it is not directly comparable to the numbers above. — [arXiv 2607.25622](https://arxiv.org/html/2607.25622v1)
- Distilled or few-step models can degrade identity preservation. FastFace proposes guidance and attention tweaks to recover it. — [FastFace arXiv 2505.21144](https://arxiv.org/pdf/2505.21144); also [training-free acceleration of ID-preserved generation, arXiv 2605.09460](https://arxiv.org/html/2605.09460)
- **Wan2.1 video LoRA on your face, on Modal**: needs at least 4 images, ideally 8 or more, at about 400-800 px per side, with optional `.txt` captions. Modal says training takes "a few minutes". Generation fans out over 7 H100s in parallel and produces a 30 s video in about 5 min with default settings. — [Modal example: Fine-tune Wan2.1 on your face](https://modal.com/docs/examples/music-video-gen)
- Modal also has an official **Flux Kontext** image editing example. — [Modal: Edit images with Flux Kontext](https://modal.com/docs/examples/image_to_image)

### Inferences
- Recommended identity design: (a) generate a canonical **character sheet** (front, 3/4 and profile views, plus a full-body turnaround) with one strong model. (b) For each shot, run a **multi-image edit** (Qwen-Image-Edit-2511 open, or Nano Banana Pro / Seedream API) that takes the sheet plus a pose or scene reference. (c) Feed the resulting keyframe to I2V or FLF2V. The keyframe carries identity into the video, which is more reliable than asking a T2V model to remember the character.
- Escalation path: run training-free first. If ArcFace similarity drops below your threshold (see section 4), train a character LoRA on about 10-20 curated sheet images, for the image model (Flux / Qwen-Image) and optionally for Wan. LoRA training is minutes to tens of minutes on one H100, per the Modal Wan example.
- Face-only adapters (PuLID, InstantID, InfiniteYou) lock the face but not clothing or body. Reference editors (Qwen-Edit, Kontext, Nano Banana) handle outfit and full-body consistency better. Many pipelines therefore combine them: a reference editor for the composition, then an optional face-ID pass or face-restore.
- [background knowledge, not re-verified this session] Other training-free options to evaluate: FLUX.1 Kontext [dev] (open, single-reference editing, 12B); OmniGen2 (open, multi-image); ByteDance USO (style + subject, built on Flux); ACE++ (Flux-fill-based subject consistency); FLUX.2 (Black Forest Labs, late 2025, multi-reference). Gemini "Nano Banana" (2.5 Flash Image) accepts multiple images, and Nano Banana Pro is its higher-quality successor. Seedream 4.0 does multi-reference generation and editing through an API.

### Gaps
- I found no head-to-head ArcFace benchmark covering Qwen-Edit-2511, Kontext, USO, Nano Banana Pro, Seedream 4 and InfiniteYou together. The engineer should build their own small eval set (section 4).
- I found no USO identity benchmark numbers.
- I found no verified H100 training time or cost for a Flux or Qwen-Image character LoRA (ai-toolkit / diffusers / musubi-tuner). [background knowledge] Community reports usually put a Flux LoRA at about 1,000-2,000 steps and about 20-45 min on one H100, roughly $1.50-$3 at Modal H100 rates. This needs verification.
- I could not confirm whether Qwen-Image-Edit has a newer release than 2511 (e.g., a 2026 "2603"-style release).

---

## 2. Video models: open weights vs closed APIs, clip lengths, and stitching

### Takeaway
On the open-weight side, Wan 2.2 (Jul 2025, Apache 2.0) and its 2026 add-ons (Wan-Animate-2, Wan-Dancer) are still the newest downloadable Wan models. Every later Wan release (2.5, 2.6, 2.7, 3.0) is API-only. LTX-2 / LTX-2.3 from Lightricks is the main open alternative and generates audio and video jointly. Closed APIs (Veo 3.1, Kling 3.0, Seedance 2.0, Sora 2) lead on quality and native audio. Seedance 2.0 stands out on multi-reference character input. Open clips are about 5 s, so long sequences need last-frame chaining or first-last-frame (FLF) keyframe interpolation.

### Cited Findings
**Wan family status (key fact for design)**
- As of Sept 6, 2026, the Wan-AI Hugging Face org has 27 repos, all Wan 2.1 or 2.2 variants, Diffusers conversions, or 2 auxiliary models: **Wan-Dancer-14B** (Jul 2026, music-to-dance, Wan 2.2 base) and **Wan-Animate-2** (Aug 2026, character animation from a driving video, also listed as Wan2.2-Animate-2-14B). Both are Apache 2.0. — [howaiworks.ai: "The newest Wan you can download is still Wan 2.2"](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2)
- Wan 2.1 was released Feb 2025 (Apache 2.0). Wan 2.2 came out Jul 28, 2025 with T2V-A14B, I2V-A14B, TI2V-5B and S2V-14B, producing silent 5 s clips at 480p/720p. — [same source](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2)
- API-only Wan releases: **2.5-Preview** (Sep 24, 2025) and **2.6** (Dec 16, 2025). **2.7** (Apr 2026) is a 4-model suite with 2-15 s clips at 720p/1080p. `wan2.7-r2v` is capped at 10 s and accepts a `reference_voice` audio URL, and `videoedit` is also capped at 10 s. **3.0** (public beta Aug 2026) does 2-30 s at 480p-1080p and 30 fps, generates audio by default, and offers `wan3.0-video` and `wan3.0-video-prime`. — [same source](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2); confirming 2.7 closed weights: [Tellers.ai](https://tellers.ai/blog/wan_2_7_thinking_mode_ai_video_generation_2026-04-15), [localaimaster](https://localaimaster.com/blog/wan-2-7-open-source), [Runpod guide](https://www.runpod.io/articles/guides/wan-2-7-runpod)
- Conflict: wan27.org and youart.ai claim Wan 2.7 / 3.0 weights exist on HF or ModelScope. Official-org checks contradict them, so treat those sites as unreliable. — [wan27.org](https://wan27.org/blog/wan-2-7-huggingface-guide) vs [howaiworks.ai](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2)
- Wan 2.6's consistency feature is R2V (reference-to-video): you upload a reference video of a character to get new scenes with that character, for up to 3 characters. One comparison reports more drift over long sequences. These are secondary sources. — [fal Wan 2.6 dev guide](https://fal.ai/learn/devs/wan-26-developer-guide-mastering-next-generation-video-generation), [youart.ai](https://youart.ai/blog/wan-3-0-vs-wan-2-6)
- Wan 2.2 VRAM: TI2V-5B fits on 8 GB with ComfyUI native offloading. One 14B expert in fp8 is 14.3 GB and fits on a 24 GB card at 640x640. The official script for 14B at 720p without offload peaks at 59.8 GB, which needs an 80 GB card. — [ComfyUI Wan2.2 docs](https://docs.comfy.org/tutorials/video/wan/wan2_2), [Runpod ComfyUI Wan 2.2 guide](https://www.runpod.io/articles/guides/comfyui-wan-2-2). Note: howaiworks says TI2V-5B needs at least 24 GB, which is likely the unoffloaded figure, so the sources conflict.

**LTX-2 (Lightricks)**
- Announced Oct 23, 2025, with full open weights released Jan 5-6, 2026, including training code and a distilled variant. It generates synchronized video and audio in one pass, at up to native 4K / 50 fps. Clip length conflicts: the press release says up to 20 s and the company newsroom says 10 s. — [GlobeNewswire press release](https://www.globenewswire.com/news-release/2026/01/06/3213304/0/en/lightricks-open-sources-ltx-2-the-first-production-ready-audio-and-video-generation-model-with-truly-open-weights.html), [LTX newsroom](https://ltx.io/newsroom/ltx-2-is-now-open-source-full-model-weights-released)
- Parameter count is about 19B (one analysis says 14B video + 5B audio, dual-stream). LTX-2.3 followed in Mar 2026 (~20.9-22B), and LTX-2.5 was reportedly released Aug 2026. — [Introl](https://introl.com/blog/ltx-2-audiovisual-diffusion-synchronized-video-audio-2026), [novoads](https://novoads.ai/en/blog/what-is-ltx-2-3), [Wikipedia: LTX](https://en.wikipedia.org/wiki/LTX_(text-to-video_model)), [invideo Aug 2026 overview](https://invideo.io/blog/ltx-ai-video-generator/)
- Modal has official LTX-Video examples for T2V and I2V. — [Modal: Generate video clips with LTX-Video](https://modal.com/docs/examples/ltx), [Modal: Animate images with LTX-Video](https://modal.com/docs/examples/image_to_video)

**Other open models**
- MiniMax H3 video weights are released under a community license that bars local deployment in the US, EU, UK and South Korea without written authorization. That matters for a US-hosted project. — [howaiworks.ai](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2)

**Closed APIs (as of mid-2026; specs and prices conflict heavily across sources)**
- Seedance 2.0 scores highest on character consistency in one scored comparison (9.5/10 vs 8-8.5 for the others). It accepts multimodal references: up to 9 images, 3 videos and 3 audio files (one source says "12-file multimodal input"). Veo 3.1 is credited with scene consistency and prompt understanding. Sora 2 is strong on dynamic motion but weak on character fidelity. — [pixalice](https://pixalice.com/blog/seedance-2-0-vs-kling-3-0-sora-2-veo-3-1-video-generation-comparison-2026), [aifreeapi](https://www.aifreeapi.com/en/posts/seedance-2-vs-kling-3-vs-sora-2-vs-veo-3), [creatok](https://www.creatok.ai/blog/seedance-2-0-vs-kling-3-0-vs-sora-2-vs-veo-3-1-comparison)
- Max duration per generation (sources conflict): Veo 3.1 runs 4-8 s natively (extendable to 60 s+). Kling 3.0 is reported at 10, 15 or 180 s. Sora 2 is reported at 12-25 s. Seedance 2.0 is about 15 s. — [aimagicx Apr 2026](https://www.aimagicx.com/blog/veo-3-vs-kling-3-vs-sora-2-april-2026-comparison), [lushbinary](https://lushbinary.com/blog/ai-video-generation-sora-veo-kling-seedance-comparison/)
- Price per second (sources conflict): Seedance 2.0 about $0.14/s. Kling 3.0 about $0.03-0.10/s. Sora 2 about $0.10-0.50/s. Veo 3.1 about $0.10-0.75/s, with one source citing $0.75/s as the official rate (likely Veo 3.1 with audio at full quality). — [aifreeapi](https://www.aifreeapi.com/en/posts/seedance-2-vs-kling-3-vs-sora-2-vs-veo-3), [seavidgen](https://seavidgen.com/blog/ai-video-models-comparison-kling-3-seedance-2-sora-2-veo-3)
- One source refers to "Sora's exit" but notes Sora 2 was still operational at publication. Confirm Sora 2 API availability before you design around it. — [mindstudio](https://www.mindstudio.ai/blog/sora-vs-veo-3-1-vs-seedance-2-comparison)

### Inferences
- For an open-weights core, build on **Wan 2.2 14B** for I2V / FLF2V / VACE / Animate / S2V (ComfyUI and diffusers support is mature, and lightx2v distill LoRAs exist), plus **LTX-2.x** when you need joint audio and video. Put closed models (Seedance 2.0, Veo 3.1, Kling 3.0) behind the same "video provider" interface as premium tiers.
- Stitching strategies, from simplest to best:
  1. **Last-frame chaining**: I2V seeded with the previous clip's final frame. It is cheap, but errors and color drift accumulate after 2-3 hops.
  2. **Keyframe-first FLF2V**: generate all shot keyframes with the identity model, then interpolate each pair with Wan 2.2 FLF2V. Identity is re-anchored at every boundary, which makes this the best choice for character consistency.
  3. **Continuation / extension**: Veo extend, Kling extend, or Wan sliding-window and context options in ComfyUI.
  4. **Hard cuts** between shots, with identity coming from keyframes. This is the simplest option and fits film grammar.
- [background knowledge, not re-verified this session] Wan 2.1/2.2 output 81 frames at 16 fps (~5 s) for 14B and 121 frames at 24 fps for TI2V-5B. VACE (Wan2.1-VACE-14B) does reference-to-video, masked editing and pose/depth control. Wan2.2-Animate-14B (Sep 2025) does character animation and replacement from a driving video. Other subject-to-video options with open weights are Phantom (ByteDance, on Wan), MAGREF, HunyuanCustom and HunyuanVideo 1.5 (Tencent, Nov 2025, ~8.3B), and SkyReels-V2 (infinite-length "diffusion forcing").

### Gaps
- I did not verify current Wan2.2 FLF2V or VACE specs, or exact HunyuanVideo 1.5 / HunyuanCustom / Phantom / MAGREF / SkyReels release details. These come from background knowledge only.
- I did not verify official Veo 3.1, Kling 3.0, Seedance 2.0 or Hailuo pricing pages. The blog numbers conflict by up to 10x.
- I could not determine whether Wan 3.0 open weights will ship. Sources only say it is rumored.

---

## 3. Audio and lip sync

### Takeaway
Pick open lip-sync tools by job. **LatentSync 1.6** is the baseline for dubbing an existing clip (lips only). **InfiniteTalk** (Wan-based, Apache 2.0) handles audio-driven image- or video-to-video with body motion and long clips. **Wan 2.2 S2V** gives more expressive generated performances. LTX-2 and the closed models (Veo 3.1, Wan 3.0, Seedance 2.0) generate audio natively, which can remove the lip-sync step altogether.

### Cited Findings
- LatentSync regenerates lip movements from audio while keeping head pose and identity, using an audio-conditioned latent diffusion model with SyncNet supervision. — [LatentSync arXiv 2412.09262](https://arxiv.org/html/2412.09262v2)
- LatentSync 1.6 is called the current local baseline for replacing lips in existing video. VRAM is about 8 GB for v1.5 and about 18 GB for v1.6. — [Instavar 2026 comparison](https://instavar.com/research/ai-video/open-source-lip-sync-models), [percify](https://percify.io/blog/the-best-free-ai-lip-sync-video-generators-for-instant-content-creation)
- InfiniteTalk does audio-driven V2V and I2V including body motion, is Apache 2.0, and runs on low-VRAM cards through Wan2GP. In one hands-on test it was steadier than Wan 2.2 S2V but less nuanced in facial expression. Wan S2V was more expressive with more head movement, though the background could look static. A vendor test reports InfiniteTalk at 720p takes about 336 s to render a 9.5 s clip (GPU not specified). — [Instavar](https://instavar.com/research/ai-video/open-source-lip-sync-models), [percify](https://percify.io/blog/the-best-free-ai-lip-sync-video-generators-for-instant-content-creation)
- MuseTalk is a real-time lip-sync alternative that uses latent-space inpainting. — [MuseTalk arXiv 2410.10122](https://arxiv.org/html/2410.10122v1)
- Wan 2.7 R2V accepts a `reference_voice`, and Wan 3.0 generates audio by default (API only). — [howaiworks.ai](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2)
- LTX-2 generates synchronized audio and video in one pass. — [GlobeNewswire](https://www.globenewswire.com/news-release/2026/01/06/3213304/0/en/lightricks-open-sources-ltx-2-the-first-production-ready-audio-and-video-generation-model-with-truly-open-weights.html)
- TTS: Modal has an official **Chatterbox TTS** example (Resemble AI, open). — [Modal: Generate speech with Chatterbox](https://modal.com/docs/examples/chatterbox_tts)

### Inferences
- Pipeline order for talking shots: script line -> TTS (ElevenLabs API, or Chatterbox open on Modal) -> audio-driven video (InfiniteTalk or Wan S2V from the identity keyframe) -> optional LatentSync touch-up -> mux. For non-dialogue shots, use plain I2V / FLF2V plus a separate SFX/music track.
- Store a per-character **voice ID** (an ElevenLabs voice or a Chatterbox reference clip) next to the character sheet as part of the "character asset".
- [background knowledge, not re-verified this session] MultiTalk (MeiGen, multi-person conversational video on Wan) comes before InfiniteTalk from the same lab. Hallo3 (Fudan) is a portrait animation model. OmniHuman-1 (ByteDance) is available via API (e.g., BytePlus/fal). Other open TTS candidates include F5-TTS, Kokoro, Dia, Higgs Audio, and VibeVoice.

### Gaps
- I found no rigorous benchmark (LSE-C/LSE-D, SyncNet confidence) comparing InfiniteTalk, Wan S2V and LatentSync head-to-head. The sources are anecdotal.
- I did not verify H100 timings for InfiniteTalk or S2V.
- I did not research current ElevenLabs pricing or 2026 open TTS leaderboards.

---

## 4. Evaluating identity consistency and quality automatically

### Takeaway
Use a 3-layer eval. (1) **Face embedding cosine** (InsightFace/ArcFace) between the character's reference face and the faces detected in every keyframe and every Nth video frame. (2) **Holistic similarity** with DINOv2/CLIP image embeddings for outfit and body. (3) A **VLM judge** for prompt adherence, artifacts and continuity. Add VBench-style temporal metrics for flicker and subject consistency.

### Cited Findings
- Academic identity papers report face similarity as ID loss or cosine similarity between face embeddings. InfiniteYou reports ID Loss (1 - cosine) plus CLIPScore and PickScore for prompt adherence and aesthetics. — [InfiniteYou arXiv](https://arxiv.org/html/2503.16418v1)
- PixelSmile scores identity preservation as cosine similarity between source and edited face embeddings, and shows that identity and expression change trade off against each other. — [PixelSmile arXiv 2603.25728](https://arxiv.org/html/2603.25728v1)
- A holistic identity benchmark scores face, body and clothing separately because face-only metrics miss outfit drift. — [arXiv 2607.25622](https://arxiv.org/html/2607.25622v1)
- Agentic systems already use VLM-based quality control as a pipeline stage: ViMax has an explicit VLM QC agent, and the IEEE SMC 2026 tutorial describes a multimodal "Continuity Supervisor" critic. — [ViMax arXiv 2606.07649](https://arxiv.org/abs/2606.07649), [IEEE SMC CAI-2026 tutorial](https://www.ieeesmc.org/cai-2026/tutorial-10-a-human-ai-collaborative-framework/)
- One aiofm.info guide claims PuLID-Flux averages about 0.72 face similarity but gives no source. Do not rely on that figure. — [aiofm.info](https://aiofm.info/en/guides/pulid-vs-instantid-vs-faceid)

### Inferences
- A concrete gate design: detect faces with InsightFace (`buffalo_l`) and take the 512-d ArcFace embedding. Compare against the mean embedding of the character sheet. Use a pass threshold of about 0.5-0.6 cosine (ArcFace same-identity pairs usually score > ~0.4-0.5, and generated content is noisier). Calibrate the threshold on your own data. For video, sample 1 frame in 8, take the min and p10 similarity per clip, and flag clips where the face is lost or similarity drops mid-clip (a sign of identity morphing).
- For temporal consistency, use adjacent-frame DINO cosine (VBench "subject consistency") and CLIP cosine ("background consistency"). A cheap flicker check is the mean absolute difference between consecutive frames.
- VLM judge: send keyframes or a contact sheet of the clip plus the shot spec to a strong VLM (Gemini 2.5/3, GPT-5-class or Claude). Ask for a structured JSON rubric (prompt adherence 1-5, anatomy artifacts, identity match vs reference, continuity with previous shot). Use the output as a retry or accept signal, not as ground truth. Spot-check judge agreement against human labels.
- [background knowledge] VBench / VBench-2.0 (github.com/Vchitect/VBench) define 16+ dimensions including subject consistency (DINO), background consistency (CLIP), motion smoothness, dynamic degree, aesthetic and imaging quality. VBench-2.0 adds human fidelity and commonsense dimensions.

### Gaps
- I did not fetch VBench docs this session, so the metric names and implementation details above come from background knowledge.
- I found no published, validated ArcFace threshold for "same character" on generated content. You need to calibrate it yourself.

---

## 5. Speedups: distillation, caching, compile, quantization, attention, parallelism

### Takeaway
The biggest lever is step distillation. LightX2V's Wan 2.2 4-step distill LoRAs/models cut 40-50 steps with CFG to 4 steps without CFG, about 20-24x fewer DiT evaluations. FP8, SageAttention, TeaCache/FBCache and torch.compile stack on top for roughly another 1.5-2x. Sequence parallelism (xDiT/USP) across GPUs cuts wall-clock time but not GPU-seconds. Distillation can hurt identity and motion, so evaluate it.

### Cited Findings
- LightX2V step distillation goes from 40-50 steps to 4 without CFG, an approximately 20-24x speedup. — [LightX2V docs: Step Distillation](https://lightx2v-en.readthedocs.io/en/latest/method_tutorials/step_distill.html)
- The LightX2V inference framework runs about 2x faster than ComfyUI for the same distilled models. The README cites up to about 42x combined speedup with FP8 and other optimizations, and about 1.4x on a single H100 for one optimization (model not specified in the snippet). — [lightx2v/Wan2.2-Distill-Loras HF](https://huggingface.co/lightx2v/Wan2.2-Distill-Loras), [lightx2v/Wan2.2-Distill-Models HF](https://huggingface.co/lightx2v/Wan2.2-Distill-Models), [LightX2V GitHub](https://github.com/modeltc/lightx2v)
- 2026 research on combining Wan2.2 dual-expert few-step distillation with low-bit quantization used one H100 80GB. — [arXiv 2606.00658](https://arxiv.org/pdf/2606.00658)
- DART (Sept 2026) addresses reusing ordinary LoRAs (e.g., a character LoRA) with few-step distilled video models without retraining, at 640x640, 129 frames, 16 fps with LightX2V. This shows that **character LoRAs and distill LoRAs interfere**. — [DART arXiv 2609.20051](https://arxiv.org/pdf/2609.20051)
- Production data point (RTX 5090, 480p, clips of 5 s or less, sliding windows + 4-step distill): median 112 s per clip. This is not H100. — [GitHub issue inkseq/h3-studio #555](https://github.com/inkseq/h3-studio/issues/555)
- Modal's official Flux example uses torch.compile for speed. — [Modal: Run Flux fast with torch.compile](https://modal.com/docs/examples/flux)
- A ready-made ComfyUI workflow for Wan 2.2 + Lightx2v V2 is published. — [RunComfy](https://www.runcomfy.com/comfyui-workflows/wan-2-2-lightx2v-v2-comfyui-workflow-fast-image-text-to-video)
- Few-step / distilled models can weaken identity preservation. FastFace and arXiv 2605.09460 propose training-free fixes. — [FastFace](https://arxiv.org/pdf/2505.21144), [arXiv 2605.09460](https://arxiv.org/html/2605.09460)

### Inferences
- A rough per-clip cost model for **Wan 2.2 14B I2V, 720p, 81 frames, H100**: this is my estimate, not a cited number, so verify it. Undistilled 40 steps with CFG is roughly 15-30+ min. 4-step distill + FP8 + SageAttention is roughly 1-3 min. At Modal's H100 rate of about $3.95/hr (section 6), that is about $0.07-0.20 per 5 s clip distilled versus $1-2+ undistilled. At 480p, expect about 2-3x less.
- Order of adoption: distill LoRA (biggest win) -> FP8 weights (halves VRAM, so 14B fits on one 80 GB card without offload) -> SageAttention 2 -> TeaCache/MagCache/FBCache (skip redundant steps; less useful at 4 steps) -> torch.compile (check compatibility with GPU snapshots, see section 6) -> xDiT/USP multi-GPU only when latency matters more than cost.
- Run an A/B on identity: distilled vs full steps with the same seed and keyframe, scored with ArcFace (section 4). If the drop is material, keep full steps for hero shots or use DART-style reparameterization.

### Gaps
- I found no authoritative, published H100 seconds-per-clip for Wan 2.2 14B with or without the lightx2v 4-step LoRA. The engineer should benchmark this directly.
- I did not verify TeaCache, FBCache, SageAttention or xDiT speedup factors this session.

---

## 6. Modal patterns for diffusers/ComfyUI inference: snapshots, volumes, lifecycle, autoscaling, cost

### Takeaway
Use the standard Modal pattern: a pinned image, weights in a Modal **Volume** (HF cache), an `@app.cls(gpu=...)` with `@modal.enter()` to load the pipeline once per container, `@modal.method()` for work, and a separate lightweight FastAPI app (`@modal.asgi_app()` with `@modal.concurrent`) that calls GPU classes. **Memory snapshots** (CPU stable, GPU alpha) cut cold starts 3-10x. They do not speed up reading weights from storage, and they conflict with torch.compile and multi-GPU. H100 costs about $3.95/hr and A100-80GB about $2.50/hr.

### Cited Findings
**Memory snapshots** — [Modal docs: Memory Snapshots](https://modal.com/docs/guide/memory-snapshots)
- CPU: `enable_memory_snapshot=True` on `@app.function` / `@app.cls`. Snapshots only apply to deployed apps (`modal deploy`).
- GPU (alpha): also pass `experimental_options={"enable_gpu_snapshot": True}`. Load, compile and warm up inside `@modal.enter(snap=True)`, which is captured in the snapshot. `@modal.enter(snap=False)` runs after restore.
- Without GPU snapshots: load the model to CPU in `snap=True`, then `.to("cuda")` in `snap=False`. In Modal's example this cut startup from about 6 s to about 2 s. Typical speedup is 3-10x.
- Limitations: GPU snapshots generally don't work with multi-GPU code. They don't speed up loading weights from storage. `torch.compile` can break snapshot creation (`TORCHINDUCTOR_COMPILE_THREADS=1` sometimes fixes it). Warm up with forward passes before the snapshot. Redeploys invalidate snapshots. Expect 2-3 snapshots per GPU type early on. Randomness seeded before the snapshot repeats on every restore, so **reseed per request**.
- GPU snapshot example page: [Modal: Snapshot GPU memory to speed up cold starts](https://modal.com/docs/examples/gpu_snapshot). It notes the feature is experimental, so test carefully before production. Related LLM example: [Cut Ministral 3 cold start 10x with snapshots](https://modal.com/docs/examples/ministral3_inference)

**Reference app pattern (Modal SD3.5 Turbo text-to-image example)** — [Modal: Run Stable Diffusion with a CLI, API, and web UI](https://modal.com/docs/examples/text_to_image)
- `debian_slim` + Python 3.12 + pinned diffusers/torch via `uv_pip_install`. `HF_HUB_CACHE=/cache` on a named Volume `hf-hub-cache`. The model is pinned to a revision.
- `@app.cls(gpu="H100", timeout=600)`. `@modal.enter()` loads the pipeline in bf16 to CUDA. `@modal.method() run(prompt, batch_size=4, seed)` returns PNG bytes.
- `@modal.fastapi_endpoint(docs=True)` exposes a Swagger-documented endpoint. A separate `@modal.concurrent(max_inputs=100)` + `@modal.asgi_app()` front end scales independently of the GPU class.
- Cold start is "about one minute" without snapshots. Warm throughput is about 1 image per 1-2 s for batch 1-16.

**Official Modal examples relevant to this pipeline** — [Modal examples index](https://modal.com/docs/examples)
- Flux + torch.compile: https://modal.com/docs/examples/flux
- Flux Kontext image editing: https://modal.com/docs/examples/image_to_image
- LTX-Video T2V: https://modal.com/docs/examples/ltx
- LTX-Video I2V: https://modal.com/docs/examples/image_to_video
- Fine-tune Wan2.1 on your face (LoRA + parallel generation on 7 H100s; Volumes `finetune-video-data` and `finetune-video-models`): https://modal.com/docs/examples/music-video-gen
- Chatterbox TTS: https://modal.com/docs/examples/chatterbox_tts
- GPU snapshot: https://modal.com/docs/examples/gpu_snapshot
- The examples index fetched this session listed **no official ComfyUI example**. The `/docs/examples/comfyapp` URL now serves the SD3.5 diffusers example. — [Modal examples index](https://modal.com/docs/examples)

**ComfyUI on Modal (community)**
- The `modal-comfyui` repo runs ComfyUI on Modal with scale-to-zero, GPU snapshots, and model caching through Volumes, and the author tested it with Wan 2.2. — [GitHub 3kanAlpha/modal-comfyui](https://github.com/3kanAlpha/modal-comfyui)
- A blog post describes getting ComfyUI cold starts under 3 s on Modal by hiding the GPU during CPU snapshot creation, because ComfyUI initializes CUDA at startup. It predates GPU snapshots, so the approach may be outdated. — [tolgaoguz.dev](https://tolgaoguz.dev/post/comfy-workflow-api-with-modal/)

**Cost (Modal per-second GPU rates, 2026; verify on modal.com/pricing)**
- B300 $0.001972/s (added Jul 2026). B200 $0.001736/s (~$6.25/hr). H200 $0.001261/s (~$4.54/hr). H100 $0.001097/s (~$3.95/hr). A100-80GB $0.000694/s (~$2.50/hr). L40S $0.000542/s (~$1.95/hr). Region pinning costs 1.5-1.75x and non-preemptible costs 3x. — [usagepricing Jul 2026 snapshot](https://www.usagepricing.com/blueprint/activity/modal-2026-07-14-b300-sandbox-notebooks), [Spheron](https://www.spheron.network/blog/modal-gpu-pricing-2026-per-second-billing/), [DevTune](https://devtune.ai/verticals/aiml-infrastructure-llm-tools/modal/pricing). Conflict: one Spheron table lists Modal H100 at $1.95/hr, likely an error. — [Spheron benchmarks](https://www.spheron.network/blog/gpu-cloud-benchmarks/)

### Inferences
- Suggested Modal app layout:
  - `api` is a CPU-only FastAPI app (`@modal.asgi_app`, `@modal.concurrent(max_inputs=100+)`). It validates requests, writes job rows, and calls `.spawn()` on GPU classes, returning a job ID with polling or a webhook.
  - Each model family gets its own `@app.cls`, sized to its VRAM:
    - `ImageEditor`: Qwen-Image-Edit-2511 on H100 or A100-80GB.
    - `VideoI2V`: Wan2.2-14B FP8 + lightx2v on H100.
    - `LipSync`: InfiniteTalk or LatentSync on L40S or A100.
    - `TTS`: Chatterbox on L4 or L40S.
    - `Judge`: InsightFace + DINOv2 on L4, CPU, or a small GPU.
  - Separate classes let each one autoscale and snapshot on its own. Mixing models in one container defeats GPU snapshots and wastes VRAM.
- Autoscaling knobs [background knowledge, not in fetched pages]:
  - `min_containers=0` for a side project (scale to zero), or 1 for the hot video class during demos.
  - `buffer_containers=1` to pre-warm under bursty load.
  - `scaledown_window` around 60-300 s, so idle GPUs are released while back-to-back shots in one job hit a warm container.
  - `max_containers` caps spend.
  - `@modal.batched(max_batch_size, wait_ms)` for image models.
  - Video DiTs usually run batch 1 with `max_inputs=1` per GPU.
  - `retries=modal.Retries(...)` and `timeout` per function.
- Weights: pre-download into a Volume with a one-off `modal run` function, and pin HF revisions. For 14B video models (tens of GB), weight loading dominates cold start, and GPU snapshots don't fix that. Keep a warm container during active sessions or accept a cold start of about 30-90 s.
- ComfyUI vs diffusers on Modal: ComfyUI gives the fastest access to new community nodes (Wan wrappers, lightx2v, InfiniteTalk, VACE) and portable workflow JSON. diffusers gives cleaner Python, easier snapshots, and simpler testing. A pragmatic split is diffusers for image edit and TTS, and ComfyUI-in-Modal (API-format workflow JSON submitted to a headless server in the container) for the fast-moving Wan video graph.

### Gaps
- I did not fetch the Modal docs pages for `min_containers`, `buffer_containers`, `scaledown_window` or `@modal.batched` this session. The exact parameter names come from background knowledge and should be checked against modal.com/docs/guide/cold-start and /scale.
- I did not verify whether Modal has published an official ComfyUI or Wan 2.2 inference example in late 2026.
- I did not verify whether GPU snapshots are still alpha in Oct 2026.

---

## 7. Orchestrating multi-step DAG workflows: retries, idempotency, partial failure, moderation, artifact caching

### Takeaway
A character -> shots -> video job is a long-running DAG of 10-100 GPU and API calls, each taking 10 s to 10 min, many of them flaky (API rate limits, OOMs, moderation rejects). Production teams such as HeyGen and Google's Veo reference architecture run this on durable execution, usually Temporal, with Inngest/Hatchet/Restate as lighter alternatives. For a side project, a Postgres job table + Modal `.spawn()` + content-addressed GCS artifacts gets you about 80% of the benefit.

### Cited Findings
- HeyGen runs millions of AI video workflows on Temporal and says video generation is "an orchestration problem as much as a media-processing problem". They note that customer-level fairness is still application logic. — [Temporal blog: How HeyGen runs millions of AI workflows](https://temporal.io/blog/how-temporal-powers-workflows-at-heygen), [HeyGen research](https://www.heygen.com/research/how-temporal-powers-workflows-at-heygen), [Inside HeyGen's durable agent harness](https://temporal.io/blog/inside-heygen's-durable-agent-harness)
- Google and Temporal show a Gemini + Veo pipeline as durable steps: prompt analysis -> script generation -> video generation -> post-processing. — [Temporal blog: Gemini and Veo](https://temporal.io/blog/build-prod-ready-gen-ai-temporal-gemini-veo)
- Durable execution means a failure in the final step (e.g., a 45 s thumbnail step during a deploy) retries only that step rather than the whole pipeline. Workflow code must be deterministic, so model calls go in activities. — [GMI Cloud on Temporal Cloud](https://www.gmicloud.ai/en/blog/temporal-cloud-continuous-ai-workflows)
- Inngest model: define `step.run()` steps inside a normal function. Inngest handles execution, retries and state. It has a post on fal.ai media pipelines covering retries, async coordination, per-user fairness and observability. — [Inngest docs](https://www.inngest.com/docs/patterns/reliably-run-critical-workflows), [Inngest blog index](https://www.inngest.com/blog.txt)
- Hatchet is a Postgres-backed queue/durable workflow engine with a low-ops profile. Rolling your own requires a job queue, state machine, idempotency keys, retry policies, dead-letter queues and a DB schema. — [youngju.dev 2026 deep dive: Temporal/Inngest/Trigger/Hatchet/Restate/DBOS](https://www.youngju.dev/blog/culture/2026-05-25-durable-workflow-temporal-inngest-trigger-hatchet-restate-dbos-2026-deep-dive), [noqta.tn](https://www.noqta.tn/blog/durable-execution-ai-agents-inngest-trigger-temporal-2026)
- Durable media pipeline reference (Temporal + a media API): [ittybit guide](https://ittybit.com/guides/durable-media-pipeline-with-temporal). Async pipeline pattern for image/video APIs: [programminginsider](https://programminginsider.com/how-to-build-a-reliable-async-pipeline-for-ai-image-and-video-apis/)
- A counterpoint argues you can do durable execution for agents in about 150 lines without Temporal. — [HackerNoon](https://hackernoon.com/you-dont-need-temporal-yet-durable-execution-for-ai-agents-in-150-lines)
- Agentic research systems model shots as a dependency graph. ViMax uses graph-based dependencies between shots for consistency. MVAgent passes typed conditioning inputs between shots and keeps a "continuity memory" of how each shot ends so the next can start from it. — [ViMax](https://arxiv.org/abs/2606.07649), [MVAgent arXiv 2609.30609](https://arxiv.org/abs/2609.30609)

### Inferences
- DAG for this project:
  1. `plan` (LLM produces structured shot list JSON).
  2. `character_sheet` (once per character, cached).
  3. Per shot in parallel: `keyframe` -> `identity_check` (retry with a new seed or prompt if below threshold, max N).
  4. `tts` per dialogue line in parallel.
  5. Per shot: `video` (I2V/FLF2V/S2V depending on type) -> `video_check`.
  6. `lipsync` if needed.
  7. `assemble` (ffmpeg concat + audio mix on CPU).
  8. `moderation` gates at the input prompt, the reference upload (face/consent/NSFW/minor checks), and the final output.
- Idempotency and caching: content-address every artifact. `key = sha256(step_name, model_id+revision, params, input_artifact_hashes, seed)` maps to `gs://bucket/artifacts/{key}.{ext}`, with a row in Postgres. Before running a step, check whether the key exists and skip if so. This gives free resume after partial failure, cheap re-runs when a user edits one shot, and deduplication across A/B arms that share upstream steps.
- Partial failure: keep a per-shot status. A failed shot shouldn't fail the job, so surface "shot 4 failed moderation" and offer regenerate. Use exponential backoff for API 429/5xx. On GPU OOM, fall back to lower resolution or a different GPU class. Put a hard budget cap per job (track estimated $ per step).
- Modal-native minimum: FastAPI `POST /jobs` writes a row and calls `orchestrator.spawn(job_id)`. `orchestrator` is a CPU Modal function that walks the DAG, fans out with `.spawn()` or `.map()` to GPU classes, and persists step state after each step. Modal's function `retries` handles transient errors. Graduate to Temporal, Inngest, Hatchet or Restate when you need cross-deploy durability, human-in-the-loop approvals (approve storyboard before spending on video), or long waits on slow closed APIs (polling a Veo/Kling job for minutes). Running the orchestrator inside a durable engine and the GPU steps as Modal calls is a clean split.
- ComfyUI's API-format workflow JSON is a good unit for a single video step (it's a DAG too), but use it as a leaf inside your own orchestrator rather than as the job-level orchestrator.
- [background knowledge] fal.ai offers "workflows" that chain fal-hosted models as a hosted DAG. That is useful for prototyping with closed models, but it locks you into fal.

### Gaps
- I found no Modal-specific documentation on long-running DAG orchestration or durable state. The Modal `.spawn()` / `FunctionCall.get()` semantics above come from background knowledge.
- I did not fetch the specifics of the fal.ai and Inngest media pipeline post.
- I found no source on standard moderation tooling for gen-video (e.g., Hive or AWS Rekognition for frames, provider-side moderation in closed APIs).

---

## 8. LLM agents for shot planning and model selection, and A/B testing workflows

### Takeaway
2026 research converges on multi-agent "film crew" designs: screenwriter -> shot planner -> character/storyboard artist -> generator -> VLM QC/continuity critic, with explicit cross-shot conditioning memory. The engineering lesson from MVAgent is that consistency comes from passing **typed conditioning artifacts**, not from repeating text prompts. I found no public sources on how product teams A/B test generation workflows.

### Cited Findings
- **ViMax** (arXiv 2606.07649, Jun 2026) uses agents for screenwriting, shot planning, character styling, video generation and VLM-based QC. It uses graph-based shot dependencies and RAG-style hierarchical story decomposition. Each shot spec includes camera angle, movement, lighting, character positioning and duration. — [arXiv abs](https://arxiv.org/abs/2606.07649), [HTML](https://arxiv.org/html/2606.07649v1)
- **MVAgent** (arXiv 2609.30609, Sept 2026): when each shot is a separate request to a frozen generator, repeated text doesn't determine appearance, layout or state. Agents pass typed conditioning inputs, and an observer keeps continuity memory of each shot's ending. It also uses shot-level policy optimization. — [arXiv](https://arxiv.org/abs/2609.30609)
- **MovieAgent** (ICLR 2026) uses multi-agent chain-of-thought planning (director, screenwriter, storyboard artist, location manager). It takes a script and a character bank and produces multi-scene, multi-shot video with consistent characters, subtitles and audio. — [Lacuna summary](https://lacuna.tiptreesystems.com/work/automated-movie-generation-via-multi-agent-cot-planning/wrk_415c6af587cb2efaebb90fb8ba81e0a6)
- **FRAMEWORKERS** (arXiv 2608.29814) is a dynamic multi-agent framework for AI video production. — [arXiv PDF](https://arxiv.org/pdf/2608.29814). "One Sentence, One Drama" generates personalized short dramas with multi-agent systems. — [arXiv 2605.22144](https://arxiv.org/pdf/2605.22144)
- The IEEE SMC CAI-2026 tutorial describes a Scripter / Storyboard Artist / Cinematographer / Composer pipeline with a multimodal Continuity Supervisor, and calls character and style consistency a fundamental open problem. — [IEEE SMC tutorial](https://www.ieeesmc.org/cai-2026/tutorial-10-a-human-ai-collaborative-framework/)
- Wan 3.0's API accepts a document (pptx/pdf/md, up to 100 MB) or a URL as input and exposes `prompt_extend`, so a planning LLM is built into the provider. Wan 2.7 has a "thinking mode" for its image models. — [howaiworks.ai](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2), [Tellers.ai](https://tellers.ai/blog/wan_2_7_thinking_mode_ai_video_generation_2026-04-15)
- HeyGen describes a durable "agent harness" on Temporal for its agentic video product. — [Temporal blog](https://temporal.io/blog/inside-heygen's-durable-agent-harness)

### Inferences
- Implement the planner as a single LLM call with a strict JSON schema (Pydantic):
  - `Shot{id, duration_s, shot_type (dialogue|action|establishing), characters[], camera, lighting, action, dialogue_line?, start_keyframe_prompt, end_keyframe_prompt?, transition (cut|flf|continue), model_hint}`
  - Then use a deterministic **router**:
    - dialogue -> TTS + InfiniteTalk/S2V
    - action with an end pose -> FLF2V
    - establishing shot without a character -> T2V
    - premium tier -> Seedance/Veo
  - Let the LLM *suggest* a model. Code should *decide* based on constraints such as duration, budget and whether the character appears in the shot. This keeps cost predictable.
- Add a critic loop: after each shot, the VLM judge plus ArcFace output feed a bounded retry (≤2) with a revised prompt or seed. Log every attempt.
- A/B testing approach (my recommendation, not sourced):
  - Version each workflow as an immutable config (`workflow_id`, model revisions, step params). Assign arms per job via a feature flag.
  - Since artifacts are content-addressed, arms share cached upstream steps (e.g., same keyframes, different video model), which makes paired comparisons cheap.
  - Score offline with automatic metrics (ArcFace min/p10, DINO temporal, VLM rubric, cost, latency) on a fixed prompt-and-character eval set. Online, use user pairwise preference (side-by-side "which is better") or downstream signals (download/share/regenerate rate).
  - Track $/accepted-second-of-video as the north-star cost metric.

### Gaps
- I found no public engineering write-ups on how companies (Higgsfield, HeyGen, Hedra, Runway, Pika) A/B test generation workflows or route between models.
- I did not open the ViMax or MVAgent papers in full, so I have no quantitative results (consistency scores vs baselines).
- I did not research Banodoco/Discord or r/StableDiffusion community benchmark threads, because those aren't reliably searchable through this tool.

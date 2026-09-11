# Image Generation Reference

Image creation, editing, and composition using Imagen 4 and Gemini image models ("Nano Banana").

> **Nano Banana** = Google's internal name for native image generation in the Gemini API. Three variants:
> - **Nano Banana 2** (`gemini-3.1-flash-image-preview`) - NEW DEFAULT. 3-5x faster, 95% Pro quality, web grounding, 100+ language text rendering, character consistency (5 chars/14 objects). Released Feb 2026.
> - **Nano Banana Flash** (`gemini-2.5-flash-image`) - Previous default, still stable.
> - **Nano Banana Pro** (`gemini-3-pro-image-preview`) - Quality with reasoning, 4K text.

## Models

### Nano Banana 2 (Default - Recommended)

**gemini-3.1-flash-image-preview** - NEW DEFAULT
- Best for: General use, fast generation with near-Pro quality
- Quality: High (95% parity with Pro); Speed: 3-5x faster than previous Flash
- Cost: ~$0.045/image (512px) to ~$0.151/image (4K); ~25-30% cheaper than Pro
- Resolution: 512px to 4K with expanded aspect ratios
- Text rendering: 100+ languages; Character consistency: up to 5 characters and 14 objects
- Reasoning levels: Minimal/High/Dynamic (auto-selected); Web grounding for brands, landmarks, recent events
- Status: Preview (Feb 2026)

### Nano Banana Flash (Previous Default)

**gemini-2.5-flash-image**
- Best for: Speed, high-volume generation, rapid prototyping (~5-10s per image)
- Cost: ~$1/1M input tokens (1 image = 1,290 tokens ≈ $0.00129)
- Aspect Ratios: all 10; Image Sizes: 1K, 2K, 4K; Status: Stable (Oct 2025)

**gemini-3-pro-image-preview** - Nano Banana Pro
- Best for: Professional assets, 4K text rendering, complex prompts
- Cost: ~$2/1M text input, $0.134/image (resolution-dependent)
- Multi-Image: up to 14 reference images (6 objects + 5 humans)
- Features: Thinking mode, Google Search grounding; Status: Preview (Nov 2025)

### Imagen 4 (Alternative - Production)

- **imagen-4.0-generate-001** - Standard quality, balanced performance, ~$0.02/image, 1K/2K, 1-4 images per request
- **imagen-4.0-ultra-generate-001** - Maximum quality, ~15-25s/image, ~$0.04/image, 2K preferred, 1-4 per request
- **imagen-4.0-fast-generate-001** - Fastest (~2-5s/image), ~$0.01/image, 1K, no `imageSize` parameter support, 1-4 per request

**Legacy**: `gemini-2.0-flash-preview-image-generation` - deprecated; use Nano Banana or Imagen 4.

## Model Comparison

| Model | Quality | Speed | Cost | Best For |
|-------|---------|-------|------|----------|
| gemini-3.1-flash-image-preview | ⭐⭐⭐⭐½ | 🚀🚀 Fastest | 💵 Low | **NEW DEFAULT** - General use |
| gemini-2.5-flash-image | ⭐⭐⭐⭐ | 🚀 Fast | 💵 Low | Previous default, stable |
| gemini-3-pro-image | ⭐⭐⭐⭐⭐ | 💡 Medium | 💰 Medium | Text/reasoning |
| imagen-4.0-generate | ⭐⭐⭐⭐ | 💡 Medium | 💰 Medium | Production (alternative) |
| imagen-4.0-ultra | ⭐⭐⭐⭐⭐ | 🐢 Slow | 💰💰 High | Marketing assets |
| imagen-4.0-fast | ⭐⭐⭐ | 🚀 Fast | 💵 Low | Bulk generation |

**Selection Guide**:
- **Default/General**: `gemini-3.1-flash-image-preview` (fastest, near-Pro quality, web grounding)
- **Stable Alternative**: `gemini-2.5-flash-image`
- **Production Quality**: `imagen-4.0-generate-001`; **Marketing/Ultra**: `imagen-4.0-ultra-generate-001`
- **Text-Heavy Images / complex prompts with reasoning**: `gemini-3-pro-image-preview` (4K text, Thinking mode)
- **Real-time data integration**: NB2 or Pro with Search grounding

## API Differences: generate_images vs generate_content

The single most important distinction - the two model families use different SDK methods with different naming conventions.

| Feature | Imagen 4 | Nano Banana (Gemini) |
|---------|----------|---------------------|
| Method | `generate_images()` | `generate_content()` |
| Config | `GenerateImagesConfig` | `GenerateContentConfig` |
| Prompt param | `prompt` (string) | `contents` (string/list) |
| Image count | `numberOfImages` (camelCase) | N/A (single per request) |
| Aspect ratio | `aspectRatio` (camelCase) | `aspect_ratio` (snake_case) |
| Size | `imageSize` | `image_size` |
| Response | `generated_images[i].image.image_bytes` | `candidates[0].content.parts[i].inline_data.data` |
| Multi-image input | ❌ | ✅ Up to 14 references |
| Multi-turn chat | ❌ | ✅ Conversational |
| Search grounding / Thinking | ❌ | ✅ (Pro only) |
| Text rendering | Limited (~25 chars) | 4K (Pro) |

**Imagen 4** uses `generate_images()`:

```python
from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

response = client.models.generate_images(
    model='imagen-4.0-generate-001',
    prompt='Professional product photography of smartphone',
    config=types.GenerateImagesConfig(
        numberOfImages=1,      # camelCase
        aspectRatio='16:9',    # camelCase
        imageSize='1K'         # Standard/Ultra only; Fast has no imageSize
    )
)
for i, generated_image in enumerate(response.generated_images):
    with open(f'output-{i}.png', 'wb') as f:
        f.write(generated_image.image.image_bytes)
```

**Nano Banana** uses `generate_content()`:

```python
response = client.models.generate_content(
    model='gemini-3.1-flash-image-preview',  # or gemini-2.5-flash-image, gemini-3-pro-image-preview
    contents='A serene mountain landscape at sunset with snow-capped peaks',
    config=types.GenerateContentConfig(
        response_modalities=['IMAGE'],  # Uppercase required
        image_config=types.ImageConfig(
            aspect_ratio='16:9',        # snake_case
            image_size='2K'             # 1K, 2K, 4K - uppercase K
        )
    )
)
for i, part in enumerate(response.candidates[0].content.parts):
    if part.inline_data:
        with open(f'output-{i}.png', 'wb') as f:
            f.write(part.inline_data.data)
```

**Critical Notes**:
1. `response_modalities` values MUST be uppercase: `'IMAGE'`, `'TEXT'`. Use `['TEXT', 'IMAGE']` when you want a description alongside the image; text-only returns a description with no generation.
2. `image_size` values MUST have uppercase K: `'1K'`, `'2K'`, `'4K'`.
3. Imagen 4 Fast doesn't support `imageSize`.
4. Pro accepts `tools=[{'google_search': {}}]` for Search grounding and both modalities for grounded infographics.

## Aspect Ratios

| Ratio | Resolution (1K) | Use Case |
|-------|----------------|----------|
| 1:1 | 1024×1024 | Social media, avatars, icons |
| 2:3 | 682×1024 | Vertical portraits |
| 3:2 | 1024×682 | Horizontal portraits |
| 3:4 | 768×1024 | Vertical posters |
| 4:3 | 1024×768 | Traditional media |
| 4:5 | 819×1024 | Instagram portrait |
| 5:4 | 1024×819 | Horizontal photos |
| 9:16 | 576×1024 | Mobile/stories/reels |
| 16:9 | 1024×576 | Landscapes, banners, YouTube |
| 21:9 | 1024×438 | Ultrawide/cinematic |

All ratios cost the same 1,290 tokens per image on Gemini models.

## Editing, Composition, Multi-Turn

```python
import PIL.Image

# Edit / style transfer / object add-remove: pass the image plus instructions
img = PIL.Image.open('original.png')
response = client.models.generate_content(
    model='gemini-2.5-flash-image',
    contents=['Add a red balloon floating in the sky', img],
    config=types.GenerateContentConfig(
        response_modalities=['IMAGE'],
        image_config=types.ImageConfig(aspect_ratio='16:9')
    )
)

# Multi-image composition: several PIL images in contents
img1, img2, img3 = (PIL.Image.open(p) for p in ('background.png', 'foreground.png', 'overlay.png'))
response = client.models.generate_content(
    model='gemini-3-pro-image-preview',
    contents=['Blend these reference styles into a cohesive hero image', img1, img2, img3],
    config=types.GenerateContentConfig(
        response_modalities=['IMAGE'],
        image_config=types.ImageConfig(aspect_ratio='16:9', image_size='4K')
    )
)
```

- Standard models: ~3-5 reference images for best results; Pro: up to 14 (6 objects + 5 humans). Collage style refs into one image when composition degrades.
- Multi-turn conversational refinement works with any Nano Banana model:

```python
chat = client.chats.create(
    model='gemini-3.1-flash-image-preview',
    config=types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE'])
)
response1 = chat.send_message('Create a minimalist logo for a coffee brand called "Brew"')
response2 = chat.send_message('Make the text bolder and add steam rising from the cup')
```

- Iterative refinement outside a chat: save the PNG, reopen with PIL, send back with edit instructions.

## Prompt Engineering

**Narrative > keywords.** Write like you're briefing a photographer, not providing SEO keywords.

❌ `"cat, 4k, masterpiece, trending, professional, ultra detailed, cinematic"`
✅ `"A fluffy orange tabby cat with green eyes lounging on a sun-drenched windowsill. Soft morning light creates a warm glow. Shot with a 50mm lens at f/1.8 for shallow depth of field. Natural lighting, documentary photography style."`

Structure every prompt as **subject** (specific) + **context** (lighting, location, time) + **style** (photography, illustration). Be specific about what you want rather than negations - "crystal clear, sharp, perfect focus" beats "no blur".

| Technique | Example | Purpose |
|-----------|---------|---------|
| ALL CAPS emphasis | `The logo MUST be centered` | Force attention to critical requirements |
| Hex colors | `#9F2B68` instead of "dark magenta" | Exact color control |
| Negative constraints | `NEVER include text/watermarks. DO NOT add labels.` | Explicit exclusions |
| Realism trigger | `Natural lighting, DOF. Captured with Canon EOS 90D DSLR.` | Photography authenticity |
| Structured edits | `Make ALL edits: - [1] - [2] - [3]` | Multi-step changes |
| Consistent style | Repeat one `base_prompt` across a set | Series coherence |

### Text in Images

- Maximum ~25 characters total for optimal results, up to 3 distinct phrases; 4K text needs `gemini-3-pro-image-preview`.
- Template: `Image with text "[EXACT TEXT]" in [font style]. Color: [hex]. Position: [top/center/bottom]. Background: [description].`

## Safety Settings

```python
config = types.GenerateContentConfig(
    response_modalities=['IMAGE'],
    safety_settings=[
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
        )
    ]
)
```

Categories: `HARM_CATEGORY_HATE_SPEECH`, `HARM_CATEGORY_DANGEROUS_CONTENT`, `HARM_CATEGORY_HARASSMENT`, `HARM_CATEGORY_SEXUALLY_EXPLICIT`. Thresholds: `BLOCK_NONE`, `BLOCK_LOW_AND_ABOVE`, `BLOCK_MEDIUM_AND_ABOVE` (default), `BLOCK_ONLY_HIGH`.

## Limitations

- **Imagen 4**: English prompts only, max 480 prompt tokens, SynthID watermark, child images restricted in EEA/CH/UK, cannot replicate specific people or copyrighted characters.
- **Nano Banana**: ~3-5 reference images on standard models (14 on Pro), standard text rendering is limited (Pro does 4K), SynthID watermark, uppercase `'IMAGE'`/`'TEXT'` modalities and `'1K'`-style sizes enforced.
- No video or animation from these models (use Veo); no real-time generation.

## Troubleshooting

### aspect_ratio Parameter Error

**Error**: `Extra inputs are not permitted [type=extra_forbidden, input_value='1:1', input_type=str]`

**Cause**: `aspect_ratio` must be nested inside an `image_config` object, not passed directly to `GenerateContentConfig`.

```python
# ❌ This will fail
config = types.GenerateContentConfig(
    response_modalities=['image'],
    aspect_ratio='16:9'  # Wrong - not a direct parameter
)

# ✅ Correct implementation
config = types.GenerateContentConfig(
    response_modalities=['IMAGE'],
    image_config=types.ImageConfig(
        aspect_ratio='16:9'
    )
)
```

### Response Modality Case Sensitivity

The `response_modalities` parameter expects uppercase values:
- ✅ Correct: `['IMAGE']`, `['TEXT']`, `['IMAGE', 'TEXT']`
- ❌ Wrong: `['image']`, `['text']`, `['Image']`

### Image Size Parameter Not Supported

**Error**: `400 INVALID_ARGUMENT`

**Cause**: the `image_size` parameter in `ImageConfig` is not supported by all Nano Banana models.

**Solution**: don't pass `image_size` unless explicitly needed - the API uses sensible defaults.

```python
# ✅ Works - no image_size
config=types.GenerateContentConfig(
    response_modalities=['IMAGE'],
    image_config=types.ImageConfig(
        aspect_ratio='16:9'  # Only aspect_ratio
    )
)

# ⚠️ May fail - with image_size (model-dependent)
config=types.GenerateContentConfig(
    response_modalities=['IMAGE'],
    image_config=types.ImageConfig(
        aspect_ratio='16:9',
        image_size='2K'  # Not supported by all models
    )
)
```

### Multi-Image Reference Issues

**Problem**: poor composition with multiple reference images.

**Solutions**: limit to 3-5 references on standard models; use Pro for up to 14; collage multiple style refs into a single image; provide clear textual descriptions of how to blend the styles.

---

**Related**: [Image Understanding](./vision-understanding.md) - analyzing reference images · [Video Generation](./video-generation.md) · [Audio Processing](./audio-processing.md) · [AI Multimodal Skill](../SKILL.md)

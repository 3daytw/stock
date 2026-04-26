import anthropic
import gradio as gr
from dotenv import load_dotenv

load_dotenv("API.env")
client = anthropic.Anthropic()

# ── Platform system prompts ────────────────────────────────────────────────────

SYSTEM_PROMPTS = {
    "Nano Banana Pro": """You are an expert AI image generation prompt engineer for Nano Banana Pro.
Your goal is to craft prompts that look photographic and natural — not AI-generated.

Rules:
- Use specific cinema/photography camera references as provided
- Describe real, imperfect lighting — avoid "perfect" studio setups
- Include organic skin texture cues: natural pores, subtle uneven tone, fine hair
- Reference film stocks or cinema LUTs for color grading
- AVOID: "highly detailed", "masterpiece", "8k render", "hyperrealistic", "flawless skin", "perfect"
- Keep the English prompt concise: 50–90 words, comma-separated

Output format — return EXACTLY this structure:
【中文說明】
主體：（描述主體與構圖）
光線：（描述打光策略）
去 AI 感重點：（說明用了哪些技巧讓畫面更真實）

【English Prompt】
（the actual generation prompt in English）""",

    "Midjourney": """You are an expert Midjourney v6 prompt engineer.
Your goal is to craft prompts that look authentic and avoid the stereotypical AI look.

Rules:
- Use --style raw for photorealistic results
- Always include --ar appropriate to the shot
- Use --v 6.1
- Reference real skin texture: natural pores, subtle blemishes, real hair strands
- Specify lighting direction and color temperature precisely
- AVOID: "epic", "stunning", "flawless", "perfect skin", "hyperrealistic"

Output format — return EXACTLY this structure:
【中文說明】
主體：（描述主體與構圖）
光線：（描述打光策略）
去 AI 感重點：（說明用了哪些技巧讓畫面更真實）

【English Prompt】
（the actual Midjourney prompt with parameters, single line）"""
}

# ── Dropdown & checkbox suggestions ───────────────────────────────────────────

LIGHTING_OPTIONS = [
    # 戶外自然光
    "黃金時刻斜射側光 Golden hour warm side light",
    "日出晨光霧感柔光 Sunrise hazy soft light",
    "午後過雲散射光 Afternoon overcast diffused light",
    "強烈正午日光硬影 Harsh midday direct sunlight",
    "斜陽穿雲丁達爾光 Tyndall rays through clouds",
    "逆光輪廓光 Backlit rim light silhouette",
    "藍調時刻城市微光 Blue hour urban ambient",
    "陰雨天均勻散射光 Rainy day flat diffused light",
    # 城市人造光
    "城市夜間霓虹反光 Neon reflection night city",
    "街燈暖橘頂光 Street lamp warm overhead",
    "玻璃帷幕大樓反射光 Glass building reflected daylight",
    "廣告招牌混合色光 Mixed signage color light",
    # 廣告常用
    "大面積柔光箱擴散光 Large softbox diffused light",
    "Clamshell 蝴蝶光（廣告人像標準）Clamshell butterfly light",
    "窗邊自然柔光 Window natural soft light",
    "環形補光自然感 Ring fill natural look",
]

MOOD_OPTIONS = [
    # 廣告主流
    "陽光清新感 Fresh sunny bright",
    "大面積柔白高調 High-key soft white airy",
    "溫暖奶油感 Warm creamy lifestyle",
    "奢華低調質感 Luxe muted editorial",
    "簡約現代乾淨 Clean minimal modern",
    "自然有機無濾鏡感 Raw organic unfiltered",
    # 季節情緒
    "清涼夏日高飽和 Vibrant summer saturated",
    "秋日琥珀溫潤感 Amber autumn warm tones",
    "冬日冷灰霧感 Cold grey winter mist",
    "春日粉嫩清爽 Pastel spring fresh",
    # 風格調性
    "都市時尚冷調 Urban fashion cool tone",
    "復古底片褪色 Vintage film faded",
    "電影感 Teal & Orange",
    "日系淡雅清透 Japanese soft desaturated",
    "運動活力鮮豔 Sport vibrant punchy",
    "夢幻柔焦朦朧 Dreamy soft focus haze",
]

EXTRA_OPTIONS = [
    # 鏡頭質感
    "底片顆粒感 Film grain",
    "鏡頭光暈 Lens flare",
    "邊緣暗角 Vignette",
    "色差散景 Chromatic aberration",
    "輕微動態模糊 Slight motion blur",
    "手持微晃感 Handheld shake",
    "淺景深背景散焦 Shallow DOF bokeh",
    "鏡頭水氣霧感 Lens fog moisture",
    # 皮膚細節（去 AI 感關鍵）
    "自然毛孔紋路 Natural skin pores",
    "真實膚色不均 Uneven natural skin tone",
    "細毛與汗水光澤 Fine hair and sweat sheen",
    "輕微雀斑色素 Subtle freckles pigmentation",
    "嘴唇自然紋路 Natural lip texture",
    "眼白自然血絲 Natural eye veins",
    # 環境細節
    "灰塵光粒子 Dust particles in light",
    "環境反光色溢 Color bleed from environment",
    "背景雜亂真實感 Realistic messy background",
    "衣物自然皺摺 Natural fabric wrinkles",
]

CAMERA_OPTIONS = [
    # 電影攝影機
    "ARRI Alexa 35（電影級色彩科學）",
    "ARRI Alexa Mini LF（大片幅電影機）",
    "RED V-RAPTOR 8K（高解析電影機）",
    "RED Komodo 6K（輕巧電影機）",
    "Sony Venice 2（廣告電影首選）",
    # 照片相機
    "Sony FX3（影像廣告常用）",
    "Fuji X-T5（底片色彩還原）",
    "Fuji GFX 100S（中片幅細節豐富）",
    "Leica M11（街拍質感）",
    "Hasselblad 503CW（中片幅底片）",
    # 底片
    "Kodak Super 16mm 底片",
    "Kodak Portra 400 底片 35mm",
    "Fuji Velvia 50 底片（高飽和）",
]

LENS_OPTIONS = [
    "Leica Summicron（人文清透感）",
    "Cooke S7/i T2（奶油膚色廣告首選）",
    "ARRI Ultra Prime（電影高銳均勻）",
    "Zeiss Supreme Prime T1.5（高對比德系銳利）",
]

FOCAL_LENGTH_OPTIONS = [
    "14mm（超廣角，強空間感）",
    "24mm（廣角，環境敘事）",
    "35mm（人文廣角，自然視角）",
    "50mm（標準，接近人眼）",
    "85mm（人像壓縮，背景虛化）",
    "135mm（強壓縮，背景大虛化）",
    "200mm（望遠壓縮，抽離感）",
    "800mm（超望遠，極端壓縮）",
]

TIPS = {
    "Nano Banana Pro": [
        "✓ 指定電影攝影機（ARRI、RED、Fuji）",
        "✓ 加入皮膚毛孔、紋路等細節",
        "✓ 描述真實不完美的打光",
        "✓ 用底片名稱描述色調",
        "✗ 避免「超寫實」「完美肌膚」「高細節」",
    ],
    "Midjourney": [
        "✓ --style raw 降低 AI 感",
        "✓ 加入皮膚自然紋路描述",
        "✓ 精確指定光線方向與色溫",
        "✓ 標明拍攝媒材與鏡頭",
        "✗ 避免 flawless、perfect、stunning",
    ],
}

# ── Core function ──────────────────────────────────────────────────────────────

def build_prompt(subject, lighting, camera, lens, focal_length, mood, extra_list, platform):
    if not subject.strip():
        return "⚠️ 請填寫主體描述"

    extra_str = "、".join(extra_list) if extra_list else ""

    parts = [
        f"Subject: {subject}",
        f"Lighting: {lighting}" if lighting else None,
        f"Camera body: {camera}" if camera else None,
        f"Lens: {lens}" if lens else None,
        f"Focal length: {focal_length}" if focal_length else None,
        f"Mood/Color: {mood}" if mood else None,
        f"Extra details: {extra_str}" if extra_str else None,
    ]
    filled = "\n".join(p for p in parts if p)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=SYSTEM_PROMPTS[platform],
            messages=[{
                "role": "user",
                "content": (
                    f"Create a {platform} prompt. "
                    f"Goal: photographic, natural, not AI-looking. "
                    f"Advertising use.\n\n{filled}"
                )
            }]
        )
        return response.content[0].text
    except Exception as e:
        return f"❌ 錯誤：{str(e)}\n\n請確認 API.env 中有正確填入 ANTHROPIC_API_KEY。"


def get_tips(platform):
    return "\n".join(TIPS[platform])


# ── Gradio UI ──────────────────────────────────────────────────────────────────

with gr.Blocks(title="AI Image Prompt Helper") as demo:
    gr.Markdown("# 🎬 AI Image Prompt 建議工具")
    gr.Markdown("廣告用途 · 去 AI 感 · 支援 Nano Banana Pro 與 Midjourney")

    with gr.Row():
        platform = gr.Radio(
            choices=["Nano Banana Pro", "Midjourney"],
            value="Nano Banana Pro",
            label="選擇平台",
            scale=2
        )
        tips_box = gr.Textbox(
            label="去 AI 感技巧",
            value=get_tips("Nano Banana Pro"),
            lines=5,
            interactive=False,
            scale=3
        )

    platform.change(fn=get_tips, inputs=platform, outputs=tips_box)

    gr.Markdown("---")

    with gr.Row():
        with gr.Column():
            subject_in = gr.Textbox(
                label="主體 *（必填）",
                placeholder="例：穿白色洋裝的女生站在街角、男模特靠著牆",
                lines=2
            )
            lighting_in = gr.Dropdown(
                label="光線",
                choices=LIGHTING_OPTIONS,
                allow_custom_value=True,
                value=None,
            )
            camera_in = gr.Dropdown(
                label="攝影機 / 相機機身",
                choices=CAMERA_OPTIONS,
                allow_custom_value=True,
                value=None,
            )
            lens_in = gr.Dropdown(
                label="鏡頭品牌",
                choices=LENS_OPTIONS,
                allow_custom_value=True,
                value=None,
            )
            focal_in = gr.Dropdown(
                label="焦段",
                choices=FOCAL_LENGTH_OPTIONS,
                allow_custom_value=True,
                value=None,
            )

        with gr.Column():
            mood_in = gr.Dropdown(
                label="氛圍 / 色調",
                choices=MOOD_OPTIONS,
                allow_custom_value=True,
                value=None,
            )
            extra_in = gr.CheckboxGroup(
                label="其他細節（可複選）",
                choices=EXTRA_OPTIONS,
                value=[],
            )

    build_btn = gr.Button("✨ 生成提示詞", variant="primary", size="lg")

    build_output = gr.Textbox(
        label="生成結果（中文說明 + English Prompt）",
        lines=8,
    )

    build_btn.click(
        fn=build_prompt,
        inputs=[subject_in, lighting_in, camera_in, lens_in, focal_in, mood_in, extra_in, platform],
        outputs=build_output
    )

    gr.Markdown("---")
    gr.Markdown("💡 所有下拉選單都可以直接打字輸入自訂內容。")

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(), share=True)

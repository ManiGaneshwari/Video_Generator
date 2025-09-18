# 🎬 Video Generator

A professional, configurable slideshow generator that creates high-quality videos with animated text overlays, synchronized audio, and automatic subtitles – all with minimal effort.

## ✨ Features

- **Automated Processing** – No manual intervention required
- **Configurable Settings** – All options managed via simple YAML file
- **Text Animations** – Fade, slide, zoom, bounce, rotate, and more
- **Audio Support** – Use your own audio file OR generate narration from text
- **Multiple Resolutions** – Export in 1080p or 720p
- **Smart Image Scaling** – Fit or crop to 16:9 ratio automatically
- **Subtitles** – Generates .srt and .vtt subtitle files
- **Professional Codebase** – Modular, easy to extend and maintain



## 📂 Project Structure

```
project/
├── README.md
├── requirements.txt
├── main.py
├── config/
│   └── settings.yaml
├── data/
│   ├── input.txt          # Text content (optional)
│   ├── images/            # Your image files
│   │   ├── image1.jpg
│   │   ├── image2.png
│   │   └── ...
│   ├── audio.mp3          # Your audio file
│   └── output/            # Generated videos and files
├── src/
│   ├── __init__.py
│   ├── text_processor.py
│   ├── audio_generator.py
│   ├── video_generator.py
│   ├── subtitle_generator.py
│   ├── renderer.py
│   └── utils.py
├── tests/
│   └── ...
└── logs/
    └── app.log
```
## 🚀 Quick Start (Beginner Friendly)

### 1. Clone the Repository
```bash
git init
git clone https://github.com/ManiGaneshwari/Video_Generator.git
cd Video_Generator
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```


### 3. Prepare Your Data

**Place images in:**
```
data/images/
```

**Provide audio** (see [Audio Setup](#-audio-setup))

**(Optional) Add text in:**
```
data/input.txt
```

### 4. Run the Generator
```bash
python main.py
```

✅ **Output video will be saved inside:**
```
data/output/
```

## 🎵 Audio Setup

You can add narration or background audio in two ways:

### Option 1️⃣ – Use Your Own Audio File

1. Place your audio file (e.g., `narration.mp3`) in the `data/` folder.
2. Update `config/settings.yaml` file like this:

```yaml
# Audio Settings
audio:
  use_tts: false
  file: "data/narration.mp3"
```
- ✅ The slideshow will use your uploaded audio file.

### Option 2️⃣ – Generate Audio from Text (TTS)

1. Create a file `data/input.txt` with your script (one line per slide):
- Example:
```
Welcome to our presentation
This is slide 2
Final thoughts
```

2. Update `config/settings.yaml`:
```yaml
# Audio Settings
audio:
  generate_from_text: true   # If true, will use TTS instead of uploaded audio
  tts:
    language: "en"
    slow: false
```
- ✅ The program will automatically convert your text into audio using Google TTS.

  
👉 **Requires installing TTS libraries:**
```bash
pip install gtts pydub
```

⚠️ **Notes:**
- If `use_tts: false` and no audio file is found → ❌ Error
- If `generate_from_text: true` but `input.txt` is missing → ❌ Error

## ⚙️ Configuration

Edit `config/settings.yaml` to customize your slideshow.

### Video Settings
```yaml
video:
  resolution: "1080p"        # "1080p" or "720p"
  scaling_method: "fit"      # "fit" or "crop"
  fps: 24
```

### Text Settings
```yaml
text:
  enabled: true
  mode: "auto"               # "auto", "single", "per_image", "from_file"
  font_size: 60
  color: "white"
  animation:
    type: "fade_in"          # animation type
    duration: 1.5
```

### Supported Animations

- `fade_in`, `fade_in_out`
- `slide_from_left/right/top/bottom`
- `zoom_in`, `zoom_out`
- `bounce_in`, `pulse`, `rotate_in`
- `none` (static text)


## 📌 Example Workflow

1. Put your images inside `data/images/`.
2. Either:
   * Provide `data/narration.mp3` (update YAML), **OR**
   * Create `data/input.txt` (update YAML for TTS).
3. Run:
```bash
   python src/main.py
```



## 📹 Accessing Your Generated Video
✅ Correct Way
Your video is automatically saved in your project directory:

```project/
└── data/
    └── output/
        └── slideshow_1080p_crop.mp4
```


To open your video:
#### Option 1: From VS Code

- Right-click on the video file in VS Code Explorer

- Select "Reveal in File Explorer" (Windows) / "Reveal in Finder" (macOS)

- Double-click the video file to open with your default player

#### Option 2: Direct File Navigation

- Navigate to data/output/ folder in File Explorer/Finder

- Double-click slideshow_1080p_crop.mp4 to open with your default video player

#### Option 3: Terminal Commands

#### Windows
```
start data/output/slideshow_1080p_crop.mp4
```
#### macOS  
```
open data/output/slideshow_1080p_crop.mp4
```

#### Linux
```
xdg-open data/output/slideshow_1080p_crop.mp4
```


### ❌ Avoid VS Code Preview Issues
If you're using VS Code:

- Don't use the three dots (⋮) menu "Download" option in the video preview
- VS Code's download feature can corrupt the file pointer, especially for large videos
- Always access the original file from data/output/ folder instead

## ⏱️ Video Duration Logic
- Important: The video length is determined by the number of images, not the audio duration.


How It Works:

- Each image gets equal display time
- Total duration = Number of images × Time per slide
- Audio is fitted to match the total video length

Example:

```
10 images × 3 seconds per slide = 30-second video
```
Even if your audio file is 2 minutes long, the video will still be 30 seconds.
To Control Duration:

- Add more images → Longer video
- Remove images → Shorter video
- Adjust slide timing in config/settings.yaml:
  

```yaml
 video:
     slide_duration: 3.0  # seconds per image
```


#### 💡 Tip: Match your script length to your desired number of images for best synchronization.


## 🐞 Common Issues & Fixes

<details>
<summary><strong>1) ModuleNotFoundError: No module named 'moviepy.editor'</strong></summary>
  
```bash
pip uninstall moviepy -y
pip install moviepy==1.0.3
```
</details>

<details>
<summary><strong>2) ModuleNotFoundError: No module named 'yaml'</strong></summary>
  
```bash
pip install PyYAML
```
</details>
<details>
<summary> <strong>3) TTS Libraries Missing</strong></summary>
  
```bash
pip install gtts pydub
```
</details>
<details>
<summary> <strong>4) No audio available</strong></summary>
  
```
Ensure you placed audio.mp3 in data/ OR
Enable TTS in settings.yaml and create input.txt
```
</details>

## 📌 Tips

- Resize very large images for faster rendering
- Match audio duration to slideshow length for smoother sync
- Use `python main.py --validate` to check setup
- Use `--debug` for detailed logs

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Submit a pull request


# 🔗 Integration: LanguageFinder + Omnilingual ASR

## Overview

The LanguageFinder makes it easy to discover language codes for use with Omnilingual ASR. No more guessing codes or searching through documentation!

---

## Installation

```bash
# Install both packages
pip install omnilingual-asr
pip install omnilingual-finder  # Or use your local version

# Or from source (for development)
cd omnilingual-finder
pip install -e .
```

---

## Basic Integration

### Before (Manual Code Lookup)

```python
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline

# ❌ Hard to know which code to use
pipeline = ASRInferencePipeline(model_card="omniASR_LLM_7B")
audio_files = ["/path/to/audio1.flac"]
lang = ["hin_Deva"]  # Is this right? What if I want Hindi in Perso-Arabic?
transcriptions = pipeline.transcribe(audio_files, lang=lang)
```

### After (With LanguageFinder)

```python
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
from finder import LanguageFinder

# ✅ Easy discovery
finder = LanguageFinder()
hindi = finder.find("Hindi")
print(f"Using: {hindi.code} ({hindi.english_name}, {hindi.speaker_count:,} speakers)")

pipeline = ASRInferencePipeline(model_card="omniASR_LLM_7B")
audio_files = ["/path/to/audio1.flac"]
lang = [hindi.code]  # Guaranteed correct!
transcriptions = pipeline.transcribe(audio_files, lang=lang)
```

---

## Usage Patterns

### Pattern 1: Check Language Support

```python
from omnilingual_asr.models.wav2vec2_llama.lang_ids import supported_langs
from finder import LanguageFinder

finder = LanguageFinder()

# Check if a language is supported
def is_supported(language_name: str) -> bool:
    """Check if a language is supported by Omnilingual ASR"""
    lang = finder.find(language_name)
    if not lang:
        print(f"❌ '{language_name}' not found in database")
        return False
    
    if lang.code in supported_langs:
        print(f"✅ {lang.english_name} ({lang.code}) is supported!")
        print(f"   Speakers: {lang.speaker_count:,}" if lang.speaker_count else "")
        print(f"   Resource level: {lang.resource_level}")
        return True
    else:
        print(f"⚠️  {lang.english_name} ({lang.code}) not yet supported")
        # Suggest alternatives
        alternatives = finder.get_alternatives(lang.code)
        if alternatives:
            print(f"   Try these instead: {', '.join(a.english_name for a in alternatives[:3])}")
        return False

# Usage
is_supported("Hindi")
is_supported("Bhojpuri")
is_supported("Dothraki")  # Not a real language :)
```

### Pattern 2: Regional Language Selection

```python
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
from finder import LanguageFinder

def transcribe_regional_audio(audio_file: str, region: str):
    """Transcribe audio, automatically selecting best language for region"""
    finder = LanguageFinder()
    
    # Get all supported languages in the region
    languages = finder.search(region=region, sort_by="speakers")
    
    # Filter to only ASR-supported languages
    supported = [lang for lang in languages if lang.code in supported_langs]
    
    if not supported:
        print(f"❌ No supported languages found for region: {region}")
        return None
    
    # Use the most-spoken supported language
    best = supported[0]
    print(f"🎯 Selected: {best.english_name} ({best.code})")
    print(f"   Speakers: {best.speaker_count:,}" if best.speaker_count else "")
    
    # Transcribe
    pipeline = ASRInferencePipeline(model_card="omniASR_LLM_7B")
    transcription = pipeline.transcribe([audio_file], lang=[best.code])[0]
    
    return transcription

# Usage
text = transcribe_regional_audio("/path/to/audio.wav", region="Maharashtra")
print(f"Transcription: {text}")
```

### Pattern 3: Multi-Language Batch Processing

```python
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
from finder import LanguageFinder

def batch_transcribe_with_discovery(audio_language_pairs):
    """
    Transcribe multiple files with automatic language code discovery.
    
    Args:
        audio_language_pairs: List of (audio_path, language_name) tuples
    
    Example:
        pairs = [
            ("/audio/hindi.wav", "Hindi"),
            ("/audio/marathi.wav", "Marathi"),
            ("/audio/tamil.wav", "Tamil"),
        ]
    """
    finder = LanguageFinder()
    
    # Discover all language codes
    audio_files = []
    lang_codes = []
    
    for audio_path, language_name in audio_language_pairs:
        lang = finder.find(language_name)
        
        if not lang:
            print(f"⚠️  Skipping {audio_path}: '{language_name}' not found")
            continue
        
        if lang.code not in supported_langs:
            print(f"⚠️  Skipping {audio_path}: {lang.english_name} not supported yet")
            continue
        
        audio_files.append(audio_path)
        lang_codes.append(lang.code)
        print(f"✓ {audio_path} → {lang.english_name} ({lang.code})")
    
    # Batch transcribe
    if audio_files:
        pipeline = ASRInferencePipeline(model_card="omniASR_LLM_7B")
        transcriptions = pipeline.transcribe(
            audio_files, 
            lang=lang_codes, 
            batch_size=len(audio_files)
        )
        return list(zip(audio_files, transcriptions))
    
    return []

# Usage
pairs = [
    ("/audio/interview_hindi.wav", "Hindi"),
    ("/audio/speech_marathi.wav", "Marathi"),
    ("/audio/podcast_tamil.wav", "Tamil"),
]

results = batch_transcribe_with_discovery(pairs)
for audio, text in results:
    print(f"\n{audio}:")
    print(f"  {text}")
```

### Pattern 4: Interactive Language Selection

```python
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
from finder import LanguageFinder

def interactive_transcribe(audio_file: str):
    """Interactive language selection for transcription"""
    finder = LanguageFinder()
    
    # Ask user for region/language
    print("🎤 Audio Transcription Tool")
    print("=" * 50)
    
    # Option 1: By region
    print("\nOption 1: Select by region")
    region = input("Enter region (e.g., 'Maharashtra', 'Tamil Nadu'): ").strip()
    
    if region:
        languages = finder.search(region=region, sort_by="speakers", limit=10)
        languages = [l for l in languages if l.code in supported_langs]
        
        if languages:
            print(f"\nAvailable languages in {region}:")
            for i, lang in enumerate(languages, 1):
                speakers = f"{lang.speaker_count:,}" if lang.speaker_count else "?"
                print(f"  {i}. {lang.english_name} ({speakers} speakers)")
            
            choice = int(input("\nSelect language (number): "))
            selected = languages[choice - 1]
        else:
            print(f"No supported languages found in {region}")
            return None
    else:
        # Option 2: By name
        lang_name = input("Enter language name: ").strip()
        selected = finder.find(lang_name)
        
        if not selected or selected.code not in supported_langs:
            print(f"❌ Language not supported")
            return None
    
    print(f"\n✅ Selected: {selected.english_name} ({selected.code})")
    
    # Transcribe
    pipeline = ASRInferencePipeline(model_card="omniASR_LLM_7B")
    print("🎧 Transcribing...")
    transcription = pipeline.transcribe([audio_file], lang=[selected.code])[0]
    
    return transcription

# Usage
text = interactive_transcribe("/path/to/audio.wav")
print(f"\n📝 Transcription:\n{text}")
```

### Pattern 5: Fallback Strategy

```python
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
from finder import LanguageFinder

def transcribe_with_fallback(audio_file: str, language_name: str):
    """
    Transcribe with automatic fallback to similar languages.
    Useful when exact language isn't supported yet.
    """
    finder = LanguageFinder()
    
    # Try exact match
    lang = finder.find(language_name)
    if not lang:
        print(f"❌ Language '{language_name}' not found")
        return None
    
    # Check if supported
    if lang.code in supported_langs:
        print(f"✅ Using: {lang.english_name} ({lang.code})")
        use_code = lang.code
    else:
        print(f"⚠️  {lang.english_name} not supported yet")
        
        # Try alternatives (same script, nearby, high-resource)
        alternatives = finder.get_alternatives(lang.code)
        alternatives = [a for a in alternatives if a.code in supported_langs]
        
        if not alternatives:
            print(f"❌ No suitable alternatives found")
            return None
        
        use_code = alternatives[0].code
        print(f"📍 Using fallback: {alternatives[0].english_name} ({use_code})")
        print(f"   Reason: Same script, nearby region, {alternatives[0].speaker_count:,} speakers")
    
    # Transcribe
    pipeline = ASRInferencePipeline(model_card="omniASR_LLM_7B")
    transcription = pipeline.transcribe([audio_file], lang=[use_code])[0]
    
    return transcription

# Usage
text = transcribe_with_fallback("/audio/bhojpuri.wav", "Bhojpuri")
# If Bhojpuri not supported, might fallback to Hindi (same script, nearby)
```

---

## Helper Functions

### Utility: List All Supported Languages

```python
from omnilingual_asr.models.wav2vec2_llama.lang_ids import supported_langs
from finder import LanguageFinder

def list_supported_languages(region: str = None, script: str = None):
    """List all ASR-supported languages with metadata"""
    finder = LanguageFinder()
    
    # Get all languages
    if region:
        languages = finder.search(region=region)
    elif script:
        languages = finder.search(script=script)
    else:
        # All languages in finder
        languages = [finder.get(code) for code in supported_langs if finder.get(code)]
    
    # Filter to supported only
    languages = [l for l in languages if l and l.code in supported_langs]
    languages.sort(key=lambda x: -x.speaker_count if x.speaker_count else 0)
    
    print(f"🌍 Supported Languages: {len(languages)}")
    print("=" * 80)
    
    for lang in languages:
        speakers = f"{lang.speaker_count:,}" if lang.speaker_count else "?"
        resource = f"[{lang.resource_level}]"
        print(f"{lang.code:20} {lang.english_name:30} {speakers:>15} speakers {resource}")
    
    return languages

# Usage
print("\n=== All Devanagari Languages ===")
list_supported_languages(script="Devanagari")

print("\n=== All South Indian Languages ===")
list_supported_languages(region="South India")
```

### Utility: Validate Language Codes

```python
from omnilingual_asr.models.wav2vec2_llama.lang_ids import supported_langs
from finder import LanguageFinder

def validate_codes(codes: list) -> dict:
    """Validate a list of language codes"""
    finder = LanguageFinder()
    results = {
        "valid": [],
        "invalid": [],
        "unsupported": []
    }
    
    for code in codes:
        lang = finder.get(code)
        
        if not lang:
            results["invalid"].append(code)
            print(f"❌ {code}: Not found in database")
        elif code not in supported_langs:
            results["unsupported"].append(code)
            print(f"⚠️  {code}: {lang.english_name} exists but not supported by ASR")
        else:
            results["valid"].append(code)
            print(f"✅ {code}: {lang.english_name}")
    
    return results

# Usage
codes_to_check = ["hin_Deva", "eng_Latn", "xyz_Fake", "bho_Deva"]
validation = validate_codes(codes_to_check)
print(f"\nValid: {len(validation['valid'])}, Invalid: {len(validation['invalid'])}")
```

---

## Advanced: Build ASR Language Selector UI

```python
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
from finder import LanguageFinder

class ASRLanguageSelectorApp:
    """Simple GUI for language selection + transcription"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Omnilingual ASR - Language Selector")
        
        self.finder = LanguageFinder()
        self.pipeline = None
        
        # Region selection
        ttk.Label(root, text="Select Region:").grid(row=0, column=0, padx=10, pady=10)
        self.region_var = tk.StringVar()
        self.region_combo = ttk.Combobox(root, textvariable=self.region_var, width=30)
        self.region_combo['values'] = ["Maharashtra", "Tamil Nadu", "Karnataka", "Gujarat", 
                                       "West Bengal", "Punjab", "Andhra Pradesh"]
        self.region_combo.grid(row=0, column=1, padx=10, pady=10)
        self.region_combo.bind('<<ComboboxSelected>>', self.on_region_selected)
        
        # Language selection
        ttk.Label(root, text="Select Language:").grid(row=1, column=0, padx=10, pady=10)
        self.lang_var = tk.StringVar()
        self.lang_combo = ttk.Combobox(root, textvariable=self.lang_var, width=30)
        self.lang_combo.grid(row=1, column=1, padx=10, pady=10)
        
        # File selection
        ttk.Button(root, text="Select Audio File", command=self.select_file).grid(row=2, column=0, columnspan=2, pady=10)
        self.file_label = ttk.Label(root, text="No file selected")
        self.file_label.grid(row=3, column=0, columnspan=2)
        
        # Transcribe button
        ttk.Button(root, text="Transcribe", command=self.transcribe).grid(row=4, column=0, columnspan=2, pady=20)
        
        # Output
        self.output_text = tk.Text(root, height=10, width=60)
        self.output_text.grid(row=5, column=0, columnspan=2, padx=10, pady=10)
        
        self.audio_file = None
        self.languages = []
    
    def on_region_selected(self, event):
        region = self.region_var.get()
        self.languages = self.finder.search(region=region, sort_by="speakers")
        
        # Filter to supported only
        from omnilingual_asr.models.wav2vec2_llama.lang_ids import supported_langs
        self.languages = [l for l in self.languages if l.code in supported_langs]
        
        # Update combo
        self.lang_combo['values'] = [f"{l.english_name} ({l.code})" for l in self.languages]
        if self.languages:
            self.lang_combo.current(0)
    
    def select_file(self):
        self.audio_file = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[("Audio Files", "*.wav *.flac *.mp3 *.m4a")]
        )
        if self.audio_file:
            self.file_label.config(text=self.audio_file)
    
    def transcribe(self):
        if not self.audio_file:
            messagebox.showerror("Error", "Please select an audio file")
            return
        
        if not self.lang_var.get():
            messagebox.showerror("Error", "Please select a language")
            return
        
        # Get selected language
        lang_idx = self.lang_combo.current()
        if lang_idx < 0:
            messagebox.showerror("Error", "Invalid language selection")
            return
        
        selected_lang = self.languages[lang_idx]
        
        try:
            # Initialize pipeline if needed
            if not self.pipeline:
                self.output_text.insert(tk.END, "Loading ASR model...\n")
                self.root.update()
                self.pipeline = ASRInferencePipeline(model_card="omniASR_LLM_7B")
            
            # Transcribe
            self.output_text.insert(tk.END, f"\nTranscribing as {selected_lang.english_name}...\n")
            self.root.update()
            
            transcription = self.pipeline.transcribe(
                [self.audio_file], 
                lang=[selected_lang.code]
            )[0]
            
            self.output_text.insert(tk.END, f"\n✅ Transcription:\n{transcription}\n")
            
        except Exception as e:
            messagebox.showerror("Error", f"Transcription failed: {str(e)}")

# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = ASRLanguageSelectorApp(root)
    root.mainloop()
```

---

## Summary

The LanguageFinder integration makes Omnilingual ASR **dramatically more accessible**:

### Before
```python
# ❌ Manual, error-prone
lang = ["hin_Deva"]  # Which script? Is this right?
```

### After
```python
# ✅ Intuitive, verified
hindi = finder.find("Hindi")
lang = [hindi.code]  # Always correct!
```

### Key Benefits

1. **✅ Discover codes easily** - No more documentation hunting
2. **✅ Validate before use** - Check if language is supported
3. **✅ Smart fallbacks** - Suggest alternatives if not supported
4. **✅ Regional browsing** - Find all languages in an area
5. **✅ Rich metadata** - Speaker counts, resource levels, scripts

### Integration Points

- ✅ Before `pipeline.transcribe()` - Discover correct codes
- ✅ After `supported_langs` import - Validate against supported list
- ✅ In UIs - Region/language pickers with autocomplete
- ✅ In batch scripts - Automated code lookup
- ✅ In documentation - Better examples for users

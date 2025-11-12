"""
Simple examples: Using LanguageFinder with Omnilingual ASR
"""

# ============================================================================
# Example 1: Simple transcription with language name
# ============================================================================

from finder.asr_integration import SmartASRPipeline

pipeline = SmartASRPipeline()

# Just specify the language name - no need to know the code!
text = pipeline.transcribe("audio.wav", language="Hindi")
print(text)


# ============================================================================
# Example 2: Regional auto-selection
# ============================================================================

from finder.asr_integration import SmartASRPipeline

pipeline = SmartASRPipeline()

# Automatically selects most common language in Maharashtra (Marathi)
text = pipeline.transcribe("audio.wav", region="Maharashtra")
print(text)


# ============================================================================
# Example 3: Batch transcription with different languages
# ============================================================================

from finder.asr_integration import SmartASRPipeline

pipeline = SmartASRPipeline()

# Each file gets its own language
pairs = [
    ("hindi_speech.wav", "Hindi"),
    ("tamil_interview.wav", "Tamil"),
    ("marathi_podcast.wav", "Marathi"),
]

results = pipeline.transcribe_batch(pairs)

for audio, code, text in results:
    print(f"\n{audio} ({code}):")
    print(f"  {text}")


# ============================================================================
# Example 4: Check if language is supported
# ============================================================================

from finder.asr_integration import SmartASRPipeline

pipeline = SmartASRPipeline()

if pipeline.is_supported("Bhojpuri"):
    text = pipeline.transcribe("audio.wav", language="Bhojpuri")
else:
    print("Bhojpuri not supported yet - use fallback")
    text = pipeline.transcribe("audio.wav", language="Bhojpuri", fallback=True)


# ============================================================================
# Example 5: List supported languages in a region
# ============================================================================

from finder.asr_integration import SmartASRPipeline

pipeline = SmartASRPipeline()

print("Supported languages in South India:")
languages = pipeline.list_supported(region="South India")

for lang in languages:
    speakers = f"{lang.speaker_count:,}" if lang.speaker_count else "?"
    print(f"  {lang.english_name:20} ({lang.code:15}) - {speakers} speakers")


# ============================================================================
# Example 6: One-liner convenience function
# ============================================================================

from finder.asr_integration import transcribe_smart

# Simplest possible usage
text = transcribe_smart("audio.wav", language="Hindi")
print(text)


# ============================================================================
# Example 7: Integration with existing code
# ============================================================================

# Before (manual code lookup):
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline

pipeline = ASRInferencePipeline(model_card="omniASR_LLM_7B")
transcription = pipeline.transcribe(["audio.wav"], lang=["hin_Deva"])[0]

# After (with language discovery):
from finder import LanguageFinder
from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline

finder = LanguageFinder()
hindi = finder.find("Hindi")

pipeline = ASRInferencePipeline(model_card="omniASR_LLM_7B")
transcription = pipeline.transcribe(["audio.wav"], lang=[hindi.code])[0]


# ============================================================================
# Example 8: Get language suggestions for UI
# ============================================================================

from finder.asr_integration import SmartASRPipeline

pipeline = SmartASRPipeline()

# User selects region in UI
user_region = "Maharashtra"
suggestions = pipeline.suggest_languages(user_region)

print(f"Recommended languages for {user_region}:")
for lang in suggestions:
    print(f"  • {lang.english_name} ({lang.speaker_count:,} speakers)")


# ============================================================================
# Example 9: Validation before batch processing
# ============================================================================

from finder.asr_integration import SmartASRPipeline

pipeline = SmartASRPipeline()

# Check all languages before starting expensive batch job
languages_to_check = ["Hindi", "Tamil", "Dothraki", "Klingon"]

supported = []
unsupported = []

for lang in languages_to_check:
    if pipeline.is_supported(lang):
        supported.append(lang)
    else:
        unsupported.append(lang)

print(f"✅ Supported: {supported}")
print(f"❌ Unsupported: {unsupported}")

# Proceed with only supported languages
pairs = [(f"audio_{lang.lower()}.wav", lang) for lang in supported]
results = pipeline.transcribe_batch(pairs)


# ============================================================================
# Example 10: Fallback strategy for new languages
# ============================================================================

from finder.asr_integration import SmartASRPipeline

pipeline = SmartASRPipeline()

# Try Bhojpuri, fallback to Hindi if not supported
text = pipeline.transcribe(
    "bhojpuri_audio.wav",
    language="Bhojpuri",
    fallback=True,  # Automatically uses Hindi (same script, nearby)
    verbose=True    # Shows what fallback was chosen
)
# Output:
# ⚠️  Bhojpuri (bho_Deva) not supported yet
#    📍 Using fallback: Hindi (hin_Deva)
#       Reason: Same script, nearby region
#       Speakers: 341,000,000
# 🎧 Transcribing with Hindi (hin_Deva)...
# ✅ Done!
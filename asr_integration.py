"""
Convenience wrapper: LanguageFinder + Omnilingual ASR integration
Makes transcription with language discovery seamless
"""
from typing import List, Optional, Union, Tuple
from pathlib import Path

try:
    from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
    from omnilingual_asr.models.wav2vec2_llama.lang_ids import supported_langs
    ASR_AVAILABLE = True
except ImportError:
    ASR_AVAILABLE = False
    print("⚠️  omnilingual-asr not installed. Install with: pip install omnilingual-asr")

from finder.core import LanguageFinder, Language


class SmartASRPipeline:
    """
    ASR Pipeline with integrated language discovery.
    
    Makes it easy to transcribe without knowing exact language codes.
    
    Example:
        pipeline = SmartASRPipeline()
        
        # By language name
        text = pipeline.transcribe("audio.wav", language="Hindi")
        
        # By region (auto-selects most common language)
        text = pipeline.transcribe("audio.wav", region="Maharashtra")
        
        # Multiple files with auto-discovery
        texts = pipeline.transcribe_batch([
            ("audio1.wav", "Hindi"),
            ("audio2.wav", "Tamil"),
            ("audio3.wav", "Marathi"),
        ])
    """
    
    def __init__(self, model_card: str = "omniASR_LLM_7B"):
        """
        Initialize pipeline with language finder.
        
        Args:
            model_card: ASR model to use
        """
        if not ASR_AVAILABLE:
            raise ImportError(
                "omnilingual-asr not installed. "
                "Install with: pip install omnilingual-asr"
            )
        
        self.finder = LanguageFinder()
        self.pipeline = ASRInferencePipeline(model_card=model_card)
        self.model_card = model_card
    
    def transcribe(
        self,
        audio_file: Union[str, Path],
        language: Optional[str] = None,
        region: Optional[str] = None,
        language_code: Optional[str] = None,
        fallback: bool = True,
        verbose: bool = True
    ) -> str:
        """
        Transcribe a single audio file.
        
        Args:
            audio_file: Path to audio file
            language: Language name (e.g., "Hindi", "Tamil")
            region: Geographic region (e.g., "Maharashtra")
            language_code: Exact language code (e.g., "hin_Deva")
            fallback: If True, use similar language if exact match not supported
            verbose: Print status messages
        
        Returns:
            Transcribed text
        
        Example:
            # By name
            text = pipeline.transcribe("audio.wav", language="Hindi")
            
            # By region
            text = pipeline.transcribe("audio.wav", region="Maharashtra")
            
            # By code (if you know it)
            text = pipeline.transcribe("audio.wav", language_code="hin_Deva")
        """
        # Resolve language
        code, lang_obj = self._resolve_language(
            language=language,
            region=region,
            language_code=language_code,
            fallback=fallback,
            verbose=verbose
        )
        
        if not code:
            raise ValueError("Could not resolve language. Specify language, region, or language_code.")
        
        # Transcribe
        if verbose:
            print(f"🎧 Transcribing with {lang_obj.english_name} ({code})...")
        
        transcription = self.pipeline.transcribe([str(audio_file)], lang=[code])[0]
        
        if verbose:
            print(f"✅ Done!")
        
        return transcription
    
    def transcribe_batch(
        self,
        audio_language_pairs: List[Tuple[Union[str, Path], str]],
        batch_size: int = 4,
        fallback: bool = True,
        verbose: bool = True
    ) -> List[Tuple[str, str, str]]:
        """
        Transcribe multiple audio files with automatic language discovery.
        
        Args:
            audio_language_pairs: List of (audio_path, language_name) tuples
            batch_size: Number of files to process at once
            fallback: Use similar language if exact match not supported
            verbose: Print progress
        
        Returns:
            List of (audio_path, language_code, transcription) tuples
        
        Example:
            pairs = [
                ("audio1.wav", "Hindi"),
                ("audio2.wav", "Marathi"),
                ("audio3.wav", "Tamil"),
            ]
            results = pipeline.transcribe_batch(pairs)
            
            for audio, code, text in results:
                print(f"{audio} ({code}): {text}")
        """
        results = []
        
        # Resolve all language codes first
        audio_files = []
        lang_codes = []
        
        for audio_path, language_name in audio_language_pairs:
            code, lang_obj = self._resolve_language(
                language=language_name,
                fallback=fallback,
                verbose=False  # Don't spam during batch
            )
            
            if not code:
                if verbose:
                    print(f"⚠️  Skipping {audio_path}: Could not resolve '{language_name}'")
                continue
            
            audio_files.append(str(audio_path))
            lang_codes.append(code)
            
            if verbose:
                print(f"✓ {Path(audio_path).name} → {lang_obj.english_name} ({code})")
        
        if not audio_files:
            return []
        
        # Batch transcribe
        if verbose:
            print(f"\n🎧 Transcribing {len(audio_files)} files (batch_size={batch_size})...")
        
        transcriptions = self.pipeline.transcribe(
            audio_files,
            lang=lang_codes,
            batch_size=batch_size
        )
        
        if verbose:
            print("✅ Done!")
        
        return list(zip(audio_files, lang_codes, transcriptions))
    
    def _resolve_language(
        self,
        language: Optional[str] = None,
        region: Optional[str] = None,
        language_code: Optional[str] = None,
        fallback: bool = True,
        verbose: bool = True
    ) -> Tuple[Optional[str], Optional[Language]]:
        """
        Resolve language specification to a supported code.
        
        Returns:
            (language_code, Language object) or (None, None) if not found
        """
        # Option 1: Exact code provided
        if language_code:
            lang = self.finder.get(language_code)
            if not lang:
                if verbose:
                    print(f"⚠️  Language code '{language_code}' not found")
                return None, None
            
            if language_code not in supported_langs:
                if verbose:
                    print(f"⚠️  {lang.english_name} ({language_code}) not supported by ASR")
                if fallback:
                    return self._find_fallback(lang, verbose)
                return None, None
            
            return language_code, lang
        
        # Option 2: Language name provided
        if language:
            lang = self.finder.find(language)
            if not lang:
                if verbose:
                    print(f"❌ Language '{language}' not found in database")
                return None, None
            
            if lang.code in supported_langs:
                if verbose:
                    print(f"✅ Using: {lang.english_name} ({lang.code})")
                return lang.code, lang
            else:
                if verbose:
                    print(f"⚠️  {lang.english_name} ({lang.code}) not supported yet")
                if fallback:
                    return self._find_fallback(lang, verbose)
                return None, None
        
        # Option 3: Region provided (use most common language)
        if region:
            languages = self.finder.search(region=region, sort_by="speakers")
            languages = [l for l in languages if l.code in supported_langs]
            
            if not languages:
                if verbose:
                    print(f"❌ No supported languages found in region: {region}")
                return None, None
            
            best = languages[0]
            if verbose:
                print(f"🎯 Auto-selected for {region}: {best.english_name} ({best.code})")
                if best.speaker_count:
                    print(f"   ({best.speaker_count:,} speakers)")
            
            return best.code, best
        
        return None, None
    
    def _find_fallback(
        self, 
        lang: Language, 
        verbose: bool = True
    ) -> Tuple[Optional[str], Optional[Language]]:
        """Find a supported fallback language"""
        alternatives = self.finder.get_alternatives(lang.code)
        alternatives = [a for a in alternatives if a.code in supported_langs]
        
        if not alternatives:
            if verbose:
                print(f"   No suitable fallback found")
            return None, None
        
        fallback = alternatives[0]
        if verbose:
            print(f"   📍 Using fallback: {fallback.english_name} ({fallback.code})")
            print(f"      Reason: Same script, nearby region")
            if fallback.speaker_count:
                print(f"      Speakers: {fallback.speaker_count:,}")
        
        return fallback.code, fallback
    
    def is_supported(self, language: str) -> bool:
        """
        Check if a language is supported.
        
        Args:
            language: Language name or code
        
        Returns:
            True if supported, False otherwise
        
        Example:
            if pipeline.is_supported("Hindi"):
                text = pipeline.transcribe("audio.wav", language="Hindi")
        """
        lang = self.finder.find(language)
        return lang is not None and lang.code in supported_langs
    
    def list_supported(
        self,
        region: Optional[str] = None,
        script: Optional[str] = None,
        limit: int = 20
    ) -> List[Language]:
        """
        List supported languages.
        
        Args:
            region: Filter by region
            script: Filter by script
            limit: Maximum results
        
        Returns:
            List of supported Language objects
        
        Example:
            # All supported Devanagari languages
            langs = pipeline.list_supported(script="Devanagari")
            for lang in langs:
                print(f"{lang.code}: {lang.english_name}")
        """
        if region:
            languages = self.finder.search(region=region, sort_by="speakers")
        elif script:
            languages = self.finder.search(script=script, sort_by="speakers")
        else:
            # Get all languages
            languages = [self.finder.get(code) for code in supported_langs]
            languages = [l for l in languages if l]
            languages.sort(key=lambda x: -x.speaker_count if x.speaker_count else 0)
        
        # Filter to supported
        languages = [l for l in languages if l.code in supported_langs]
        
        return languages[:limit]
    
    def suggest_languages(self, region: str) -> List[Language]:
        """
        Suggest best languages for a region.
        
        Args:
            region: Geographic region
        
        Returns:
            List of recommended Language objects (supported only)
        
        Example:
            suggestions = pipeline.suggest_languages("Maharashtra")
            print("Recommended languages:")
            for lang in suggestions:
                print(f"  - {lang.english_name} ({lang.speaker_count:,} speakers)")
        """
        languages = self.finder.search(region=region, sort_by="speakers")
        languages = [l for l in languages if l.code in supported_langs]
        return languages[:5]  # Top 5


# Convenience function
def transcribe_smart(
    audio_file: Union[str, Path],
    language: Optional[str] = None,
    region: Optional[str] = None,
    model_card: str = "omniASR_LLM_7B"
) -> str:
    """
    One-liner transcription with language discovery.
    
    Args:
        audio_file: Path to audio
        language: Language name (e.g., "Hindi")
        region: Region name (e.g., "Maharashtra")
        model_card: Model to use
    
    Returns:
        Transcribed text
    
    Example:
        # Quick transcription
        text = transcribe_smart("audio.wav", language="Hindi")
        
        # Or by region
        text = transcribe_smart("audio.wav", region="Tamil Nadu")
    """
    pipeline = SmartASRPipeline(model_card=model_card)
    return pipeline.transcribe(audio_file, language=language, region=region)
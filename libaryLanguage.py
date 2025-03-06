import re
import unicodedata
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter
import logging
import os
import importlib.util

logger = logging.getLogger(__name__)

class LibraryLanguageDetector:
    def __init__(self, use_libraries=True):
        self.setup_method_weights()
        self.use_libraries = use_libraries
        self.initialize_libraries()
        
    def initialize_libraries(self):
        """Initialize available language detection libraries"""
        self.available_libraries = {}
        
        # Try to load langdetect
        try:
            import langdetect
            from langdetect import detect, DetectorFactory
            from langdetect.detector import Detector
            
            # Set seed for consistent results
            DetectorFactory.seed = 0
            
            self.available_libraries['langdetect'] = {
                'module': langdetect,
                'factory': DetectorFactory()
            }
            logger.info("Loaded langdetect library")
        except ImportError:
            logger.info("langdetect library not available")
        except Exception as e:
            logger.warning(f"Error initializing langdetect: {e}")
            
        # Try to load fastText
        try:
            import fasttext
            
            # Check if model file exists
            model_path = "lid.176.ftz"
            if os.path.exists(model_path):
                try:
                    model = fasttext.load_model(model_path)
                    self.available_libraries['fasttext'] = {
                        'module': fasttext,
                        'model': model
                    }
                    logger.info("Loaded fastText model")
                except Exception as e:
                    logger.warning(f"Error loading fastText model: {e}")
            else:
                logger.info("fastText model file not found")
        except ImportError:
            logger.info("fastText library not available")
        except Exception as e:
            logger.warning(f"Error initializing fastText: {e}")
            
        # Try to load Lingua
        try:
            from lingua import Language, LanguageDetectorBuilder
            
            # Build detector with common languages
            languages = [
                Language.ENGLISH, Language.FRENCH, Language.GERMAN, 
                Language.SPANISH, Language.PORTUGUESE, Language.ITALIAN,
                Language.DUTCH, Language.POLISH, Language.DANISH,
                Language.FINNISH, Language.SWEDISH, Language.TURKISH,
                Language.INDONESIAN, Language.VIETNAMESE, Language.GREEK,
                Language.ARABIC, Language.RUSSIAN, Language.CHINESE,
                Language.JAPANESE, Language.KOREAN
            ]
            
            try:
                detector = LanguageDetectorBuilder.from_languages(*languages).build()
                self.available_libraries['lingua'] = {
                    'module': 'lingua',
                    'detector': detector,
                    'language_map': {
                        Language.ENGLISH: 'en', Language.FRENCH: 'fr',
                        Language.GERMAN: 'de', Language.SPANISH: 'es',
                        Language.PORTUGUESE: 'pt', Language.ITALIAN: 'it',
                        Language.DUTCH: 'nl', Language.POLISH: 'pl',
                        Language.DANISH: 'da', Language.FINNISH: 'fi',
                        Language.SWEDISH: 'sv', Language.TURKISH: 'tr',
                        Language.INDONESIAN: 'id', Language.VIETNAMESE: 'vi',
                        Language.GREEK: 'el', Language.ARABIC: 'ar',
                        Language.RUSSIAN: 'ru', Language.CHINESE: 'zh',
                        Language.JAPANESE: 'ja', Language.KOREAN: 'ko'
                    }
                }
                logger.info("Loaded Lingua library")
            except Exception as e:
                logger.warning(f"Error initializing Lingua detector: {e}")
        except ImportError:
            logger.info("Lingua library not available")
        except Exception as e:
            logger.warning(f"Error importing Lingua: {e}")
            
        # Try to load pycld2
        try:
            import pycld2
            self.available_libraries['pycld2'] = {
                'module': pycld2
            }
            logger.info("Loaded pycld2 library")
        except ImportError:
            logger.info("pycld2 library not available")
        except Exception as e:
            logger.warning(f"Error initializing pycld2: {e}")
            
        # Try to load polyglot
        try:
            from polyglot.detect import Detector as PolyglotDetector
            self.available_libraries['polyglot'] = {
                'module': 'polyglot'
            }
            logger.info("Loaded polyglot library")
        except ImportError:
            logger.info("polyglot library not available")
        except Exception as e:
            logger.warning(f"Error initializing polyglot: {e}")
            
        logger.info(f"Initialized {len(self.available_libraries)} language detection libraries")
 
    def setup_method_weights(self):
        """Setup weights for different detection methods"""
        self.method_weights = {
               # Library weights
            'langdetect': 0.8,     # Good general-purpose detector
            'fasttext': 0.85,      # Excellent for many languages
            'cld3': 0.85,          # Google's detector: very good
            'pycld2': 0.8,         # CLD2 detector: good but older
            'lingua': 0.85,        # Good for European languages
            'polyglot': 0.75       # Decent detector but less maintained
        }
    
    def detect_language(self, text: str, region: str = None, ip_country: str = None, 
                       user_history: List[str] = None) -> Dict[str, Any]:
        """
        Main method to detect language using multiple signals
        
        Args:
            text: Text to analyze
            region: Region/timezone info, e.g. 'Asia/Kolkata'
            ip_country: Country code from IP
            user_history: Previous detected languages
            
        Returns:
            Dict with detected language, confidence, methods used
        """
        # Normalize text
        cleaned_text = self._normalize_text(text)
        
        # Track signals with confidence values
        signals = []
    
             
        #  Use available libraries if enabled
        if self.use_libraries:
            lib_signals = self._detect_with_libraries(cleaned_text)
            signals.extend(lib_signals)
   
        
        # If no signals were found, default to English with low confidence
        if not signals:
            return {
                'language': 'en',
                'confidence': 0.2,
                'methods': ['default'],
                'reliable': False
            }
            
        # Combine signals with a weighted voting system
        final_lang, confidence, methods = self._combine_signals(signals)
        
        return {
            'language': final_lang, 
            'confidence': confidence,
            'methods': methods,
            'reliable': confidence > 0.7
        }
    
    def _detect_with_libraries(self, text: str) -> List[Tuple[str, str, float]]:
        """Use available language detection libraries"""
        if not text or len(text.strip()) < 3:
            return []
            
        library_signals = []
        
        # 1. Try langdetect
        if 'langdetect' in self.available_libraries:
            try:
                langdetect_result = self._detect_with_langdetect(text)
                if langdetect_result[0]:  # If language was detected
                    lang, conf = langdetect_result
                    library_signals.append(('langdetect', lang, conf * self.method_weights['langdetect']))
            except Exception as e:
                logger.warning(f"Error with langdetect: {e}")
                
        # 2. Try fastText
        if 'fasttext' in self.available_libraries:
            try:
                fasttext_result = self._detect_with_fasttext(text)
                if fasttext_result[0]:  # If language was detected
                    lang, conf = fasttext_result
                    library_signals.append(('fasttext', lang, conf * self.method_weights['fasttext']))
            except Exception as e:
                logger.warning(f"Error with fastText: {e}")
                
        # 3. Try CLD3
        if 'cld3' in self.available_libraries:
            try:
                cld3_result = self._detect_with_cld3(text)
                if cld3_result[0]:  # If language was detected
                    lang, conf = cld3_result
                    library_signals.append(('cld3', lang, conf * self.method_weights['cld3']))
            except Exception as e:
                logger.warning(f"Error with CLD3: {e}")
                
        # 4. Try Lingua
        if 'lingua' in self.available_libraries:
            try:
                lingua_result = self._detect_with_lingua(text)
                if lingua_result[0]:  # If language was detected
                    lang, conf = lingua_result
                    library_signals.append(('lingua', lang, conf * self.method_weights['lingua']))
            except Exception as e:
                logger.warning(f"Error with Lingua: {e}")
                
        # 5. Try pyCLD2
        if 'pycld2' in self.available_libraries:
            try:
                pycld2_result = self._detect_with_pycld2(text)
                if pycld2_result[0]:  # If language was detected
                    lang, conf = pycld2_result
                    library_signals.append(('pycld2', lang, conf * self.method_weights['pycld2']))
            except Exception as e:
                logger.warning(f"Error with pyCLD2: {e}")
                
        # 6. Try polyglot
        if 'polyglot' in self.available_libraries:
            try:
                polyglot_result = self._detect_with_polyglot(text)
                if polyglot_result[0]:  # If language was detected
                    lang, conf = polyglot_result
                    library_signals.append(('polyglot', lang, conf * self.method_weights['polyglot']))
            except Exception as e:
                logger.warning(f"Error with polyglot: {e}")
                
        return library_signals
    
    def _detect_with_langdetect(self, text: str) -> Tuple[str, float]:
        """Detect language using langdetect library"""
        if 'langdetect' not in self.available_libraries:
            return "", 0.0
            
        lib_info = self.available_libraries['langdetect']
        langdetect = lib_info['module']
        factory = lib_info['factory']
        
        try:
            # For very short texts, add some padding to help langdetect
            padded_text = text
            if len(text.split()) < 3:
                # Repeat the text to give langdetect more to work with
                padded_text = text + " " + text
            
            # Try using Detector for probabilities
            try:
                detector = langdetect.detector.Detector(factory)
                detector.append(padded_text)
                detector.detect()
                
                probs = detector.get_probabilities()
                if probs and len(probs) > 0:
                    best_lang = probs[0]
                    return best_lang.lang, best_lang.prob
            except Exception as e:
                     
                logger.debug(f"Error with langdetect detector: {e}")
                
            # Fallback to simple detection
            try:
                lang = langdetect.detect(padded_text)
                return lang, 0.5  # Medium confidence since no probability available
            except langdetect.LangDetectException as e:
                
                    logger.debug(f"Error with langdetect detection: {e}")
                    
        except Exception as e:
            logger.warning(f"Unexpected error with langdetect: {e}")
            
        return "", 0.0
        
    def _detect_with_fasttext(self, text: str) -> Tuple[str, float]:
        """Detect language using fastText library"""
        if 'fasttext' not in self.available_libraries:
            return "", 0.0
            
        lib_info = self.available_libraries['fasttext']
        model = lib_info['model']
        
        try:
            # Clean text for fastText
            cleaned_text = text.replace('\n', ' ').strip()
            
            # For very short texts, duplicate to give more signal
            if len(cleaned_text.split()) < 3:
                cleaned_text = cleaned_text + " " + cleaned_text
                
            # Get predictions
            predictions = model.predict(cleaned_text, k=3)  # Get top 3 predictions
            if predictions and len(predictions) == 2:
                labels, probs = predictions
                
                if labels and probs and len(labels) > 0 and len(probs) > 0:
                    # Extract language code (format: __label__en)
                    lang_code = labels[0].replace('__label__', '')
                    confidence = float(probs[0])
                    
                    # Adjust confidence for very short texts
                    if len(text.split()) < 3:
                        confidence *= 0.8  # Reduce confidence for very short texts
                        
                    return lang_code, confidence
                    
        except Exception as e:
            logger.warning(f"Error with fastText detection: {e}")
            
        return "", 0.0
        
    def _detect_with_lingua(self, text: str) -> Tuple[str, float]:
        """Detect language using Lingua"""
        if 'lingua' not in self.available_libraries:
            return "", 0.0
            
        lib_info = self.available_libraries['lingua']
        detector = lib_info['detector']
        language_map = lib_info['language_map']
        
        try:
            # For very short texts, duplicate to give more signal
            padded_text = text
            if len(text.split()) < 3:
                padded_text = text + " " + text
                
            # Get confidence values
            confidence_values = detector.compute_language_confidence_values(padded_text)
            
            if confidence_values and len(confidence_values) > 0:
                # Get highest confidence language
                highest = confidence_values[0]
                lang_code = language_map.get(highest.language, 'en')
                confidence = highest.value
                
                # Adjust confidence for very short texts
                if len(text.split()) < 3:
                    confidence *= 0.8
                    
                return lang_code, confidence
                
        except Exception as e:
            logger.warning(f"Error with Lingua detection: {e}")
            
        return "", 0.0
        
    def _detect_with_pycld2(self, text: str) -> Tuple[str, float]:
        """Detect language using pyCLD2"""
        if 'pycld2' not in self.available_libraries:
            return "", 0.0
            
        pycld2 = self.available_libraries['pycld2']['module']
        
        try:
            # For very short texts, duplicate to give more signal
            padded_text = text
            if len(text.split()) < 3:
                padded_text = text + " " + text
                
            # Detect language
            is_reliable, text_bytes, details = pycld2.detect(padded_text)
            
            if details and len(details) > 0:
                # Get top language
                lang_code = details[0][1]
                confidence = details[0][2] / 100.0  # Convert percentage to 0-1 scale
                
                # Adjust confidence based on reliability flag
                if not is_reliable:
                    confidence *= 0.7
                    
                # Adjust confidence for very short texts
                if len(text.split()) < 3:
                    confidence *= 0.8
                    
                return lang_code, confidence
                
        except Exception as e:
            logger.warning(f"Error with pyCLD2 detection: {e}")
            
        return "", 0.0
        
    def _detect_with_polyglot(self, text: str) -> Tuple[str, float]:
        """Detect language using polyglot"""
        if 'polyglot' not in self.available_libraries:
            return "", 0.0
            
        try:
            from polyglot.detect import Detector as PolyglotDetector
            
            # For very short texts, duplicate to give more signal
            padded_text = text
            if len(text.split()) < 3:
                padded_text = text + " " + text
                
            # Detect language
            detector = PolyglotDetector(padded_text)
            
            # Get top language
            if detector.languages and len(detector.languages) > 0:
                top_lang = detector.languages[0]
                lang_code = top_lang.code
                confidence = top_lang.confidence
                
                # Adjust confidence for very short texts
                if len(text.split()) < 3:
                    confidence *= 0.8
                    
                return lang_code, confidence
                
        except Exception as e:
            logger.warning(f"Error with polyglot detection: {e}")
            
        return "", 0.0
    


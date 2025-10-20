"""Contextual Translation Engine with Context Awareness and Slang Support"""
import re
import logging
from typing import List, Tuple, Dict, Optional
from collections import deque
from langdetect import detect, detect_langs, LangDetectException

log = logging.getLogger("Translator")

class ContextualTranslationEngine:
    """Advanced contextual translation with slang support and context awareness"""
    
    def __init__(self):
        self.context_history = deque(maxlen=10)  # Keep last 10 phrases for context
        self.conversation_context = {}  # Topic and domain detection
        
        # Comprehensive slang database (expandable)
        self.slang_db = {
            'en': {
                # Common internet slang
                'lol': 'laughing out loud',
                'lmao': 'laughing my ass off',
                'rofl': 'rolling on floor laughing',
                'brb': 'be right back',
                'btw': 'by the way',
                'tbh': 'to be honest',
                'imo': 'in my opinion',
                'imho': 'in my humble opinion',
                'fyi': 'for your information',
                'omg': 'oh my god',
                'omfg': 'oh my fucking god',
                'wtf': 'what the fuck',
                'wth': 'what the hell',
                'idk': 'I don\'t know',
                'afaik': 'as far as I know',
                'asap': 'as soon as possible',
                'bff': 'best friends forever',
                'dm': 'direct message',
                'irl': 'in real life',
                'tmi': 'too much information',
                'ftw': 'for the win',
                'rn': 'right now',
                'nvm': 'never mind',
                'smh': 'shaking my head',
                'fomo': 'fear of missing out',
                'yolo': 'you only live once',
                'bae': 'before anyone else (significant other)',
                'salty': 'upset or bitter',
                'lit': 'exciting or excellent',
                'fire': 'amazing or cool',
                'savage': 'fierce or ruthless',
                'slay': 'do something exceptionally well',
                'goat': 'greatest of all time',
                'sus': 'suspicious',
                'bet': 'yes or okay',
                'cap': 'lie',
                'no cap': 'no lie',
                'deadass': 'seriously',
                'lowkey': 'slightly or secretly',
                'highkey': 'very or extremely',
                'vibe': 'mood or atmosphere',
                'simp': 'someone overly attentive',
                'stan': 'obsessive fan',
                'ghosting': 'suddenly cutting off communication',
                'flex': 'show off',
                'clout': 'influence or fame',
                'snatched': 'looking good',
                'shook': 'shocked or surprised',
                'tea': 'gossip',
                'shade': 'disrespect or criticism',
                'woke': 'socially aware',
                'basic': 'unoriginal or mainstream',
                'extra': 'over the top',
                'salty': 'bitter or angry',
                'thirsty': 'desperate for attention',
                'receipts': 'proof or evidence',
                'cancelled': 'boycotted or rejected',
                'ship': 'support a relationship',
                'binge': 'watch/consume excessively',
                'adulting': 'doing adult responsibilities',
                'hangry': 'angry because hungry',
                'selfie': 'self-portrait photo',
                'photobomb': 'appear unexpectedly in photo',
                'unfriend': 'remove from social media',
                'troll': 'provoke online',
                'viral': 'widely spread online',
                'meme': 'humorous internet content',
                # Modern expressions
                'on fleek': 'perfect',
                'turnt': 'excited or intoxicated',
                'squad': 'close group of friends',
                'goals': 'aspirational',
                'mood': 'relatable feeling',
                'same': 'I agree/relate',
                'oof': 'expression of pain/sympathy',
                'yeet': 'throw with force',
                'periodt': 'end of discussion',
                'slaps': 'really good (music)',
                'slept on': 'underrated',
                'hits different': 'uniquely good',
                'rent free': 'constantly thinking about',
                'main character': 'acting like protagonist',
                'npc': 'boring person (non-player character)',
                'pick me': 'seeking validation',
                'gatekeep': 'restrict access',
                'gaslight': 'manipulate perception',
                'girlboss': 'successful woman',
            },
            'fr': {
                # French slang
                'mdr': 'mort de rire (laughing out loud)',
                'ptdr': 'pété de rire (dying of laughter)',
                'lol': 'laughing out loud',
                'stp': 's\'il te plaît (please)',
                'svp': 's\'il vous plaît (please formal)',
                'tlm': 'tout le monde (everyone)',
                'bcp': 'beaucoup (a lot)',
                'pk': 'pourquoi (why)',
                'pq': 'pourquoi (why)',
                'pcq': 'parce que (because)',
                'dsl': 'désolé (sorry)',
                'jsp': 'je sais pas (I don\'t know)',
                'jpp': 'j\'en peux plus (I can\'t anymore)',
                'ouf': 'fou (crazy - verlan)',
                'meuf': 'femme (woman - verlan)',
                'relou': 'lourd (annoying - verlan)',
                'chelou': 'louche (weird - verlan)',
                'kiffer': 'aimer (to like/love)',
                'zarbi': 'bizarre (weird)',
                'taffer': 'travailler (to work)',
                'thune': 'argent (money)',
                'fric': 'argent (money)',
                'bouffer': 'manger (to eat)',
                'choper': 'attraper (to catch/get)',
                'galérer': 'avoir des difficultés (struggle)',
                'péter un câble': 'devenir fou (go crazy)',
                'avoir la flemme': 'être paresseux (be lazy)',
                'c\'est chaud': 'c\'est difficile (it\'s tough)',
                'trop': 'très (very)',
                'grave': 'très (very/seriously)',
                'carrément': 'vraiment (totally)',
                'mortel': 'génial (awesome)',
                'stylé': 'cool (stylish)',
                'trop bien': 'super (great)',
            },
            'es': {
                # Spanish slang
                'tq': 'te quiero (I love you)',
                'tk': 'te quiero (I love you)',
                'xq': 'porque (because)',
                'pq': 'porque (because)',
                'tb': 'también (also)',
                'tmb': 'también (also)',
                'bn': 'bien (good)',
                'q': 'que (that/what)',
                'k': 'que (that/what)',
                'xa': 'para (for)',
                'x': 'por (for/by)',
                'msj': 'mensaje (message)',
                'tío': 'guy/dude',
                'tía': 'girl/chick',
                'guay': 'cool',
                'chulo': 'cool/nice',
                'mola': 'cool/nice',
                'flipar': 'to be amazed',
                'mogollón': 'a lot',
                'chaval': 'kid/young person',
                'tronco': 'buddy',
                'colega': 'friend',
                'pijo': 'posh person',
                'currar': 'to work',
                'curro': 'work/job',
                'pasta': 'money',
                'pela': 'money',
                'liar': 'to mess up',
                'molar': 'to be cool',
                'petarlo': 'to break it',
                'enrollarse': 'to make out',
            },
            'de': {
                # German slang
                'geil': 'cool/awesome',
                'krass': 'crazy/extreme',
                'cool': 'cool',
                'mega': 'very/mega',
                'hammer': 'awesome',
                'bock': 'desire/want',
                'digger': 'dude/bro',
                'alter': 'dude/man',
                'chillen': 'to chill/relax',
                'checken': 'to understand',
                'abfeiern': 'to party hard',
                'fett': 'cool/fat',
                'nice': 'nice',
                'assi': 'antisocial person',
                'tussi': 'silly girl',
                'pennen': 'to sleep',
                'labern': 'to talk nonsense',
                'schnallen': 'to understand',
                'kumpel': 'buddy',
                'macker': 'guy/dude',
            }
        }
        
        # Context patterns for better translation
        self.context_patterns = {
            'greeting': ['hello', 'hi', 'hey', 'bonjour', 'hola', 'salut', 'buenos días'],
            'farewell': ['bye', 'goodbye', 'see you', 'au revoir', 'adiós', 'hasta luego'],
            'question': ['?', 'how', 'what', 'when', 'where', 'why', 'who', 'comment', 'quoi', 'quand', 'où', 'pourquoi', 'cómo', 'qué', 'cuándo', 'dónde'],
            'emotion_positive': ['happy', 'great', 'awesome', 'excellent', 'wonderful', 'fantastic', 'heureux', 'génial', 'super', 'feliz', 'excelente'],
            'emotion_negative': ['sad', 'bad', 'terrible', 'awful', 'horrible', 'triste', 'mal', 'terrible'],
            'formal': ['sir', 'madam', 'monsieur', 'madame', 'señor', 'señora', 'please', 's\'il vous plaît', 'por favor'],
            'informal': ['dude', 'bro', 'mate', 'buddy', 'mec', 'tío', 'colega'],
        }
    
    def detect_context_type(self, text: str) -> List[str]:
        """Detect the context type of the text"""
        text_lower = text.lower()
        detected_contexts = []
        
        for context_type, patterns in self.context_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                detected_contexts.append(context_type)
        
        return detected_contexts if detected_contexts else ['general']
    
    def expand_slang(self, text: str, lang: str) -> Tuple[str, bool]:
        """
        Expand slang and abbreviations to full form for better translation
        Returns: (expanded_text, was_modified)
        """
        if lang not in self.slang_db:
            return text, False
        
        expanded = text
        modified = False
        slang_dict = self.slang_db[lang]
        
        # Word boundary aware replacement
        words = text.split()
        new_words = []
        
        for word in words:
            word_lower = word.lower()
            # Remove punctuation for matching
            clean_word = re.sub(r'[^\w\s]', '', word_lower)
            
            if clean_word in slang_dict:
                # Preserve original capitalization style
                if word.isupper():
                    replacement = slang_dict[clean_word].upper()
                elif word[0].isupper():
                    replacement = slang_dict[clean_word].capitalize()
                else:
                    replacement = slang_dict[clean_word]
                
                # Preserve punctuation
                punctuation = ''.join(c for c in word if not c.isalnum())
                new_words.append(replacement + punctuation)
                modified = True
            else:
                new_words.append(word)
        
        expanded = ' '.join(new_words)
        
        # Multi-word slang expressions
        for slang, expansion in slang_dict.items():
            if ' ' in slang and slang in expanded.lower():
                expanded = re.sub(re.escape(slang), expansion, expanded, flags=re.IGNORECASE)
                modified = True
        
        return expanded, modified
    
    def autocorrect_with_context(self, text: str, lang: str) -> str:
        """
        Contextual autocorrect that understands slang and context
        """
        # First expand slang
        corrected, _ = self.expand_slang(text, lang)
        
        # Common typing errors (language-specific)
        corrections = {
            'en': {
                r'\bim\b': 'I\'m',
                r'\bi\b': 'I',
                r'\bill\b': 'I\'ll',
                r'\byour\b(?=\s+(going|doing|coming))': 'you\'re',
                r'\btheir\b(?=\s+(going|doing|coming))': 'they\'re',
                r'\bu\b': 'you',
                r'\bur\b': 'your',
                r'\br\b': 'are',
                r'\btho\b': 'though',
                r'\bcuz\b': 'because',
                r'\bcoz\b': 'because',
                r'\bcause\b': 'because',
                r'\bgonna\b': 'going to',
                r'\bwanna\b': 'want to',
                r'\bgotta\b': 'got to',
                r'\bkinda\b': 'kind of',
                r'\bsorta\b': 'sort of',
                r'\byeah\b': 'yes',
                r'\bnah\b': 'no',
                r'\byep\b': 'yes',
                r'\bnope\b': 'no',
            },
            'fr': {
                r'\bké\b': 'que',
                r'\bki\b': 'qui',
                r'\bkom\b': 'comme',
                r'\bcé\b': 'c\'est',
                r'\bsé\b': 's\'est',
                r'\bté\b': 't\'es',
                r'\bpas\sde\b': 'pas de',
            }
        }
        
        if lang in corrections:
            for pattern, replacement in corrections[lang].items():
                corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
        
        return corrected
    
    def add_context(self, text: str, lang: str, context_type: str = None):
        """Add text to context history for better future translations"""
        self.context_history.append({
            'text': text,
            'lang': lang,
            'type': context_type or self.detect_context_type(text),
            'timestamp': __import__('time').time()
        })
    
    def get_context_summary(self) -> str:
        """Get a summary of recent conversation context"""
        if not self.context_history:
            return ""
        
        # Combine recent context
        recent_context = list(self.context_history)[-3:]  # Last 3 entries
        return " | ".join([ctx['text'][:50] for ctx in recent_context])
    
    def enhance_translation_with_context(self, original: str, translated: str, 
                                        src_lang: str, tgt_lang: str) -> str:
        """
        Enhance translation using context and conversation history
        """
        # Detect context type
        context_types = self.detect_context_type(original)
        
        # Apply context-aware adjustments
        enhanced = translated
        
        # Formality matching
        if 'formal' in context_types:
            # Ensure formal tone in translation
            enhanced = self._apply_formal_tone(enhanced, tgt_lang)
        elif 'informal' in context_types:
            # Ensure informal/casual tone
            enhanced = self._apply_informal_tone(enhanced, tgt_lang)
        
        # Emotion preservation
        if any(ctx in context_types for ctx in ['emotion_positive', 'emotion_negative']):
            # Preserve emotional intensity
            enhanced = self._preserve_emotion(original, enhanced, context_types)
        
        return enhanced
    
    def _apply_formal_tone(self, text: str, lang: str) -> str:
        """Apply formal tone to translation"""
        # Language-specific formal conversions
        if lang == 'fr':
            # Convert tu -> vous forms where applicable
            text = re.sub(r'\btu\b', 'vous', text, flags=re.IGNORECASE)
            text = re.sub(r'\bton\b', 'votre', text, flags=re.IGNORECASE)
            text = re.sub(r'\bta\b', 'votre', text, flags=re.IGNORECASE)
        elif lang == 'es':
            # Convert tú -> usted forms
            text = re.sub(r'\btú\b', 'usted', text, flags=re.IGNORECASE)
        
        return text
    
    def _apply_informal_tone(self, text: str, lang: str) -> str:
        """Apply informal/casual tone to translation"""
        if lang == 'fr':
            # Convert vous -> tu forms where applicable
            text = re.sub(r'\bvous\b(?!\s+êtes\s+nombreux)', 'tu', text, flags=re.IGNORECASE)
        
        return text
    
    def _preserve_emotion(self, original: str, translated: str, context_types: List[str]) -> str:
        """Preserve emotional intensity in translation"""
        # Count exclamation marks and capitals as emotion indicators
        exclamations = original.count('!')
        if exclamations > 0 and translated.count('!') < exclamations:
            # Add exclamation marks to preserve intensity
            translated = translated.rstrip('.') + '!' * min(exclamations, 3)
        
        return translated
    
    def get_contextual_suggestion(self, text: str, lang: str) -> Optional[str]:
        """Get contextual suggestions for improving the input"""
        # Check for common mistakes or suggest expansions
        if lang in self.slang_db:
            expanded, modified = self.expand_slang(text, lang)
            if modified:
                return f"Slang detected. Expanded to: {expanded}"
        
        return None


# Global instance
contextual_engine = ContextualTranslationEngine()

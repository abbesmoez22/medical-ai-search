import spacy
from typing import List, Dict, Any
import structlog
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = structlog.get_logger()


class MedicalNERService:
    def __init__(self):
        self.nlp = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize medical NER model"""
        try:
            # Try to load medical model first
            self.nlp = spacy.load("en_core_sci_md")
            logger.info("Medical NER model loaded successfully", model="en_core_sci_md")
        except OSError:
            try:
                # Fallback to basic English model
                self.nlp = spacy.load("en_core_web_sm")
                logger.warning("Medical NER model not found, using basic model", model="en_core_web_sm")
            except OSError:
                logger.error("No spaCy model found, NER will be disabled")
                self.nlp = None
    
    async def extract_entities(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract medical entities from text"""
        if not self.nlp or not text:
            return self._empty_entities()
        
        try:
            # Limit text length for performance
            text = text[:100000]  # 100KB limit
            
            # Run NLP processing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(self.executor, self.nlp, text)
            
            entities = {
                'diseases': [],
                'drugs': [],
                'procedures': [],
                'anatomy': [],
                'symptoms': [],
                'measurements': [],
                'general': []
            }
            
            for ent in doc.ents:
                entity_info = {
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'confidence': self._calculate_confidence(ent)
                }
                
                # Categorize entities based on label
                category = self._categorize_entity(ent.label_)
                entities[category].append(entity_info)
            
            # Add custom medical entity extraction
            custom_entities = self._extract_custom_medical_entities(text)
            for category, custom_ents in custom_entities.items():
                entities[category].extend(custom_ents)
            
            # Remove duplicates and sort by confidence
            for category in entities:
                entities[category] = self._deduplicate_entities(entities[category])
            
            logger.info("Medical NER completed", 
                       total_entities=sum(len(ents) for ents in entities.values()),
                       text_length=len(text))
            
            return entities
            
        except Exception as e:
            logger.error("Medical NER failed", error=str(e))
            return self._empty_entities()
    
    def _calculate_confidence(self, ent) -> float:
        """Calculate confidence score for entity"""
        try:
            # Use entity probability if available
            if hasattr(ent, 'prob') and ent.prob is not None:
                return float(ent.prob)
            
            # Fallback confidence based on entity length and type
            base_confidence = 0.7
            
            # Longer entities tend to be more reliable
            length_bonus = min(len(ent.text) / 20, 0.2)
            
            # Medical-specific labels get higher confidence
            medical_labels = {'DISEASE', 'DRUG', 'SYMPTOM', 'ANATOMY', 'PROCEDURE'}
            medical_bonus = 0.1 if ent.label_ in medical_labels else 0
            
            return min(base_confidence + length_bonus + medical_bonus, 1.0)
            
        except:
            return 0.5  # Default confidence
    
    def _categorize_entity(self, label: str) -> str:
        """Categorize entity based on spaCy label"""
        disease_labels = {'DISEASE', 'DISORDER', 'CONDITION', 'SYNDROME'}
        drug_labels = {'DRUG', 'MEDICATION', 'CHEMICAL', 'SUBSTANCE'}
        procedure_labels = {'PROCEDURE', 'TREATMENT', 'THERAPY', 'OPERATION'}
        anatomy_labels = {'ANATOMY', 'ORGAN', 'BODY_PART', 'TISSUE'}
        symptom_labels = {'SYMPTOM', 'SIGN', 'MANIFESTATION'}
        measurement_labels = {'MEASUREMENT', 'QUANTITY', 'DOSE', 'CONCENTRATION'}
        
        if label in disease_labels:
            return 'diseases'
        elif label in drug_labels:
            return 'drugs'
        elif label in procedure_labels:
            return 'procedures'
        elif label in anatomy_labels:
            return 'anatomy'
        elif label in symptom_labels:
            return 'symptoms'
        elif label in measurement_labels:
            return 'measurements'
        else:
            return 'general'
    
    def _extract_custom_medical_entities(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract custom medical entities using regex patterns"""
        import re
        
        custom_entities = {
            'diseases': [],
            'drugs': [],
            'procedures': [],
            'measurements': []
        }
        
        # Common disease patterns
        disease_patterns = [
            r'\b(?:diabetes|hypertension|cancer|tumor|carcinoma|pneumonia|influenza|covid-19|alzheimer|parkinson)\b',
            r'\b\w+itis\b',  # Inflammatory conditions
            r'\b\w+osis\b',  # Disease conditions
        ]
        
        # Drug name patterns
        drug_patterns = [
            r'\b[A-Z][a-z]+(?:mab|nib|tib|cept|pril|sartan|statin|cillin|mycin|zole|pine|lol|ide)\b',
            r'\b(?:aspirin|ibuprofen|acetaminophen|morphine|insulin|penicillin|warfarin)\b'
        ]
        
        # Medical procedure patterns
        procedure_patterns = [
            r'\b(?:surgery|biopsy|endoscopy|catheterization|angioplasty|transplant|dialysis)\b',
            r'\b\w+(?:ectomy|otomy|ostomy|plasty|graphy|scopy)\b'
        ]
        
        # Measurement patterns
        measurement_patterns = [
            r'\b\d+\.?\d*\s*(?:mg|g|ml|mcg|ug|IU|units?|mmol|mol)\b',
            r'\b\d+\.?\d*\s*(?:cm|mm|kg|lbs|°C|°F|%|bpm|mmHg)\b'
        ]
        
        patterns_map = {
            'diseases': disease_patterns,
            'drugs': drug_patterns,
            'procedures': procedure_patterns,
            'measurements': measurement_patterns
        }
        
        for category, patterns in patterns_map.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entity = {
                        'text': match.group(),
                        'label': f'CUSTOM_{category.upper()}',
                        'start': match.start(),
                        'end': match.end(),
                        'confidence': 0.6  # Lower confidence for regex matches
                    }
                    custom_entities[category].append(entity)
        
        return custom_entities
    
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entities and sort by confidence"""
        if not entities:
            return []
        
        # Group by text (case-insensitive)
        entity_groups = {}
        for entity in entities:
            key = entity['text'].lower()
            if key not in entity_groups:
                entity_groups[key] = []
            entity_groups[key].append(entity)
        
        # Keep highest confidence entity from each group
        deduplicated = []
        for group in entity_groups.values():
            best_entity = max(group, key=lambda x: x['confidence'])
            deduplicated.append(best_entity)
        
        # Sort by confidence (highest first)
        return sorted(deduplicated, key=lambda x: x['confidence'], reverse=True)
    
    def _empty_entities(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return empty entities structure"""
        return {
            'diseases': [],
            'drugs': [],
            'procedures': [],
            'anatomy': [],
            'symptoms': [],
            'measurements': [],
            'general': []
        }
    
    async def analyze_medical_relevance(self, text: str) -> Dict[str, Any]:
        """Analyze overall medical relevance of text"""
        entities = await self.extract_entities(text)
        
        total_entities = sum(len(ents) for ents in entities.values())
        word_count = len(text.split())
        
        # Calculate entity density
        entity_density = total_entities / word_count if word_count > 0 else 0
        
        # Calculate category distribution
        category_distribution = {}
        for category, ents in entities.items():
            category_distribution[category] = len(ents)
        
        # Calculate medical relevance score
        medical_score = min(entity_density * 100, 1.0)  # Normalize
        
        # Boost score based on medical entity types
        medical_categories = ['diseases', 'drugs', 'procedures', 'symptoms']
        medical_entity_count = sum(len(entities[cat]) for cat in medical_categories)
        medical_boost = min(medical_entity_count / 20, 0.3)  # Max 30% boost
        
        final_score = min(medical_score + medical_boost, 1.0)
        
        return {
            'medical_relevance_score': final_score,
            'entity_density': entity_density,
            'total_entities': total_entities,
            'category_distribution': category_distribution,
            'is_medical_document': final_score > 0.3
        }
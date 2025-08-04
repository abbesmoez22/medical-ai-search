import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
import re
import tempfile
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog
import textstat
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

logger = structlog.get_logger()

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')


class PDFProcessor:
    def __init__(self):
        self.medical_patterns = {
            'doi': r'10\.\d{4,}/[^\s]+',
            'pmid': r'PMID:\s*(\d+)',
            'pubmed_id': r'PubMed\s*ID:\s*(\d+)',
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'drug_names': r'\b[A-Z][a-z]+(?:mab|nib|tib|cept|pril|sartan|statin|cillin|mycin)\b',
            'medical_terms': r'\b(?:diagnosis|treatment|therapy|patient|clinical|medical|disease|syndrome|disorder)\b',
            'dosage': r'\b\d+\s*(?:mg|g|ml|mcg|ug|IU|units?)\b',
            'measurements': r'\b\d+\.?\d*\s*(?:cm|mm|kg|lbs|°C|°F|%)\b'
        }
        
        self.section_patterns = {
            'abstract': r'(?i)(?:^|\n)\s*(abstract|summary)\s*:?\s*\n',
            'introduction': r'(?i)(?:^|\n)\s*(introduction|background)\s*:?\s*\n',
            'methods': r'(?i)(?:^|\n)\s*(methods?|methodology|materials?\s+and\s+methods?)\s*:?\s*\n',
            'results': r'(?i)(?:^|\n)\s*(results?|findings?)\s*:?\s*\n',
            'discussion': r'(?i)(?:^|\n)\s*(discussion|conclusion)\s*:?\s*\n',
            'references': r'(?i)(?:^|\n)\s*(references?|bibliography)\s*:?\s*\n'
        }
    
    async def extract_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text and metadata from PDF using multiple methods"""
        try:
            # Try multiple extraction methods for best results
            extraction_results = []
            
            # Method 1: PyPDF2 (fast, basic)
            pypdf2_result = await self._extract_with_pypdf2(file_path)
            if pypdf2_result:
                extraction_results.append(('pypdf2', pypdf2_result))
            
            # Method 2: pdfplumber (better for tables and layout)
            pdfplumber_result = await self._extract_with_pdfplumber(file_path)
            if pdfplumber_result:
                extraction_results.append(('pdfplumber', pdfplumber_result))
            
            # Method 3: PyMuPDF (best OCR and image handling)
            pymupdf_result = await self._extract_with_pymupdf(file_path)
            if pymupdf_result:
                extraction_results.append(('pymupdf', pymupdf_result))
            
            # Select best extraction result
            best_result = self._select_best_extraction(extraction_results)
            
            if not best_result:
                raise Exception("Failed to extract text with any method")
            
            # Process and enhance the extracted text
            processed_result = await self._process_extracted_text(best_result)
            
            logger.info("PDF text extraction completed", 
                       file_path=file_path, 
                       method=processed_result.get('extraction_method'),
                       word_count=processed_result.get('word_count'))
            
            return processed_result
            
        except Exception as e:
            logger.error("PDF processing failed", error=str(e), file_path=file_path)
            raise
    
    async def _extract_with_pypdf2(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract text using PyPDF2"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract metadata
                metadata = pdf_reader.metadata or {}
                
                # Extract text from all pages
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                
                return {
                    'text': text_content,
                    'page_count': len(pdf_reader.pages),
                    'metadata': dict(metadata),
                    'method': 'pypdf2'
                }
        except Exception as e:
            logger.warning("PyPDF2 extraction failed", error=str(e))
            return None
    
    async def _extract_with_pdfplumber(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract text using pdfplumber"""
        try:
            with pdfplumber.open(file_path) as pdf:
                text_content = ""
                tables = []
                
                for page in pdf.pages:
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                    
                    # Extract tables
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
                
                return {
                    'text': text_content,
                    'page_count': len(pdf.pages),
                    'tables': tables,
                    'metadata': pdf.metadata or {},
                    'method': 'pdfplumber'
                }
        except Exception as e:
            logger.warning("pdfplumber extraction failed", error=str(e))
            return None
    
    async def _extract_with_pymupdf(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract text using PyMuPDF"""
        try:
            doc = fitz.open(file_path)
            text_content = ""
            images = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Extract text
                text_content += page.get_text() + "\n"
                
                # Extract images info
                image_list = page.get_images()
                if image_list:
                    images.extend([f"Page {page_num + 1}: {len(image_list)} images"])
            
            doc.close()
            
            return {
                'text': text_content,
                'page_count': len(doc),
                'images': images,
                'metadata': doc.metadata,
                'method': 'pymupdf'
            }
        except Exception as e:
            logger.warning("PyMuPDF extraction failed", error=str(e))
            return None
    
    def _select_best_extraction(self, extraction_results: List[tuple]) -> Optional[Dict[str, Any]]:
        """Select the best extraction result based on text quality"""
        if not extraction_results:
            return None
        
        best_result = None
        best_score = 0
        
        for method, result in extraction_results:
            if not result or not result.get('text'):
                continue
            
            text = result['text']
            score = self._calculate_extraction_quality(text)
            
            if score > best_score:
                best_score = score
                best_result = result
        
        return best_result
    
    def _calculate_extraction_quality(self, text: str) -> float:
        """Calculate quality score for extracted text"""
        if not text or len(text) < 100:
            return 0.0
        
        # Factors for quality assessment
        word_count = len(text.split())
        char_count = len(text)
        
        # Check for reasonable word/character ratio
        avg_word_length = char_count / word_count if word_count > 0 else 0
        
        # Check for presence of medical terms
        medical_indicators = ['patient', 'treatment', 'diagnosis', 'study', 'clinical', 'medical', 'therapy']
        medical_score = sum(1 for term in medical_indicators if term.lower() in text.lower())
        
        # Check for proper sentence structure
        sentences = sent_tokenize(text)
        sentence_score = min(len(sentences) / 50, 1.0)  # Normalize to 50 sentences
        
        # Check readability
        try:
            readability_score = textstat.flesch_reading_ease(text) / 100
        except:
            readability_score = 0.5
        
        # Calculate composite score
        length_score = min(word_count / 1000, 1.0)  # Normalize to 1000 words
        medical_relevance = min(medical_score / len(medical_indicators), 1.0)
        format_score = 1.0 if 3 <= avg_word_length <= 8 else 0.5
        
        return (length_score + medical_relevance + format_score + sentence_score + readability_score) / 5
    
    async def _process_extracted_text(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enhance extracted text"""
        text = extraction_result.get('text', '')
        
        # Clean and normalize text
        cleaned_text = self._clean_text(text)
        
        # Extract medical information
        extracted_info = self._extract_medical_info(cleaned_text)
        
        # Identify document structure
        document_structure = self._identify_document_structure(cleaned_text)
        
        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(cleaned_text)
        
        return {
            'text': cleaned_text,
            'page_count': extraction_result.get('page_count', 0),
            'word_count': len(cleaned_text.split()),
            'char_count': len(cleaned_text),
            'metadata': extraction_result.get('metadata', {}),
            'extraction_method': extraction_result.get('method', 'unknown'),
            'extracted_info': extracted_info,
            'document_structure': document_structure,
            'quality_metrics': quality_metrics,
            'tables': extraction_result.get('tables', []),
            'images': extraction_result.get('images', [])
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page headers/footers patterns
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'\d+\s*\n', '', text)  # Remove page numbers
        
        # Fix common OCR errors
        text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
        
        # Remove excessive line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Fix spacing around punctuation
        text = re.sub(r'\s+([,.;:!?])', r'\1', text)
        text = re.sub(r'([,.;:!?])\s*', r'\1 ', text)
        
        return text.strip()
    
    def _extract_medical_info(self, text: str) -> Dict[str, List[str]]:
        """Extract medical entities and patterns"""
        extracted = {}
        
        for pattern_name, pattern in self.medical_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if isinstance(matches[0] if matches else None, tuple):
                # Handle grouped matches
                matches = [match[0] if isinstance(match, tuple) else match for match in matches]
            extracted[pattern_name] = list(set(matches))  # Remove duplicates
        
        return extracted
    
    def _identify_document_structure(self, text: str) -> Dict[str, Dict[str, int]]:
        """Identify document sections"""
        structure = {}
        
        for section_name, pattern in self.section_patterns.items():
            matches = list(re.finditer(pattern, text))
            if matches:
                for i, match in enumerate(matches):
                    section_key = f"{section_name}_{i}" if i > 0 else section_name
                    structure[section_key] = {
                        'start': match.end(),
                        'end': matches[i + 1].start() if i + 1 < len(matches) else len(text)
                    }
        
        return structure
    
    def _calculate_quality_metrics(self, text: str) -> Dict[str, float]:
        """Calculate comprehensive quality metrics"""
        if not text:
            return {'overall_score': 0.0}
        
        try:
            # Basic metrics
            word_count = len(text.split())
            sentence_count = len(sent_tokenize(text))
            
            # Readability metrics
            flesch_score = textstat.flesch_reading_ease(text)
            flesch_kincaid = textstat.flesch_kincaid_grade(text)
            
            # Medical relevance
            medical_terms = self._extract_medical_info(text)
            medical_term_count = sum(len(terms) for terms in medical_terms.values())
            medical_density = medical_term_count / word_count if word_count > 0 else 0
            
            # Structure score
            structure = self._identify_document_structure(text)
            structure_score = min(len(structure) / 5, 1.0)  # Expect ~5 sections
            
            # Calculate overall score
            readability_score = max(0, min(flesch_score / 100, 1.0))
            complexity_score = max(0, min((20 - flesch_kincaid) / 20, 1.0))
            length_score = min(word_count / 3000, 1.0)  # Normalize to 3000 words
            
            overall_score = (
                readability_score * 0.25 +
                complexity_score * 0.25 +
                min(medical_density * 10, 1.0) * 0.25 +
                structure_score * 0.25
            )
            
            return {
                'overall_score': overall_score,
                'readability_score': readability_score,
                'complexity_score': complexity_score,
                'medical_density': medical_density,
                'structure_score': structure_score,
                'word_count': word_count,
                'sentence_count': sentence_count,
                'flesch_reading_ease': flesch_score,
                'flesch_kincaid_grade': flesch_kincaid
            }
            
        except Exception as e:
            logger.warning("Quality metrics calculation failed", error=str(e))
            return {'overall_score': 0.5}  # Default score
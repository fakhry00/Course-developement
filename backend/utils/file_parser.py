"""
File parsing utilities for extracting text from various document formats
"""

import fitz  # PyMuPDF
import docx2txt
from pathlib import Path
from typing import Optional

class FileParser:
    """Utility class for parsing different file formats"""
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from PDF, DOCX, or DOC files"""
        
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.pdf':
            return self._extract_from_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            return self._extract_from_word(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF using PyMuPDF"""
        
        try:
            doc = fitz.open(str(file_path))
            text = ""
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                text += page.get_text()
            
            doc.close()
            return text.strip()
            
        except Exception as e:
            raise Exception(f"Error reading PDF file: {str(e)}")
    
    def _extract_from_word(self, file_path: Path) -> str:
        """Extract text from Word documents using docx2txt"""
        
        try:
            text = docx2txt.process(str(file_path))
            return text.strip()
            
        except Exception as e:
            raise Exception(f"Error reading Word file: {str(e)}")
    
    def extract_metadata(self, file_path: Path) -> dict:
        """Extract metadata from documents"""
        
        metadata = {
            'filename': file_path.name,
            'size': file_path.stat().st_size,
            'extension': file_path.suffix.lower()
        }
        
        if file_path.suffix.lower() == '.pdf':
            try:
                doc = fitz.open(str(file_path))
                metadata.update({
                    'page_count': doc.page_count,
                    'title': doc.metadata.get('title', ''),
                    'author': doc.metadata.get('author', ''),
                    'subject': doc.metadata.get('subject', '')
                })
                doc.close()
            except:
                pass
        
        return metadata 

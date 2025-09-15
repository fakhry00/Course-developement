"""
LLM Configuration Management
"""

import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMConfig:
    """Centralized LLM configuration management"""
    
    @staticmethod
    def get_default_llm(temperature=0.3, max_tokens=3000):
        """Get default LLM configuration"""
        
        # Check if API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Use the correct model name
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        try:
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                request_timeout=180,
                api_key=api_key,
                max_retries=3
            )
        except Exception as e:
            # Fallback to gpt-3.5-turbo if gpt-4o-mini is not available
            print(f"Warning: {model_name} not available, falling back to gpt-3.5-turbo")
            return ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=temperature,
                max_tokens=max_tokens,
                request_timeout=180,
                api_key=api_key,
                max_retries=3
            )
    
    @staticmethod
    def get_content_generation_llm():
        """Get LLM optimized for content generation"""
        return LLMConfig.get_default_llm(temperature=0.4, max_tokens=4000)
    
    @staticmethod
    def get_analysis_llm():
        """Get LLM optimized for analysis tasks"""
        return LLMConfig.get_default_llm(temperature=0.1, max_tokens=3000)
    
    @staticmethod
    def test_llm_connection():
        """Test LLM connection"""
        try:
            llm = LLMConfig.get_default_llm()
            response = llm.invoke("Hello, this is a test.")
            return True, "LLM connection successful"
        except Exception as e:
            return False, f"LLM connection failed: {str(e)}"
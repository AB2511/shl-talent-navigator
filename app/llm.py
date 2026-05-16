"""
Multi-provider LLM integration.
Supports Gemini, OpenRouter, and Groq with unified interface.
"""
import os
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """Unified LLM client supporting multiple providers with fallback to template mode."""
    
    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: LLM provider (gemini, openrouter, groq)
            api_key: API key for the provider
            model: Model name to use
        """
        self.provider = provider or os.getenv("LLM_PROVIDER", "gemini")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", self._get_default_model())
        
        # NO-API-KEY MODE: Allow initialization without API key
        self.template_mode = not self.api_key
        
        if self.template_mode:
            print("⚠️  NO API KEY MODE: Using template responses (LLM disabled)")
            self.client = None
        else:
            self.client = httpx.AsyncClient(timeout=30.0)
    
    def _get_default_model(self) -> str:
        """Get default model for provider."""
        defaults = {
            "gemini": "gemini-1.5-flash",  # Updated to gemini-1.5-flash
            "openrouter": "openai/gpt-3.5-turbo",
            "groq": "llama2-70b-4096"
        }
        return defaults.get(self.provider, "gemini-1.5-flash")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Generate text completion from LLM or use template response if no API key.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        # NO-API-KEY MODE: Return template response
        if self.template_mode:
            return self._generate_template_response(prompt)
        
        if self.provider == "gemini":
            return await self._generate_gemini(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "openrouter":
            return await self._generate_openrouter(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "groq":
            return await self._generate_groq(prompt, system_prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    async def _generate_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Google Gemini API."""
        url = f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent"
        
        # Combine system prompt and user prompt
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = await self.client.post(
            f"{url}?key={self.api_key}",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    
    async def _generate_openrouter(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using OpenRouter API."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    async def _generate_groq(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Groq API."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    def _generate_template_response(self, prompt: str) -> str:
        """
        Generate template response when no API key is available.
        Provides basic functionality without LLM.
        """
        prompt_lower = prompt.lower()
        
        # Recommendation template
        if "recommend" in prompt_lower or "available assessments" in prompt_lower:
            return """Based on your requirements, here are relevant SHL assessments from our catalog:

The assessments listed above have been filtered based on your specified criteria. Each assessment includes:
- Duration and format details
- Target job levels
- Skills and competencies measured
- Remote testing availability

Would you like to refine these recommendations or compare specific assessments?"""
        
        # Comparison template
        elif "compare" in prompt_lower or "comparison" in prompt_lower:
            return """Here's a comparison of the selected assessments:

**Key Differences:**
- Duration and time requirements
- Target job levels and roles
- Skills and competencies measured
- Testing format and delivery options

Please review the assessment details provided to make an informed decision."""
        
        # Refinement template
        elif "refine" in prompt_lower or "adjust" in prompt_lower:
            return """I've adjusted the recommendations based on your updated requirements.

The refined results better match your specified constraints. If you'd like to further narrow down the options, please let me know what additional criteria to consider."""
        
        # Default template
        else:
            return """Thank you for your query. I've processed your request based on the available assessment catalog.

Please review the assessments provided and let me know if you need:
- More specific recommendations
- Comparison between assessments
- Additional filtering criteria

Note: Running in template mode (no LLM API key configured). For enhanced conversational responses, configure LLM_API_KEY in your environment."""
    
    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()

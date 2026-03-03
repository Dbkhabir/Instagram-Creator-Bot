"""
Captcha solving with free OCR (Tesseract) and paid fallback (2Captcha)
প্রথমে free OCR try করবে, fail হলে 2Captcha use করবে
"""

import cv2
import numpy as np
import pytesseract
import requests
import time
import logging
from PIL import Image
from io import BytesIO
from typing import Optional
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CaptchaSolver:
    """Captcha solving with multiple methods"""
    
    def __init__(self):
        self.use_free_ocr = config.USE_FREE_OCR
        self.api_key_2captcha = config.CAPTCHA_2CAPTCHA_KEY
    
    def preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        """
        Image preprocessing for better OCR accuracy
        OCR এর জন্য image কে optimize করা
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Noise removal
            kernel = np.ones((1, 1), np.uint8)
            opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
            
            # Dilation
            closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=1)
            
            # Invert if needed (white text on black background)
            if np.mean(closing) > 127:
                closing = cv2.bitwise_not(closing)
            
            return closing
            
        except Exception as e:
            logger.error(f"Image preprocessing error: {e}")
            return None
    
    def solve_with_tesseract(self, image_bytes: bytes) -> Optional[str]:
        """
        Solve captcha using free Tesseract OCR
        Free OCR দিয়ে captcha solve করা
        """
        try:
            logger.info("🔍 Attempting free OCR solution...")
            
            # Preprocess image
            processed_img = self.preprocess_image(image_bytes)
            
            if processed_img is None:
                return None
            
            # Configure Tesseract
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            
            # Extract text
            text = pytesseract.image_to_string(processed_img, config=custom_config)
            text = text.strip().replace(' ', '').replace('\n', '')
            
            # Validate result (Instagram captchas are usually 6 characters)
            if len(text) >= 4 and len(text) <= 8:
                logger.info(f"✅ Free OCR solved: {text}")
                return text
            
            logger.warning(f"⚠️ Free OCR result invalid: {text}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Tesseract OCR error: {e}")
            return None
    
    def solve_with_2captcha(self, image_bytes: bytes) -> Optional[str]:
        """
        Solve captcha using 2Captcha paid service (fallback)
        যদি free OCR fail করে তাহলে 2Captcha use করবে
        """
        try:
            if not self.api_key_2captcha:
                logger.warning("⚠️ 2Captcha API key not configured")
                return None
            
            logger.info("💰 Using 2Captcha paid service...")
            
            # Upload captcha
            files = {'file': ('captcha.png', image_bytes, 'image/png')}
            data = {
                'key': self.api_key_2captcha,
                'method': 'post',
                'json': 1
            }
            
            response = requests.post(
                'http://2captcha.com/in.php',
                files=files,
                data=data,
                timeout=30
            )
            
            result = response.json()
            
            if result.get('status') != 1:
                logger.error(f"2Captcha upload failed: {result}")
                return None
            
            captcha_id = result['request']
            logger.info(f"📤 Captcha uploaded to 2Captcha: {captcha_id}")
            
            # Wait for solution (usually takes 10-20 seconds)
            max_attempts = 24  # 2 minutes max
            for attempt in range(max_attempts):
                time.sleep(5)
                
                check_response = requests.get(
                    'http://2captcha.com/res.php',
                    params={
                        'key': self.api_key_2captcha,
                        'action': 'get',
                        'id': captcha_id,
                        'json': 1
                    },
                    timeout=10
                )
                
                check_result = check_response.json()
                
                if check_result.get('status') == 1:
                    solution = check_result['request']
                    logger.info(f"✅ 2Captcha solved: {solution}")
                    return solution
                
                if check_result.get('request') == 'CAPCHA_NOT_READY':
                    logger.info(f"⏳ Waiting for 2Captcha... ({attempt + 1}/{max_attempts})")
                    continue
                
                logger.error(f"2Captcha error: {check_result}")
                return None
            
            logger.error("⏰ 2Captcha timeout")
            return None
            
        except Exception as e:
            logger.error(f"❌ 2Captcha error: {e}")
            return None
    
    def solve_captcha(self, image_url: str = None, image_bytes: bytes = None) -> Optional[str]:
        """
        Main captcha solving method with fallback
        প্রথমে free OCR, তারপর 2Captcha
        """
        
        # Download image if URL provided
        if image_url and not image_bytes:
            try:
                response = requests.get(image_url, timeout=10)
                image_bytes = response.content
            except Exception as e:
                logger.error(f"Failed to download captcha image: {e}")
                return None
        
        if not image_bytes:
            logger.error("No captcha image provided")
            return None
        
        # Try free OCR first
        if self.use_free_ocr:
            solution = self.solve_with_tesseract(image_bytes)
            if solution:
                return solution
            
            logger.warning("⚠️ Free OCR failed, trying paid service...")
        
        # Fallback to 2Captcha
        if self.api_key_2captcha:
            solution = self.solve_with_2captcha(image_bytes)
            if solution:
                return solution
        
        logger.error("❌ All captcha solving methods failed")
        return None
    
    def solve_recaptcha_v2(self, site_key: str, page_url: str) -> Optional[str]:
        """
        Solve reCAPTCHA v2 using 2Captcha
        Instagram যদি reCAPTCHA use করে
        """
        try:
            if not self.api_key_2captcha:
                logger.warning("⚠️ 2Captcha API key not configured")
                return None
            
            logger.info("🔐 Solving reCAPTCHA v2...")
            
            # Submit captcha
            response = requests.get(
                'http://2captcha.com/in.php',
                params={
                    'key': self.api_key_2captcha,
                    'method': 'userrecaptcha',
                    'googlekey': site_key,
                    'pageurl': page_url,
                    'json': 1
                },
                timeout=30
            )
            
            result = response.json()
            
            if result.get('status') != 1:
                logger.error(f"reCAPTCHA submit failed: {result}")
                return None
            
            captcha_id = result['request']
            logger.info(f"📤 reCAPTCHA submitted: {captcha_id}")
            
            # Wait for solution (can take 30-60 seconds)
            max_attempts = 40  # 3+ minutes max
            for attempt in range(max_attempts):
                time.sleep(5)
                
                check_response = requests.get(
                    'http://2captcha.com/res.php',
                    params={
                        'key': self.api_key_2captcha,
                        'action': 'get',
                        'id': captcha_id,
                        'json': 1
                    },
                    timeout=10
                )
                
                check_result = check_response.json()
                
                if check_result.get('status') == 1:
                    solution = check_result['request']
                    logger.info(f"✅ reCAPTCHA solved")
                    return solution
                
                if check_result.get('request') == 'CAPCHA_NOT_READY':
                    logger.info(f"⏳ Waiting for reCAPTCHA... ({attempt + 1}/{max_attempts})")
                    continue
                
                logger.error(f"reCAPTCHA error: {check_result}")
                return None
            
            logger.error("⏰ reCAPTCHA timeout")
            return None
            
        except Exception as e:
            logger.error(f"❌ reCAPTCHA solving error: {e}")
            return None


# Initialize captcha solver
captcha_solver = CaptchaSolver()
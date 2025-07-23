"""
Image processing filters for vision_api
Contains all image transformation functions used by the Flask API
"""

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from typing import Union, Tuple
import io


def apply_invert(image: Image.Image) -> Image.Image:
    """
    Invert image colors (negative effect)
    
    Args:
        image: PIL Image object
        
    Returns:
        PIL Image object with inverted colors
    """
    try:
        return ImageOps.invert(image.convert('RGB'))
    except Exception as e:
        raise ValueError(f"Error applying invert filter: {str(e)}")


def apply_grayscale(image: Image.Image) -> Image.Image:
    """
    Convert image to grayscale
    
    Args:
        image: PIL Image object
        
    Returns:
        PIL Image object in grayscale
    """
    try:
        return image.convert('L').convert('RGB')  # Convert back to RGB for consistency
    except Exception as e:
        raise ValueError(f"Error applying grayscale filter: {str(e)}")


def apply_contrast(image: Image.Image, factor: float = 1.5) -> Image.Image:
    """
    Adjust image contrast
    
    Args:
        image: PIL Image object
        factor: Contrast factor (0.0 = gray, 1.0 = original, >1.0 = more contrast)
        
    Returns:
        PIL Image object with adjusted contrast
    """
    try:
        # Validate factor range
        if factor < 0:
            raise ValueError("Contrast factor must be non-negative")
        if factor > 3.0:
            factor = 3.0  # Cap at reasonable maximum
            
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)
    except Exception as e:
        raise ValueError(f"Error applying contrast filter: {str(e)}")


def apply_blur(image: Image.Image, radius: float = 2.0) -> Image.Image:
    """
    Apply Gaussian blur to image
    
    Args:
        image: PIL Image object
        radius: Blur radius (higher = more blur)
        
    Returns:
        PIL Image object with blur effect
    """
    try:
        # Validate radius range
        if radius < 0:
            raise ValueError("Blur radius must be non-negative")
        if radius > 10.0:
            radius = 10.0  # Cap at reasonable maximum
            
        return image.filter(ImageFilter.GaussianBlur(radius=radius))
    except Exception as e:
        raise ValueError(f"Error applying blur filter: {str(e)}")


def apply_sharpen(image: Image.Image, factor: float = 2.0) -> Image.Image:
    """
    Apply sharpening filter to image
    
    Args:
        image: PIL Image object
        factor: Sharpening factor (1.0 = original, >1.0 = more sharp)
        
    Returns:
        PIL Image object with sharpening effect
    """
    try:
        # Validate factor range
        if factor < 0:
            raise ValueError("Sharpen factor must be non-negative")
        if factor > 5.0:
            factor = 5.0  # Cap at reasonable maximum
            
        enhancer = ImageEnhance.Sharpness(image)
        return enhancer.enhance(factor)
    except Exception as e:
        raise ValueError(f"Error applying sharpen filter: {str(e)}")


def get_available_filters() -> dict:
    """
    Get list of available filters with their descriptions and parameters
    
    Returns:
        Dictionary of available filters with metadata
    """
    return {
        "invert": {
            "description": "Invert image colors (negative effect)",
            "parameters": None,
            "example_usage": "No additional parameters needed"
        },
        "grayscale": {
            "description": "Convert image to grayscale",
            "parameters": None,
            "example_usage": "No additional parameters needed"
        },
        "contrast": {
            "description": "Adjust image contrast",
            "parameters": {
                "factor": {
                    "type": "float",
                    "default": 1.5,
                    "range": "0.0 - 3.0",
                    "description": "Contrast factor (0.0=gray, 1.0=original, >1.0=more contrast)"
                }
            },
            "example_usage": "factor=1.5 for enhanced contrast"
        },
        "blur": {
            "description": "Apply Gaussian blur effect",
            "parameters": {
                "radius": {
                    "type": "float",
                    "default": 2.0,
                    "range": "0.0 - 10.0",
                    "description": "Blur radius (higher values = more blur)"
                }
            },
            "example_usage": "radius=3.0 for medium blur"
        },
        "sharpen": {
            "description": "Apply sharpening filter",
            "parameters": {
                "factor": {
                    "type": "float",
                    "default": 2.0,
                    "range": "0.0 - 5.0",
                    "description": "Sharpening factor (1.0=original, >1.0=more sharp)"
                }
            },
            "example_usage": "factor=2.5 for enhanced sharpness"
        }
    }


def apply_filter(image: Image.Image, filter_name: str, **kwargs) -> Image.Image:
    """
    Apply a specific filter to an image
    
    Args:
        image: PIL Image object
        filter_name: Name of the filter to apply
        **kwargs: Additional parameters for the filter
        
    Returns:
        PIL Image object with filter applied
        
    Raises:
        ValueError: If filter_name is not supported
    """
    # Ensure image is in RGB mode
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    filter_functions = {
        'invert': apply_invert,
        'grayscale': apply_grayscale,
        'contrast': apply_contrast,
        'blur': apply_blur,
        'sharpen': apply_sharpen
    }
    
    if filter_name not in filter_functions:
        available = ', '.join(filter_functions.keys())
        raise ValueError(f"Unsupported filter '{filter_name}'. Available filters: {available}")
    
    try:
        filter_func = filter_functions[filter_name]
        
        # Apply filter with or without parameters
        if filter_name in ['invert', 'grayscale']:
            return filter_func(image)
        else:
            return filter_func(image, **kwargs)
            
    except Exception as e:
        raise ValueError(f"Error applying {filter_name} filter: {str(e)}")


def validate_image(image_data: bytes) -> Image.Image:
    """
    Validate and load image from bytes
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        PIL Image object
        
    Raises:
        ValueError: If image is invalid or unsupported format
    """
    try:
        image = Image.open(io.BytesIO(image_data))
        
        # Print debug info
        print(f"Image format: {image.format}")
        print(f"Image mode: {image.mode}")
        print(f"Image size: {image.size}")
        
        # Validate image format - be more permissive with JPEG variants
        allowed_formats = ['JPEG', 'PNG', 'WEBP', 'BMP', 'TIFF', 'GIF']
        if image.format not in allowed_formats:
            print(f"Warning: Unusual format {image.format}, trying to process anyway...")
            # Don't raise error immediately, try to convert
        
        # Validate image size (prevent extremely large images)
        max_size = (10000, 10000)  # 10K resolution limit
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            raise ValueError(f"Image too large. Maximum size: {max_size[0]}x{max_size[1]}")
        
        # Try to load the image to ensure it's valid
        image.load()
        
        return image
        
    except Exception as e:
        print(f"Image validation error: {str(e)}")
        print(f"Error type: {type(e)}")
        raise ValueError(f"Invalid image file: {str(e)}")


def image_to_bytes(image: Image.Image, format: str = 'JPEG', quality: int = 95) -> bytes:
    """
    Convert PIL Image to bytes
    
    Args:
        image: PIL Image object
        format: Output format (JPEG, PNG, etc.)
        quality: Image quality (1-100, only for JPEG)
        
    Returns:
        Image as bytes
    """
    try:
        output = io.BytesIO()
        
        # Ensure format is supported
        if format.upper() not in ['JPEG', 'PNG', 'WEBP']:
            format = 'JPEG'
        
        # IMPORTANT: Preserve original image size
        print(f"Original image size before conversion: {image.size}")
        
        # Save with appropriate parameters
        if format.upper() == 'JPEG':
            # Convert to RGB if necessary for JPEG
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            # Use high quality to preserve image details
            image.save(output, format=format, quality=quality, optimize=False)
        else:
            image.save(output, format=format, optimize=False)
        
        print(f"Processed image size after conversion: {image.size}")
        return output.getvalue()
        
    except Exception as e:
        raise ValueError(f"Error converting image to bytes: {str(e)}")
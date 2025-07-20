"""
Vision API - Flask Backend
Professional image processing API with web interface
"""

from flask import Flask, request, jsonify, render_template, send_file, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import time
import uuid
from datetime import datetime, timedelta
import mimetypes
from PIL import Image
import io

# Import our filter functions
from filters import (
    apply_filter, 
    get_available_filters, 
    validate_image, 
    image_to_bytes
)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed'
app.config['SECRET_KEY'] = 'vision-api-secret-key-change-in-production'

# Supported image formats
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files():
    """Clean up files older than 1 hour"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        for folder in [app.config['UPLOAD_FOLDER'], app.config['PROCESSED_FOLDER']]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        print(f"Cleaned up old file: {filename}")
    except Exception as e:
        print(f"Error during cleanup: {e}")

def get_file_info(file_path):
    """Get file information"""
    try:
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
    except Exception:
        return None

@app.route('/')
def home():
    """Serve the main web interface"""
    return render_template('index.html')

@app.route('/api')
def api_info():
    """API information and documentation"""
    return jsonify({
        "name": "Vision API",
        "version": "1.0.0",
        "description": "Professional image processing and computer vision API",
        "author": "Vision API Team",
        "endpoints": {
            "GET /": "Web interface for image processing",
            "GET /api": "This API information",
            "GET /health": "API health check",
            "GET /filters": "Get available filters and their parameters",
            "POST /process": "Process image with selected filter",
            "GET /processed/<filename>": "Download processed image",
            "GET /stats": "API usage statistics"
        },
        "supported_formats": {
            "input": ["JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF"],
            "output": ["JPEG", "PNG"]
        },
        "limits": {
            "max_file_size": "16MB",
            "max_image_dimensions": "10000x10000px",
            "file_retention": "1 hour"
        }
    })

@app.route('/health')
def health_check():
    """API health check endpoint"""
    try:
        # Test basic functionality
        test_image = Image.new('RGB', (100, 100), color='red')
        test_bytes = image_to_bytes(test_image)
        
        # Test filter functionality
        filters = get_available_filters()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "message": "Vision API is running perfectly!",
            "services": {
                "image_processing": "operational",
                "filter_engine": "operational",
                "file_storage": "operational"
            },
            "available_filters": len(filters),
            "uptime": "healthy"
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "message": f"Health check failed: {str(e)}",
            "error": str(e)
        }), 500

@app.route('/filters')
def get_filters():
    """Get available filters and their parameters"""
    try:
        filters_info = get_available_filters()
        return jsonify({
            "filters": filters_info,
            "count": len(filters_info),
            "categories": {
                "color": ["invert", "grayscale"],
                "enhancement": ["contrast", "sharpen"],
                "effects": ["blur"]
            }
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get filters: {str(e)}"}), 500

@app.route('/process', methods=['POST'])
def process_image():
    """Process uploaded image with selected filter"""
    start_time = time.time()
    
    try:
        # Validate request
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        if 'filter' not in request.form:
            return jsonify({"error": "No filter specified"}), 400
        
        file = request.files['image']
        filter_name = request.form['filter']
        
        # Validate file
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                "error": f"Unsupported file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        # Validate filter
        available_filters = get_available_filters()
        if filter_name not in available_filters:
            return jsonify({
                "error": f"Unknown filter '{filter_name}'. Available: {', '.join(available_filters.keys())}"
            }), 400
        
        # Read and validate image
        image_data = file.read()
        if len(image_data) == 0:
            return jsonify({"error": "Empty file"}), 400
        
        try:
            image = validate_image(image_data)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        # Collect filter parameters
        filter_params = {}
        if filter_name == 'contrast':
            factor = request.form.get('factor', 1.5)
            try:
                filter_params['factor'] = float(factor)
            except ValueError:
                return jsonify({"error": "Invalid contrast factor"}), 400
                
        elif filter_name == 'blur':
            radius = request.form.get('radius', 2.0)
            try:
                filter_params['radius'] = float(radius)
            except ValueError:
                return jsonify({"error": "Invalid blur radius"}), 400
                
        elif filter_name == 'sharpen':
            factor = request.form.get('factor', 2.0)
            try:
                filter_params['factor'] = float(factor)
            except ValueError:
                return jsonify({"error": "Invalid sharpen factor"}), 400
        
        # Apply filter
        try:
            filtered_image = apply_filter(image, filter_name, **filter_params)
        except ValueError as e:
            return jsonify({"error": f"Filter processing failed: {str(e)}"}), 400
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        original_ext = file.filename.rsplit('.', 1)[1].lower()
        processed_filename = f"{file_id}_{filter_name}.{original_ext}"
        processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
        
        # Save processed image
        try:
            if original_ext in ['jpg', 'jpeg']:
                output_format = 'JPEG'
            else:
                output_format = 'PNG'
                
            processed_bytes = image_to_bytes(filtered_image, format=output_format)
            
            with open(processed_path, 'wb') as f:
                f.write(processed_bytes)
                
        except Exception as e:
            return jsonify({"error": f"Failed to save processed image: {str(e)}"}), 500
        
        # Calculate processing time
        processing_time = round((time.time() - start_time) * 1000, 2)  # milliseconds
        
        # Clean up old files (async)
        try:
            cleanup_old_files()
        except Exception:
            pass  # Don't fail the request if cleanup fails
        
        # Return success response
        return jsonify({
            "success": True,
            "message": "Image processed successfully",
            "filename": processed_filename,
            "filter": filter_name,
            "parameters": filter_params,
            "processing_time": processing_time,
            "original_size": f"{image.size[0]}x{image.size[1]}",
            "output_format": output_format,
            "file_size": len(processed_bytes)
        })
        
    except Exception as e:
        processing_time = round((time.time() - start_time) * 1000, 2)
        app.logger.error(f"Unexpected error in process_image: {str(e)}")
        return jsonify({
            "error": f"Internal server error: {str(e)}",
            "processing_time": processing_time
        }), 500

@app.route('/processed/<filename>')
def download_processed_image(filename):
    """Download or serve processed image"""
    try:
        # Security: ensure filename is safe
        filename = secure_filename(filename)
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            abort(404)
        
        # Get format from query parameter
        output_format = request.args.get('format', 'JPEG').upper()
        download = request.args.get('download', 'false').lower() == 'true'
        
        # If format conversion is requested
        if output_format in ['JPEG', 'PNG'] and (output_format.lower() not in filename.lower()):
            try:
                # Load and convert image
                with Image.open(file_path) as img:
                    converted_bytes = image_to_bytes(img, format=output_format)
                
                # Create response
                response_io = io.BytesIO(converted_bytes)
                response_io.seek(0)
                
                # Set appropriate mimetype
                mimetype = 'image/jpeg' if output_format == 'JPEG' else 'image/png'
                
                # Generate new filename
                base_name = filename.rsplit('.', 1)[0]
                new_filename = f"{base_name}.{output_format.lower()}"
                
                return send_file(
                    response_io,
                    mimetype=mimetype,
                    as_attachment=download,
                    download_name=new_filename if download else None
                )
                
            except Exception as e:
                return jsonify({"error": f"Format conversion failed: {str(e)}"}), 500
        
        # Serve original processed file
        return send_file(
            file_path,
            as_attachment=download,
            download_name=filename if download else None
        )
        
    except Exception as e:
        app.logger.error(f"Error serving processed image: {str(e)}")
        return jsonify({"error": "Failed to serve image"}), 500

@app.route('/stats')
def get_stats():
    """Get API usage statistics"""
    try:
        upload_count = len([f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                           if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f))])
        processed_count = len([f for f in os.listdir(app.config['PROCESSED_FOLDER']) 
                              if os.path.isfile(os.path.join(app.config['PROCESSED_FOLDER'], f))])
        
        # Calculate total file sizes
        def get_folder_size(folder):
            total = 0
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    total += os.path.getsize(filepath)
            return total
        
        upload_size = get_folder_size(app.config['UPLOAD_FOLDER'])
        processed_size = get_folder_size(app.config['PROCESSED_FOLDER'])
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "files": {
                "uploaded": upload_count,
                "processed": processed_count,
                "total": upload_count + processed_count
            },
            "storage": {
                "uploads_size_mb": round(upload_size / 1024 / 1024, 2),
                "processed_size_mb": round(processed_size / 1024 / 1024, 2),
                "total_size_mb": round((upload_size + processed_size) / 1024 / 1024, 2)
            },
            "filters": {
                "available": len(get_available_filters()),
                "categories": ["color", "enhancement", "effects"]
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get stats: {str(e)}"}), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({
        "error": "File too large",
        "message": "Maximum file size is 16MB",
        "max_size": "16MB"
    }), 413

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        "error": "Not found",
        "message": "The requested resource was not found"
    }), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

if __name__ == '__main__':
    # Run cleanup on startup
    try:
        cleanup_old_files()
        print("✅ Startup cleanup completed")
    except Exception as e:
        print(f"⚠️ Startup cleanup failed: {e}")
    
    print("🚀 Starting Vision API Server...")
    print("=" * 50)
    print("📱 Web Interface: http://127.0.0.1:5000")
    print("🔧 API Documentation: http://127.0.0.1:5000/api")
    print("❤️ Health Check: http://127.0.0.1:5000/health")
    print("🎨 Available Filters: http://127.0.0.1:5000/filters")
    print("📊 Statistics: http://127.0.0.1:5000/stats")
    print("=" * 50)
    print("💡 Supported Filters: invert, grayscale, contrast, blur, sharpen")
    print("📁 Max File Size: 16MB")
    print("🖼️ Max Dimensions: 10000x10000px")
    print("⏰ File Retention: 1 hour")
    print("=" * 50)
    
    # Run the Flask development server
    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000,
        threaded=True
    )
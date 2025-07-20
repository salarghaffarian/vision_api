// Vision API - Frontend JavaScript
// Handles image upload, filter selection, processing, and download

class VisionAPI {
    constructor() {
        this.selectedFilter = null;
        this.uploadedImage = null;
        this.processedImageUrl = null;
        this.apiBase = window.location.origin;
        
        this.initializeEventListeners();
        this.checkServerHealth();
        this.initializeSliders();
    }

    // Initialize all event listeners
    initializeEventListeners() {
        // Upload area events
        const uploadArea = document.getElementById('upload-area');
        const imageInput = document.getElementById('image-input');

        uploadArea.addEventListener('click', () => imageInput.click());
        uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
        uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
        uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        
        imageInput.addEventListener('change', this.handleImageSelect.bind(this));

        // Filter selection events
        document.querySelectorAll('.filter-card').forEach(card => {
            card.addEventListener('click', () => this.selectFilter(card.dataset.filter));
        });

        // Button events
        document.getElementById('process-btn').addEventListener('click', this.processImage.bind(this));
        document.getElementById('reset-btn').addEventListener('click', this.resetInterface.bind(this));
        document.getElementById('download-btn').addEventListener('click', this.downloadImage.bind(this));

        // Keyboard shortcuts
        document.addEventListener('keydown', this.handleKeyboard.bind(this));
    }

    // Initialize parameter sliders
    initializeSliders() {
        const sliders = [
            { id: 'contrast-factor', valueId: 'contrast-value' },
            { id: 'blur-radius', valueId: 'blur-value' },
            { id: 'sharpen-factor', valueId: 'sharpen-value' }
        ];

        sliders.forEach(slider => {
            const input = document.getElementById(slider.id);
            const valueDisplay = document.getElementById(slider.valueId);
            
            if (input && valueDisplay) {
                input.addEventListener('input', (e) => {
                    valueDisplay.textContent = parseFloat(e.target.value).toFixed(1);
                });
            }
        });
    }

    // Drag and drop handlers
    handleDragOver(e) {
        e.preventDefault();
        document.getElementById('upload-area').classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        document.getElementById('upload-area').classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        document.getElementById('upload-area').classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.handleFile(files[0]);
        }
    }

    // Handle image selection
    handleImageSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.handleFile(file);
        }
    }

    // Handle file processing
    handleFile(file) {
        // Validate file type
        const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/tiff'];
        if (!validTypes.includes(file.type)) {
            this.showError('upload-error', 'Please select a valid image file (JPEG, PNG, WEBP, BMP, TIFF)');
            return;
        }

        // Validate file size (10MB limit)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            this.showError('upload-error', 'File size too large. Maximum size is 10MB');
            return;
        }

        this.uploadedImage = file;
        this.displayOriginalImage(file);
        this.hideError('upload-error');
        
        // Show preview and filter sections
        document.getElementById('filter-toolbar').style.display = 'block';
        
        // Reset processed image
        this.resetProcessedImage();
    }

    // Display original image
    displayOriginalImage(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = document.getElementById('original-image');
            img.src = e.target.result;
            img.style.display = 'block';
            
            // Create image object to get dimensions
            const imageObj = new Image();
            imageObj.onload = () => {
                const info = `${imageObj.width}×${imageObj.height}px • ${this.formatFileSize(file.size)} • ${file.type.split('/')[1].toUpperCase()}`;
                document.getElementById('original-info').textContent = info;
            };
            imageObj.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    // Format file size for display
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Filter selection
    selectFilter(filterName) {
        // Remove previous selection
        document.querySelectorAll('.filter-card').forEach(card => {
            card.classList.remove('selected');
        });

        // Add selection to clicked card
        document.querySelector(`[data-filter="${filterName}"]`).classList.add('selected');
        
        this.selectedFilter = filterName;
        this.showFilterParameters(filterName);
        
        // Enable process button
        document.getElementById('process-btn').disabled = false;
    }

    // Show/hide filter parameters
    showFilterParameters(filterName) {
        // Hide all parameter groups
        document.querySelectorAll('.parameter-group').forEach(group => {
            group.style.display = 'none';
        });

        // Show parameters section if filter has parameters
        const hasParameters = ['contrast', 'blur', 'sharpen'].includes(filterName);
        const parametersSection = document.getElementById('parameters-section');
        
        if (hasParameters) {
            parametersSection.style.display = 'block';
            document.getElementById(`${filterName}-params`).style.display = 'block';
        } else {
            parametersSection.style.display = 'none';
        }
    }

    // Process image with selected filter
    async processImage() {
        if (!this.uploadedImage || !this.selectedFilter) {
            this.showError('process-error', 'Please select an image and filter first');
            return;
        }

        const processBtn = document.getElementById('process-btn');
        const originalText = processBtn.innerHTML;
        
        // Show loading state
        processBtn.innerHTML = '<div class="loading"></div> Processing...';
        processBtn.disabled = true;

        try {
            const formData = new FormData();
            formData.append('image', this.uploadedImage);
            formData.append('filter', this.selectedFilter);

            // Add filter parameters if applicable
            this.addFilterParameters(formData);

            const response = await fetch(`${this.apiBase}/process`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                this.displayProcessedImage(result);
                this.showSuccess('process-result', 'Image processed successfully!');
                this.hideError('process-error');
                showToast('Image processed successfully!', 'success');
            } else {
                throw new Error(result.error || 'Processing failed');
            }

        } catch (error) {
            this.showError('process-error', `Processing failed: ${error.message}`);
            showToast(`Processing failed: ${error.message}`, 'error');
        } finally {
            // Restore button state
            processBtn.innerHTML = originalText;
            processBtn.disabled = false;
        }
    }

    // Add filter parameters to form data
    addFilterParameters(formData) {
        switch (this.selectedFilter) {
            case 'contrast':
                const contrastValue = document.getElementById('contrast-factor').value;
                formData.append('factor', contrastValue);
                break;
            case 'blur':
                const blurValue = document.getElementById('blur-radius').value;
                formData.append('radius', blurValue);
                break;
            case 'sharpen':
                const sharpenValue = document.getElementById('sharpen-factor').value;
                formData.append('factor', sharpenValue);
                break;
        }
    }

    // Display processed image
    displayProcessedImage(result) {
        const processedImg = document.getElementById('processed-image');
        const placeholder = document.getElementById('processed-placeholder');
        
        // Create image URL from response
        this.processedImageUrl = `${this.apiBase}/processed/${result.filename}`;
        
        processedImg.src = this.processedImageUrl;
        processedImg.style.display = 'block';
        placeholder.style.display = 'none';
        
        // Update processed image info
        const info = `${result.filter} filter applied • ${result.processing_time}ms`;
        document.getElementById('processed-info').textContent = info;
        
        // Show download section
        document.getElementById('download-section').style.display = 'block';
    }

    // Download processed image
    downloadImage() {
        if (!this.processedImageUrl) {
            this.showError('process-error', 'No processed image to download');
            return;
        }

        const format = document.getElementById('format-select').value;
        const link = document.createElement('a');
        
        // Add format parameter to download URL
        const downloadUrl = `${this.processedImageUrl}?format=${format}&download=true`;
        
        link.href = downloadUrl;
        link.download = `processed_image_${this.selectedFilter}.${format.toLowerCase()}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showToast(`Downloaded as ${format}!`, 'success');
    }

    // Reset interface
    resetInterface() {
        // Reset all sections
        document.getElementById('filter-toolbar').style.display = 'none';
        document.getElementById('download-section').style.display = 'none';
        document.getElementById('parameters-section').style.display = 'none';

        // Reset selections
        document.querySelectorAll('.filter-card').forEach(card => {
            card.classList.remove('selected');
        });

        // Reset form
        document.getElementById('image-input').value = '';
        document.getElementById('process-btn').disabled = true;

        // Reset variables
        this.selectedFilter = null;
        this.uploadedImage = null;
        this.processedImageUrl = null;

        // Hide errors and results
        this.hideError('upload-error');
        this.hideError('process-error');
        this.hideResult('process-result');

        // Reset processed image
        this.resetProcessedImage();
        
        showToast('Interface reset!', 'success');
    }

    // Reset processed image display
    resetProcessedImage() {
        const processedImg = document.getElementById('processed-image');
        const placeholder = document.getElementById('processed-placeholder');
        
        processedImg.style.display = 'none';
        processedImg.src = '';
        placeholder.style.display = 'flex';
        
        document.getElementById('processed-info').textContent = '';
        document.getElementById('download-section').style.display = 'none';
    }

    // Check server health
    async checkServerHealth() {
        try {
            const response = await fetch(`${this.apiBase}/health`);
            const data = await response.json();
            
            if (response.ok) {
                document.getElementById('server-status').innerHTML = `✅ ${data.message}`;
                document.getElementById('server-status').style.color = '#28a745';
            } else {
                throw new Error('Server health check failed');
            }
        } catch (error) {
            document.getElementById('server-status').innerHTML = '❌ Server not responding';
            document.getElementById('server-status').style.color = '#dc3545';
        }
    }

    // Handle keyboard shortcuts
    handleKeyboard(e) {
        // Escape key - reset interface
        if (e.key === 'Escape') {
            this.resetInterface();
        }
        
        // Enter key - process image if ready
        if (e.key === 'Enter' && this.selectedFilter && this.uploadedImage) {
            this.processImage();
        }
        
        // Number keys - quick filter selection
        const filterKeys = {
            '1': 'invert',
            '2': 'grayscale', 
            '3': 'contrast',
            '4': 'blur',
            '5': 'sharpen'
        };
        
        if (filterKeys[e.key] && this.uploadedImage) {
            this.selectFilter(filterKeys[e.key]);
        }
    }

    // Utility functions for showing/hiding messages
    showError(elementId, message) {
        const errorDiv = document.getElementById(elementId);
        errorDiv.innerHTML = `<strong>Error:</strong> ${message}`;
        errorDiv.style.display = 'block';
    }

    hideError(elementId) {
        const errorDiv = document.getElementById(elementId);
        errorDiv.style.display = 'none';
    }

    showSuccess(elementId, message) {
        const resultDiv = document.getElementById(elementId);
        resultDiv.innerHTML = `<strong>Success:</strong> ${message}`;
        resultDiv.style.display = 'block';
    }

    hideResult(elementId) {
        const resultDiv = document.getElementById(elementId);
        resultDiv.style.display = 'none';
    }
}

// Initialize the Vision API when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.visionAPI = new VisionAPI();
});

// Additional utility functions for enhanced user experience

// Prevent default drag behaviors on the page
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    document.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// Add visual feedback for successful operations
function showToast(message, type = 'success') {
    // Remove any existing toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-icon">${type === 'success' ? '✅' : '❌'}</span>
            <span class="toast-message">${message}</span>
        </div>
    `;

    // Add toast styles
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? 'linear-gradient(135deg, #28a745, #20c997)' : 'linear-gradient(135deg, #dc3545, #c82333)'};
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        z-index: 1000;
        transform: translateX(100%);
        transition: transform 0.3s ease;
        display: flex;
        align-items: center;
        gap: 10px;
        max-width: 300px;
    `;

    document.body.appendChild(toast);

    // Animate in
    setTimeout(() => {
        toast.style.transform = 'translateX(0)';
    }, 100);

    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// Export functions for global access
window.showToast = showToast;

// Add some CSS animations dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    .filter-card:active {
        transform: translateY(-2px) scale(0.98) !important;
    }
    
    .image-box img:hover {
        cursor: zoom-in;
    }
    
    .toast-content {
        display: flex;
        align-items: center;
        gap: 10px;
    }
`;
document.head.appendChild(style);
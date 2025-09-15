// Main JavaScript functionality for AI Course Generator

class CourseGenerator {
    constructor() {
        this.sessionId = null;
        this.currentStatus = 'initialized';
        this.init();
    }

    init() {
        // Initialize event listeners
        this.setupEventListeners();
        
        // Check if we're on a specific page
        this.handlePageSpecificLogic();
        
        // Setup global error handling
        this.setupErrorHandling();
    }

    setupEventListeners() {
        // File upload handling
        document.addEventListener('change', (e) => {
            if (e.target.type === 'file') {
                this.handleFileSelect(e.target);
            }
        });

        // Form submissions
        document.addEventListener('submit', (e) => {
            if (e.target.tagName === 'FORM') {
                this.handleFormSubmit(e);
            }
        });

        // Button clicks
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action]')) {
                this.handleActionButton(e);
            }
        });
    }

    handlePageSpecificLogic() {
        const path = window.location.pathname;
        
        if (path.includes('/upload')) {
            this.initUploadPage();
        } else if (path.includes('/review')) {
            this.initReviewPage();
        } else if (path.includes('/export')) {
            this.initExportPage();
        }
    }

    initUploadPage() {
        // Setup drag and drop
        this.setupDragAndDrop();
        
        // Setup file validation
        this.setupFileValidation();
    }

    initReviewPage() {
        // Load existing data
        this.loadWeeklyPlan();
        
        // Setup plan editing
        this.setupPlanEditing();
    }

    initExportPage() {
        // Setup export options
        this.setupExportOptions();
        
        // Check generation status
        this.checkGenerationStatus();
    }

    setupDragAndDrop() {
        const uploadZones = document.querySelectorAll('.upload-zone, .form-control[type="file"]');
        
        uploadZones.forEach(zone => {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                zone.addEventListener(eventName, this.handleDragEvent.bind(this), false);
            });
        });
    }

    handleDragEvent(e) {
        e.preventDefault();
        e.stopPropagation();

        const zone = e.target.closest('.upload-zone') || e.target;
        
        if (e.type === 'dragenter' || e.type === 'dragover') {
            zone.classList.add('dragover');
        } else if (e.type === 'dragleave') {
            zone.classList.remove('dragover');
        } else if (e.type === 'drop') {
            zone.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleDroppedFiles(files, zone);
            }
        }
    }

    handleDroppedFiles(files, zone) {
        const fileInput = zone.querySelector('input[type="file"]') || 
                         document.querySelector('input[type="file"]');
        
        if (fileInput) {
            fileInput.files = files;
            this.handleFileSelect(fileInput);
        }
    }

    handleFileSelect(input) {
        const files = input.files;
        const fileList = input.closest('.mb-4')?.querySelector('.file-list') ||
                        this.createFileList(input);

        // Clear existing list
        fileList.innerHTML = '';

        // Display selected files
        Array.from(files).forEach(file => {
            const fileItem = this.createFileItem(file);
            fileList.appendChild(fileItem);
        });

        // Validate files
        this.validateFiles(files);
    }

    createFileList(input) {
        const fileList = document.createElement('div');
        fileList.className = 'file-list mt-2';
        input.parentNode.appendChild(fileList);
        return fileList;
    }

    createFileItem(file) {
        const item = document.createElement('div');
        item.className = 'file-item d-flex align-items-center p-2 border rounded mb-2';
        
        const icon = this.getFileIcon(file.type);
        const size = this.formatFileSize(file.size);
        
        item.innerHTML = `
            <i class="${icon} me-2"></i>
            <div class="flex-grow-1">
                <div class="fw-bold">${file.name}</div>
                <small class="text-muted">${size}</small>
            </div>
            <span class="badge bg-success">Ready</span>
        `;
        
        return item;
    }

    getFileIcon(mimeType) {
        if (mimeType.includes('pdf')) return 'fas fa-file-pdf text-danger';
        if (mimeType.includes('word') || mimeType.includes('document')) return 'fas fa-file-word text-primary';
        return 'fas fa-file text-secondary';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    validateFiles(files) {
        const maxSize = 50 * 1024 * 1024; // 50MB
        const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword'];
        
        let hasErrors = false;
        
        Array.from(files).forEach(file => {
            if (file.size > maxSize) {
                this.showError(`File ${file.name} is too large. Maximum size is 50MB.`);
                hasErrors = true;
            }
            
            if (!allowedTypes.some(type => file.type.includes(type.split('/')[1]))) {
                this.showError(`File ${file.name} is not a supported format. Please use PDF or Word documents.`);
                hasErrors = true;
            }
        });
        
        return !hasErrors;
    }

    setupFileValidation() {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        
        fileInputs.forEach(input => {
            input.addEventListener('change', (e) => {
                this.validateFiles(e.target.files);
            });
        });
    }

    handleFormSubmit(e) {
        const form = e.target;
        const formId = form.id;
        
        if (formId === 'uploadForm') {
            e.preventDefault();
            this.handleUploadForm(form);
        } else if (formId === 'planApprovalForm') {
            e.preventDefault();
            this.handlePlanApproval(form);
        }
    }

    async handleUploadForm(form) {
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        
        // Validate files before submission
        const moduleFile = form.querySelector('input[name="module_file"]').files[0];
        if (!moduleFile) {
            this.showError('Please select a module specification file.');
            return;
        }
        
        try {
            // Show loading state
            this.setButtonLoading(submitBtn, true);
            this.showProcessingSteps();
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.handleUploadSuccess(result);
            } else {
                throw new Error(result.detail || 'Upload failed');
            }
            
        } catch (error) {
            this.handleUploadError(error);
        } finally {
            this.setButtonLoading(submitBtn, false);
        }
    }

    showProcessingSteps() {
        const processingCard = document.getElementById('processingCard');
        if (processingCard) {
            processingCard.style.display = 'block';
            
            // Simulate processing steps
            const steps = ['step1', 'step2', 'step3', 'step4'];
            steps.forEach((stepId, index) => {
                setTimeout(() => {
                    // Hide previous step
                    if (index > 0) {
                        const prevStep = document.getElementById(steps[index - 1]);
                        if (prevStep) prevStep.style.display = 'none';
                    }
                    
                    // Show current step
                    const currentStep = document.getElementById(stepId);
                    if (currentStep) currentStep.style.display = 'block';
                    
                }, index * 1500);
            });
        }
    }

    handleUploadSuccess(result) {
        this.sessionId = result.session_id || this.getSessionIdFromUrl();
        
        // Store module data
        sessionStorage.setItem('moduleData', JSON.stringify(result.module_data));
        
        // Show success message
        this.showSuccess('Files processed successfully! Redirecting to planning stage...');
        
        // Redirect after delay
        setTimeout(() => {
            window.location.href = `/review/${this.sessionId}`;
        }, 2000);
    }

    handleUploadError(error) {
        this.showError(`Upload failed: ${error.message}`);
        
        // Hide processing card
        const processingCard = document.getElementById('processingCard');
        if (processingCard) {
            processingCard.style.display = 'none';
        }
    }

    setButtonLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            button.dataset.originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        } else {
            button.disabled = false;
            button.innerHTML = button.dataset.originalText || button.innerHTML;
        }
    }

    loadWeeklyPlan() {
        // Load plan data from session storage or server
        const moduleData = JSON.parse(sessionStorage.getItem('moduleData') || '{}');
        const planData = JSON.parse(sessionStorage.getItem('weeklyPlan') || '{}');
        
        if (Object.keys(planData).length > 0) {
            this.displayWeeklyPlan(planData);
        }
    }

    setupPlanEditing() {
        // Setup inline editing for weekly plans
        document.addEventListener('input', (e) => {
            if (e.target.matches('.week-edit-input')) {
                this.handlePlanEdit(e.target);
            }
        });
        
        // Setup add/remove buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.add-item-btn')) {
                this.addPlanItem(e.target);
            } else if (e.target.matches('.remove-item-btn')) {
                this.removePlanItem(e.target);
            }
        });
    }

    handlePlanEdit(input) {
        const weekCard = input.closest('.week-card');
        if (weekCard) {
            weekCard.classList.add('edited');
        }
        
        // Auto-save changes
        this.debouncedSave();
    }

    debouncedSave() {
        clearTimeout(this.saveTimeout);
        this.saveTimeout = setTimeout(() => {
            this.saveWeeklyPlan();
        }, 1000);
    }

    saveWeeklyPlan() {
        const planData = this.extractPlanData();
        sessionStorage.setItem('weeklyPlan', JSON.stringify(planData));
        
        // Show save indicator
        this.showSuccess('Changes saved automatically', 2000);
    }

    extractPlanData() {
        const weeks = [];
        const weekCards = document.querySelectorAll('.week-card');
        
        weekCards.forEach(card => {
            const weekNumber = parseInt(card.dataset.week);
            const title = card.querySelector('.week-title-input')?.value || '';
            const learningOutcomes = this.extractListItems(card, '.learning-outcomes input');
            const lectureTopics = this.extractListItems(card, '.lecture-topics input');
            const tutorialActivities = this.extractListItems(card, '.tutorial-activities input');
            const labActivities = this.extractListItems(card, '.lab-activities input');
            
            weeks.push({
                week_number: weekNumber,
                title,
                learning_outcomes: learningOutcomes,
                lecture_topics: lectureTopics,
                tutorial_activities: tutorialActivities,
                lab_activities: labActivities
            });
        });
        
        return { weeks };
    }

    extractListItems(container, selector) {
        const inputs = container.querySelectorAll(selector);
        return Array.from(inputs).map(input => input.value).filter(value => value.trim());
    }

    setupExportOptions() {
        const exportCards = document.querySelectorAll('.export-card');
        
        exportCards.forEach(card => {
            card.addEventListener('click', () => {
                const format = card.dataset.format;
                this.initiateExport(format);
            });
        });
    }

    async initiateExport(format) {
        try {
            this.showSuccess(`Preparing ${format.toUpperCase()} export...`);
            
            // Implementation would depend on specific export requirements
            console.log(`Exporting in ${format} format`);
            
        } catch (error) {
            this.showError(`Export failed: ${error.message}`);
        }
    }

    checkGenerationStatus() {
        const sessionId = this.getSessionIdFromUrl();
        if (sessionId) {
            // Poll for generation status
            this.pollGenerationStatus(sessionId);
        }
    }

    async pollGenerationStatus(sessionId) {
        try {
            const response = await fetch(`/api/status/${sessionId}`);
            const status = await response.json();
            
            this.updateStatusDisplay(status);
            
            if (status.status === 'completed') {
                this.enableDownloadOptions();
            } else if (status.status === 'generating') {
                // Continue polling
                setTimeout(() => this.pollGenerationStatus(sessionId), 5000);
            }
            
        } catch (error) {
            console.error('Status check failed:', error);
        }
    }

    updateStatusDisplay(status) {
        const statusElements = document.querySelectorAll('.status-indicator');
        statusElements.forEach(element => {
            const step = element.dataset.step;
            if (status.completed_steps?.includes(step)) {
                element.className = 'status-indicator completed';
            } else if (status.current_step === step) {
                element.className = 'status-indicator processing';
            }
        });
    }

    enableDownloadOptions() {
        const downloadBtns = document.querySelectorAll('.download-btn');
        downloadBtns.forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('btn-secondary');
            btn.classList.add('btn-success');
        });
    }

    getSessionIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        return pathParts[pathParts.length - 1];
    }

    handleActionButton(e) {
        const button = e.target;
        const action = button.dataset.action;
        
        switch (action) {
            case 'generate-plan':
                this.generateWeeklyPlan();
                break;
            case 'approve-plan':
                this.approvePlan();
                break;
            case 'generate-content':
                this.generateContent();
                break;
            case 'download-package':
                this.downloadPackage();
                break;
        }
    }

    async generateWeeklyPlan() {
        const sessionId = this.getSessionIdFromUrl();
        
        try {
            const response = await fetch('/api/generate-plan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `session_id=${sessionId}`
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.displayWeeklyPlan(result.week_plans);
                this.showSuccess('Weekly plan generated successfully!');
            } else {
                throw new Error(result.detail || 'Plan generation failed');
            }
            
        } catch (error) {
            this.showError(`Plan generation failed: ${error.message}`);
        }
    }

    displayWeeklyPlan(weekPlans) {
        const container = document.getElementById('weeklyPlanContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        weekPlans.forEach(week => {
            const weekCard = this.createWeekCard(week);
            container.appendChild(weekCard);
        });
    }

    createWeekCard(week) {
        const card = document.createElement('div');
        card.className = 'week-card card mb-3 fade-in';
        card.dataset.week = week.week_number;
        
        card.innerHTML = `
            <div class="card-header">
                <div class="row align-items-center">
                    <div class="col">
                        <h6 class="mb-0">Week ${week.week_number}: 
                            <input type="text" class="form-control d-inline-block week-title-input week-edit-input" 
                                   style="width: 300px; display: inline-block;" 
                                   value="${week.title}">
                        </h6>
                    </div>
                    <div class="col-auto">
                        <button class="btn btn-sm btn-outline-light" type="button" 
                                data-bs-toggle="collapse" data-bs-target="#week${week.week_number}Details">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="collapse" id="week${week.week_number}Details">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label"><strong>Learning Outcomes</strong></label>
                            <div class="learning-outcomes">
                                ${this.createEditableList(week.learning_outcomes || [])}
                            </div>
                            <button class="btn btn-sm btn-outline-success add-item-btn" data-target=".learning-outcomes">
                                <i class="fas fa-plus"></i> Add Outcome
                            </button>
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <label class="form-label"><strong>Lecture Topics</strong></label>
                            <div class="lecture-topics">
                                ${this.createEditableList(week.lecture_topics || [])}
                            </div>
                            <button class="btn btn-sm btn-outline-success add-item-btn" data-target=".lecture-topics">
                                <i class="fas fa-plus"></i> Add Topic
                            </button>
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <label class="form-label"><strong>Tutorial Activities</strong></label>
                            <div class="tutorial-activities">
                                ${this.createEditableList(week.tutorial_activities || [])}
                            </div>
                            <button class="btn btn-sm btn-outline-success add-item-btn" data-target=".tutorial-activities">
                                <i class="fas fa-plus"></i> Add Activity
                            </button>
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <label class="form-label"><strong>Lab Activities</strong></label>
                            <div class="lab-activities">
                                ${this.createEditableList(week.lab_activities || [])}
                            </div>
                            <button class="btn btn-sm btn-outline-success add-item-btn" data-target=".lab-activities">
                                <i class="fas fa-plus"></i> Add Lab
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return card;
    }

    createEditableList(items) {
        if (!items.length) {
            return '<div class="text-muted">No items added yet</div>';
        }
        
        return items.map(item => `
            <div class="input-group mb-2">
                <input type="text" class="form-control week-edit-input" value="${item}">
                <button class="btn btn-outline-danger btn-sm remove-item-btn" type="button">×</button>
            </div>
        `).join('');
    }

    addPlanItem(button) {
        const target = button.closest('.card-body').querySelector(button.dataset.target);
        const newItem = document.createElement('div');
        newItem.className = 'input-group mb-2';
        newItem.innerHTML = `
            <input type="text" class="form-control week-edit-input" placeholder="Enter new item...">
            <button class="btn btn-outline-danger btn-sm remove-item-btn" type="button">×</button>
        `;
        
        // Remove "no items" message if present
        const noItemsMsg = target.querySelector('.text-muted');
        if (noItemsMsg) {
            noItemsMsg.remove();
        }
        
        target.appendChild(newItem);
        newItem.querySelector('input').focus();
    }

    removePlanItem(button) {
        const item = button.closest('.input-group');
        const container = item.parentNode;
        
        item.remove();
        
        // Add "no items" message if container is empty
        if (container.children.length === 0) {
            container.innerHTML = '<div class="text-muted">No items added yet</div>';
        }
        
        this.debouncedSave();
    }

    async approvePlan() {
        const sessionId = this.getSessionIdFromUrl();
        const planData = this.extractPlanData();
        
        try {
            const response = await fetch('/api/approve-plan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `session_id=${sessionId}&approved_weeks=${encodeURIComponent(JSON.stringify(planData.weeks))}`
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess('Plan approved! Proceeding to content generation...');
                setTimeout(() => {
                    this.generateContent();
                }, 2000);
            } else {
                throw new Error(result.detail || 'Plan approval failed');
            }
            
        } catch (error) {
            this.showError(`Plan approval failed: ${error.message}`);
        }
    }

    async generateContent() {
        const sessionId = this.getSessionIdFromUrl();
        
        try {
            this.showSuccess('Starting content generation... This may take several minutes.');
            
            const response = await fetch('/api/generate-content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `session_id=${sessionId}`
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess('Content generation completed! Redirecting to export page...');
                setTimeout(() => {
                    window.location.href = `/export/${sessionId}`;
                }, 2000);
            } else {
                throw new Error(result.detail || 'Content generation failed');
            }
            
        } catch (error) {
            this.showError(`Content generation failed: ${error.message}`);
        }
    }

    async downloadPackage() {
        const sessionId = this.getSessionIdFromUrl();
        
        try {
            // First, package the content
            const response = await fetch('/api/package-content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `session_id=${sessionId}`
            });
            
            const result = await response.json();
            
            if (response.ok) {
                // Trigger download
                window.location.href = result.download_url;
            } else {
                throw new Error(result.detail || 'Packaging failed');
            }
            
        } catch (error) {
            this.showError(`Download failed: ${error.message}`);
        }
    }

    setupErrorHandling() {
        window.addEventListener('error', (e) => {
            console.error('Global error:', e.error);
            this.showError('An unexpected error occurred. Please refresh the page and try again.');
        });

        window.addEventListener('unhandledrejection', (e) => {
            console.error('Unhandled promise rejection:', e.reason);
            this.showError('A network error occurred. Please check your connection and try again.');
        });
    }

    showSuccess(message, duration = 5000) {
        this.showAlert(message, 'success', duration);
    }

    showError(message, duration = 10000) {
        this.showAlert(message, 'danger', duration);
    }

    showInfo(message, duration = 5000) {
        this.showAlert(message, 'info', duration);
    }

    showAlert(message, type = 'info', duration = 5000) {
        // Find or create alerts container
        let container = document.getElementById('alertsContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'alertsContainer';
            container.className = 'position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }

        // Create alert element
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show slide-in-left`;
        alert.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        container.appendChild(alert);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, duration);
        }
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new CourseGenerator();
});

// Utility functions
window.CourseGeneratorUtils = {
    formatFileSize: (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    validateEmail: (email) => {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },

    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};
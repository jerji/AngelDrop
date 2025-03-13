/**
 * File Upload Handler
 * Manages the drag-and-drop file upload interface, file staging, and form submission.
 */

// Global variables for UI elements
const dropArea = document.getElementById('drop-area');
const fileElem = document.getElementById('fileElem');
const progressBar = document.getElementById('progress-bar');
const fileList = document.getElementById('file-list');
const uploadForm = document.getElementById('upload-form');
const writingStatus = document.getElementById('writing-status');
const dots = document.getElementById('dots');

// Array to store files staged for upload
let stagedFiles = [];
let dotInterval; // For animating the writing status dots

/**
 * Initialize event listeners for drag and drop functionality
 */
function initializeDragAndDrop() {
    // Prevent default behaviors for drag events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        document.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop area when dragging over it
    ['dragenter', 'dragover'].forEach(eventName => {
        document.addEventListener(eventName, highlight, false);
    });
    
    // Remove highlight when leaving drop area or after drop
    ['dragleave', 'drop'].forEach(eventName => {
        document.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle file drop
    document.addEventListener('drop', handleDrop, false);
}

/**
 * Prevent default behaviors for events
 */
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

/**
 * Highlight the drop area when dragging over it
 */
function highlight(e) {
    if (dropArea) {
        dropArea.classList.add('highlight');
    }
}

/**
 * Remove highlight from drop area
 */
function unhighlight(e) {
    if (dropArea) {
        dropArea.classList.remove('highlight');
    }
}

/**
 * Handle file drop event
 */
function handleDrop(e) {
    let dt = e.dataTransfer;
    let files = dt.files;
    handleFiles(files);
}

/**
 * Process files from drop or file input
 * @param {FileList} files - Files to be processed
 */
function handleFiles(files) {
    // Add files to the stagedFiles array
    stagedFiles = stagedFiles.concat([...files]);
    
    // Update UI to show staged files
    renderFileList();
}

/**
 * Render the list of staged files in the UI
 */
function renderFileList() {
    // Clear the existing file list
    fileList.innerHTML = "";
    
    // Add each file to the list with a remove button
    stagedFiles.forEach((file, index) => {
        let fileItem = document.createElement('div');
        fileItem.classList.add('file-item');
        
        let fileName = document.createElement('span');
        fileName.textContent = `${file.name} (Ready for Upload)`;
        fileItem.appendChild(fileName);
        
        let removeButton = document.createElement('span');
        removeButton.textContent = 'X';
        removeButton.classList.add('remove-button');
        removeButton.addEventListener('click', () => removeFile(index));
        fileItem.appendChild(removeButton);
        
        fileList.appendChild(fileItem);
    });
    
    // Show or hide the upload button based on whether there are files to upload
    document.getElementById("submit-button").style.display = 
        stagedFiles.length > 0 ? "block" : "none";
}

/**
 * Remove a file from the staged files list
 * @param {number} index - Index of file to remove
 */
function removeFile(index) {
    stagedFiles.splice(index, 1);
    renderFileList();
}

/**
 * Animate dots for the "Writing to disk" status
 */
function animateDots() {
    let dotCount = 0;
    dotInterval = setInterval(() => {
        dotCount = (dotCount + 1) % 4; // Cycle through 0-3
        dots.textContent = '.'.repeat(dotCount);
    }, 500); // Change every 500ms
}

/**
 * Stop the dots animation
 */
function stopAnimateDots() {
    clearInterval(dotInterval);
    dots.textContent = '';
}

/**
 * Handle form submission for file uploads
 * @param {Event} event - Form submission event
 */
function handleFormSubmit(event) {
    event.preventDefault();  // Prevent the default form submission
    
    // Create FormData object to send files
    let formData = new FormData();
    stagedFiles.forEach(file => {
        formData.append('file', file);
    });
    
    // Add password if provided
    const passwordField = document.getElementById('link_password');
    if (passwordField) {
        formData.append('link_password', passwordField.value);
    }
    
    // Create and configure XHR request
    let xhr = new XMLHttpRequest();
    xhr.open('POST', window.location.href, true);
    
    // Track upload progress
    xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            progressBar.value = percentComplete;
            
            // Show writing status when upload is complete
            if (percentComplete === 100) {
                progressBar.classList.add('writing');
                writingStatus.style.display = 'block';
                animateDots();
            }
        }
    });
    
    // Handle successful response
    xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
            console.log('Success:', xhr.responseText);
            
            // Reset UI elements
            resetUploadUI();
            
            // Display flash messages if any
            const parser = new DOMParser();
            const doc = parser.parseFromString(xhr.responseText, 'text/html');
            let flashMessage = doc.querySelector('.flash-messages');
            
            if (flashMessage) {
                document.querySelector('.container').prepend(flashMessage);
            } else {
                window.location.reload();
            }
        } else {
            // Handle error
            console.error('Error:', xhr.status, xhr.statusText);
            resetUploadUI();
        }
    };
    
    // Handle network errors
    xhr.onerror = function() {
        console.error('Network Error');
        resetUploadUI();
    };
    
    // Send the request
    xhr.send(formData);
}

/**
 * Reset the upload UI after upload completion or error
 */
function resetUploadUI() {
    progressBar.value = 0;
    progressBar.classList.remove('writing');
    writingStatus.style.display = 'none';
    stopAnimateDots();
    fileList.innerHTML = "";
    stagedFiles = [];
    document.getElementById("submit-button").style.display = "none";
}

// Initialize the application
function init() {
    initializeDragAndDrop();
    
    // Set up form submission handler
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFormSubmit);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', init);
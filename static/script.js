/**
 * File Uploader Script
 * Handles drag & drop, file staging, AJAX upload with progress, and status display.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Only run upload specific code if the upload form exists on the page
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        initializeUploadFeatures();
    }

    initializeAdminFeatures();

});

// --- Admin Features ---
function initializeAdminFeatures() {
    // Copy button functionality (as previously implemented)
    document.querySelectorAll('.copy-button').forEach(button => {
        button.addEventListener('click', function () {
            const linkToCopy = this.dataset.link;
            navigator.clipboard.writeText(linkToCopy)
                .then(() => {
                    const originalText = this.textContent;
                    this.textContent = 'Copied!';
                    this.disabled = true;
                    setTimeout(() => {
                        this.textContent = originalText;
                        this.disabled = false;
                    }, 1500);
                })
                .catch(err => {
                    console.error('Could not copy text: ', err);
                    alert('Could not copy link automatically. Please copy manually:\n' + linkToCopy);
                });
        });
    });

}


// --- Upload Features ---
function initializeUploadFeatures() {
    const dropArea = document.getElementById('drop-area');
    const fileElem = document.getElementById('fileElem'); // Input element
    const progressBar = document.getElementById('progress-bar');
    const progressPercent = document.getElementById('progress-percent');
    const fileListContainer = document.getElementById('file-list'); // Renamed for clarity
    const uploadForm = document.getElementById('upload-form');
    const submitButton = document.getElementById('submit-button');
    const uploadingStatus = document.getElementById('uploading-status');
    const writingStatus = document.getElementById('writing-status');
    const dots = document.getElementById('dots'); // Dots for writing status

    let stagedFiles = []; // Files selected by the user
    let dotInterval;

    // --- Drag and Drop Initialization ---
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false); // Prevent browser opening file
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
        });

        dropArea.addEventListener('drop', handleDrop, false);
    } else {
        console.warn("Drop area element not found.");
    }

    // --- Form and Input Handling ---
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFormSubmit);
    } else {
        console.error("Upload form element not found!");
    }

    // Note: The input 'onchange' is handled directly in the HTML: onchange="handleFileSelect(this.files)"
    // Make sure the function handleFileSelect is defined globally or attached to window.
    window.handleFileSelect = (files) => {
        handleFiles(files);
    };


    // --- Core Functions ---

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    function handleFiles(files) {
        const newFiles = [...files]; // Convert FileList to array

        // Optional: Filter for duplicates or disallowed types here if needed
        // Example: const uniqueNewFiles = newFiles.filter(nf => !stagedFiles.some(sf => sf.name === nf.name && sf.size === nf.size));

        stagedFiles = stagedFiles.concat(newFiles); // Add new files to the stage
        renderFileList(); // Update the UI
    }

    function renderFileList() {
        fileListContainer.innerHTML = ""; // Clear current list

        if (stagedFiles.length === 0) {
            submitButton.style.display = 'none'; // Hide button if no files
            return;
        }

        stagedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.classList.add('file-item');
            fileItem.dataset.fileIndex = index; // Store index for reference

            const fileName = document.createElement('span');
            fileName.classList.add('file-name');
            fileName.textContent = file.name;
            fileItem.appendChild(fileName);

            const fileSize = document.createElement('span');
            fileSize.classList.add('file-size');
            fileSize.textContent = `(${(file.size / 1024 / 1024).toFixed(2)} MB)`; // Display size
            fileItem.appendChild(fileSize);

            const fileStatus = document.createElement('span');
            fileStatus.classList.add('file-status');
            fileStatus.textContent = ' (Ready)'; // Initial status
            fileItem.appendChild(fileStatus);

            const removeButton = document.createElement('span');
            removeButton.textContent = '✖'; // Use multiplication sign for better visuals
            removeButton.classList.add('remove-button');
            removeButton.title = 'Remove file';
            removeButton.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent triggering other clicks
                removeFile(index);
            });
            fileItem.appendChild(removeButton);

            fileListContainer.appendChild(fileItem);
        });

        submitButton.style.display = 'block'; // Show upload button
    }

    function removeFile(index) {
        stagedFiles.splice(index, 1); // Remove file from array by index
        renderFileList(); // Re-render the list
    }

    function handleFormSubmit(event) {
        event.preventDefault(); // Stop standard form submission

        if (stagedFiles.length === 0) {
            alert("Please select files to upload.");
            return;
        }

        // Disable submit button during upload
        submitButton.disabled = true;
        submitButton.textContent = 'Uploading...';


        // Show progress bar and status
        progressBar.style.display = 'block';
        uploadingStatus.style.display = 'block';
        progressBar.value = 0;
        progressPercent.textContent = '0';
        writingStatus.style.display = 'none'; // Hide writing status initially

        // Clear previous file statuses in UI
        fileListContainer.querySelectorAll('.file-status').forEach(span => span.textContent = ' (Uploading...)');
        fileListContainer.querySelectorAll('.remove-button').forEach(btn => btn.style.display = 'none'); // Hide remove buttons

        // Prepare FormData
        const formData = new FormData(); // No need to pass the form element for AJAX
        stagedFiles.forEach(file => {
            formData.append('file', file); // Use 'file' as expected by Flask backend
        });

        // Append password if the field exists
        const passwordField = document.getElementById('link_password');
        if (passwordField) {
            formData.append('link_password', passwordField.value);
        }

        // --- AJAX Upload ---
        const xhr = new XMLHttpRequest();
        xhr.open('POST', uploadForm.action, true); // Use form's action URL
        xhr.setRequestHeader('Accept', 'application/json'); // Indicate we prefer JSON response

        // Progress Listener
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                progressBar.value = percentComplete;
                progressPercent.textContent = percentComplete;

                if (percentComplete === 100) {
                    // Upload transport complete, now server processing starts
                    uploadingStatus.style.display = 'none';
                    writingStatus.style.display = 'block';
                    progressBar.classList.add('writing'); // Style change for processing
                    animateDots(); // Start dots animation
                }
            }
        });

        // Load Listener (Request finished)
        xhr.onload = () => {
            stopAnimateDots(); // Stop dots animation
            progressBar.classList.remove('writing');
            writingStatus.style.display = 'none'; // Hide writing status

            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    handleUploadResponse(response);
                } catch (e) {
                    console.error("Failed to parse JSON response:", e);
                    console.error("Raw response:", xhr.responseText);
                    // Display generic error message or raw response if debugging
                    updateFileStatusesGeneric("Error: Invalid server response.", false);
                    displayFlashMessages([{
                        class: 'error',
                        message: 'An unexpected error occurred after upload. Please check the server logs.'
                    }]);
                }
            } else {
                // Handle HTTP errors (4xx, 5xx)
                console.error('Upload failed:', xhr.status, xhr.statusText);
                updateFileStatusesGeneric(`Error: ${xhr.status} ${xhr.statusText}`, false);
                // Try to parse error messages if server sends JSON error
                let errorMessages = [{
                    class: 'error',
                    message: `Upload failed. Server responded with status ${xhr.status}.`
                }];
                if (xhr.status === 403) {
                    errorMessages = [{class: 'error', message: 'Invalid password. Try again'}];
                }
                try {
                    const errorResponse = JSON.parse(xhr.responseText);
                    if (errorResponse && errorResponse.messages) {
                        // Assuming backend sends similar message structure on error
                        errorMessages = parseFlashedMessages(errorResponse.messages);
                    }
                } catch (e) { /* Ignore parsing errors for error response */
                }
                displayFlashMessages(errorMessages);
            }

            // Reset UI state after handling response
            resetUploadStateAfterCompletion();
        };

        // Error Listener (Network errors)
        xhr.onerror = () => {
            console.error('Network Error during upload.');
            stopAnimateDots();
            progressBar.classList.remove('writing');
            writingStatus.style.display = 'none';
            uploadingStatus.style.display = 'none';
            progressBar.style.display = 'none';
            updateFileStatusesGeneric("Network Error", false);
            displayFlashMessages([{
                class: 'error',
                message: 'Upload failed due to a network error. Please check your connection.'
            }]);
            resetUploadStateAfterCompletion(); // Reset button etc.
        };

        // Send the data
        xhr.send(formData);
    }

    function handleUploadResponse(response) {
        // Update UI based on detailed results if available
        if (response.results && response.results.length > 0) {
            response.results.forEach(result => {
                // Find the corresponding file item in the UI
                const fileItem = Array.from(fileListContainer.children).find(item =>
                    item.querySelector('.file-name').textContent === result.filename
                );
                if (fileItem) {
                    const statusSpan = fileItem.querySelector('.file-status');
                    if (result.success) {
                        statusSpan.textContent = ' (Uploaded Successfully)';
                        statusSpan.classList.add('success');
                        statusSpan.classList.remove('error');
                    } else {
                        statusSpan.textContent = ` (Error: ${result.message})`;
                        statusSpan.classList.add('error');
                        statusSpan.classList.remove('success');
                    }
                } else {
                    console.warn(`Could not find UI element for file: ${result.filename}`);
                }
            });
        } else {
            // Fallback if no detailed results - use overall success flag
            updateFileStatusesGeneric(response.success ? "Uploaded" : "Failed", response.success);
        }

        // Display flash messages from the response
        if (response.messages) {
            const messages = parseFlashedMessages(response.messages);
            displayFlashMessages(messages);
        }

        // Clear staged files ONLY if overall success OR if detailed results show all succeeded
        // Keep files listed on partial failure for user feedback.
        const allSucceeded = response.results ? response.results.every(r => r.success) : response.success;
        if (allSucceeded) {
            stagedFiles = []; // Clear the internal array
            // Optionally clear the UI list after a short delay, or leave it showing success
            // setTimeout(renderFileList, 3000); // Example: clear list after 3s
        } else {
            // On partial failure, keep list but re-enable remove buttons for failed items? Or just leave as is.
            fileListContainer.querySelectorAll('.file-item').forEach(item => {
                const statusSpan = item.querySelector('.file-status');
                if (statusSpan && statusSpan.classList.contains('error')) {
                    const removeBtn = item.querySelector('.remove-button');
                    if (removeBtn) removeBtn.style.display = 'inline-block'; // Show remove for failed ones
                }
            });
        }
    }


    function updateFileStatusesGeneric(statusText, success) {
        fileListContainer.querySelectorAll('.file-status').forEach(span => {
            span.textContent = ` (${statusText})`;
            if (success) {
                span.classList.add('success');
                span.classList.remove('error');
            } else {
                span.classList.add('error');
                span.classList.remove('success');
            }
        });
    }

    function parseFlashedMessages(flashedMessages) {
        // Backend sends [(category, message), ...]
        return flashedMessages.map(msg => ({class: msg[0], message: msg[1]}));
    }

    function displayFlashMessages(messages) {
        const container = document.querySelector('.container'); // Find main container
        if (!container) return;

        // Remove existing flash messages first
        const existingFlashes = container.querySelector('.flash-messages');
        if (existingFlashes) {
            existingFlashes.remove();
        }

        if (messages && messages.length > 0) {
            const ul = document.createElement('ul');
            ul.className = 'flash-messages';
            messages.forEach(msg => {
                const li = document.createElement('li');
                li.className = msg.class; // 'success' or 'error'
                li.textContent = msg.message;
                ul.appendChild(li);
            });
            // Prepend to the main container
            container.prepend(ul);
        }
    }


    function resetUploadStateAfterCompletion() {
        // Re-enable submit button
        submitButton.disabled = false;
        submitButton.textContent = 'Upload Selected Files';

        // Hide progress/status unless explicitly leaving results visible
        // progressBar.style.display = 'none';
        // uploadingStatus.style.display = 'none';
        // writingStatus.style.display = 'none';

        // Maybe reset password field if it exists?
        // if (passwordField) passwordField.value = '';

        // Reset input element value to allow selecting the same file again
        if (fileElem) fileElem.value = '';
    }


    // --- Animation for "Writing..." ---
    function animateDots() {
        let dotCount = 0;
        clearInterval(dotInterval); // Clear any existing interval
        dotInterval = setInterval(() => {
            dotCount = (dotCount + 1) % 4;
            dots.textContent = '.'.repeat(dotCount);
        }, 400);
    }

    function stopAnimateDots() {
        clearInterval(dotInterval);
        dots.textContent = '...'; // Reset to static dots or empty
    }
} // End initializeUploadFeatures
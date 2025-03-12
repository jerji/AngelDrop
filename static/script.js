let dropArea = document.getElementById('drop-area');
let fileElem = document.getElementById('fileElem');
let progressBar = document.getElementById('progress-bar');
let fileList = document.getElementById('file-list');
let uploadForm = document.getElementById('upload-form');
let stagedFiles = []; // Array to store staged files

;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
  document.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults (e) {
  e.preventDefault();
  e.stopPropagation();
}

;['dragenter', 'dragover'].forEach(eventName => {
  document.addEventListener(eventName, highlight, false);
});

;['dragleave', 'drop'].forEach(eventName => {
  document.addEventListener(eventName, unhighlight, false);
});

function highlight(e) {
    if (dropArea)
        dropArea.classList.add('highlight');
}

function unhighlight(e) {
    if (dropArea)
        dropArea.classList.remove('highlight');
}

document.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
  let dt = e.dataTransfer;
  let files = dt.files;
  handleFiles(files);
}

function handleFiles(files) {
    // Add files to the stagedFiles array
    stagedFiles = stagedFiles.concat([...files]);

    // Display file names and "Ready for Upload" status
    renderFileList();
}

function renderFileList() {
    // Clear the existing file list
    fileList.innerHTML = "";

    stagedFiles.forEach((file, index) => { // Add index
        let fileItem = document.createElement('div');
        fileItem.classList.add('file-item'); // Add a class for styling

        let fileName = document.createElement('span');
        fileName.textContent = `${file.name} (Ready for Upload)`;
        fileItem.appendChild(fileName);

        let removeButton = document.createElement('span');
        removeButton.textContent = 'X';
        removeButton.classList.add('remove-button'); // Add a class for styling
        removeButton.addEventListener('click', () => removeFile(index)); // Pass index
        fileItem.appendChild(removeButton);

        fileList.appendChild(fileItem);
    });
     // Show the upload button if there are staged files, otherwise hide it
    document.getElementById("submit-button").style.display = stagedFiles.length > 0 ? "block" : "none";
}


function removeFile(index) {
    stagedFiles.splice(index, 1); // Remove the file at the given index
    renderFileList(); // Re-render the file list
}

// Prevent the default form submission behavior
uploadForm.addEventListener('submit', function(event) {
    event.preventDefault();  // Prevent the default form submission

    // Now handle the upload using FormData and XMLHttpRequest
    let formData = new FormData();
    stagedFiles.forEach(file => {
        formData.append('file', file);
    });

     // Append password if required
    if (document.getElementById('link_password')) {
        formData.append('link_password', document.getElementById('link_password').value);
    }

    let xhr = new XMLHttpRequest();
    xhr.open('POST', window.location.href, true);

    // Progress event listener
    xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
            let percentComplete = (e.loaded / e.total) * 100;
            progressBar.value = percentComplete;
        }
    });

    xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
            // Handle successful upload
            console.log('Success:', xhr.responseText);
            fileList.innerHTML = ""; // Clear file list
            stagedFiles = [];     // Clear staged files
            document.getElementById("submit-button").style.display = "none";
            progressBar.value = 0; // Reset progress bar

            //Find flashed message and display it.
            const parser = new DOMParser();
            const doc = parser.parseFromString(xhr.responseText, 'text/html');
            let flashMessage = doc.querySelector('.flash-messages');

            if (flashMessage) {
              document.querySelector('.container').prepend(flashMessage);
            } else {
                window.location.reload();
            }

        } else {
            // Handle upload error
            console.error('Error:', xhr.status, xhr.statusText);
             fileList.innerHTML = ""; // Clear file list
            stagedFiles = [];     // Clear staged files
            document.getElementById("submit-button").style.display = "none";  // Hide upload button
             progressBar.value = 0;
        }
    };

    xhr.onerror = function() {
        // Handle network errors
        console.error('Network Error');
        fileList.innerHTML = "";
        stagedFiles = [];
        document.getElementById("submit-button").style.display = "none";
         progressBar.value = 0;
    };

    xhr.send(formData);
});
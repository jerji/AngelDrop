let dropArea = document.getElementById('drop-area');
let fileElem = document.getElementById('fileElem');
let progressBar = document.getElementById('progress-bar');
let fileList = document.getElementById('file-list');
let uploadForm = document.getElementById('upload-form');
let stagedFiles = []; // Array to store staged files
let writingStatus = document.getElementById('writing-status'); // Get the writing status element
let dots = document.getElementById('dots'); // Get the dots element

;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    document.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
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
uploadForm.addEventListener('submit', function (event) {
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
    xhr.upload.addEventListener('progress', function (e) {
        if (e.lengthComputable) {
            progressBar.value = (e.loaded / e.total) * 100;
             // Change progress bar color when it reaches 100%
            if (progressBar.value === 100) {
                progressBar.classList.add('writing'); // Add the 'writing' class
                writingStatus.style.display = 'block'; // Show writing status
                animateDots(); // Start the animation
            }
        }
    });

    xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 300) {
            // Handle successful upload
            console.log('Success:', xhr.responseText);
            // Reset progress bar and writing status
            progressBar.value = 0;
            progressBar.classList.remove('writing'); //remove class
            writingStatus.style.display = 'none';
            stopAnimateDots(); // Stop the dots

            fileList.innerHTML = ""; // Clear file list
            stagedFiles = [];     // Clear staged files
            document.getElementById("submit-button").style.display = "none";


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
            // Reset progress bar and writing status
            progressBar.value = 0;
             progressBar.classList.remove('writing'); //remove class
            writingStatus.style.display = 'none';
            stopAnimateDots(); // Stop dots

            fileList.innerHTML = ""; // Clear file list
            stagedFiles = [];     // Clear staged files
            document.getElementById("submit-button").style.display = "none";  // Hide upload button
        }
    };

    xhr.onerror = function () {
        // Handle network errors
        console.error('Network Error');
        // Reset progress bar and writing status
        progressBar.value = 0;
        progressBar.classList.remove('writing');
        writingStatus.style.display = 'none';
        stopAnimateDots(); // Stop the dots
        fileList.innerHTML = "";
        stagedFiles = [];
        document.getElementById("submit-button").style.display = "none";
    };

    xhr.send(formData);
});

let dotInterval; // Variable to hold the interval ID

function animateDots() {
    let dotCount = 0;
    dotInterval = setInterval(() => {
        dotCount = (dotCount + 1) % 4; // Cycle through 0-3
        dots.textContent = '.'.repeat(dotCount);
    }, 500); // Change every 500ms
}

function stopAnimateDots() {
    clearInterval(dotInterval);
    dots.textContent = ''; // Clear dots
}
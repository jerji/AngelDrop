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
    [...files].forEach(file => {
        let fileItem = document.createElement('div');
        fileItem.textContent = `${file.name} (Ready for Upload)`;
        fileList.appendChild(fileItem);
    });

    // Show the upload button
    document.getElementById("submit-button").style.display = "block";
}

// Prevent the default form submission behavior
uploadForm.addEventListener('submit', function(event) {
    event.preventDefault();  // Prevent the default form submission

    // Now handle the upload using FormData and fetch
    let formData = new FormData();
    stagedFiles.forEach(file => {
        formData.append('file', file);
    });

     // Append password if required
    if (document.getElementById('link_password')) {
        formData.append('link_password', document.getElementById('link_password').value);
    }

    fetch(window.location.href, {
        method: 'POST',
        body: formData,
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.text(); // or response.json() if expecting JSON
    })
    .then(data => {
        // Handle successful upload (e.g., clear the list, display a message)
        console.log('Success:', data);
        fileList.innerHTML = ""; // Clear file list
        stagedFiles = [];     // Clear staged files
        document.getElementById("submit-button").style.display = "none";  // Hide upload button

        //Find flashed message and display it
        const parser = new DOMParser();
        const doc = parser.parseFromString(data, 'text/html');
        let flashMessage = doc.querySelector('.flash-messages');
        if (flashMessage) {
          // If the container exists, insert it into the current document.
          document.querySelector('.container').prepend(flashMessage);
        }
        else{
          // Refresh the page.
          window.location.reload();
        }
    })
    .catch((error) => {
        console.error('Error:', error);
         fileList.innerHTML = ""; // Clear file list
        stagedFiles = [];     // Clear staged files
        document.getElementById("submit-button").style.display = "none";  // Hide upload button

    });
});
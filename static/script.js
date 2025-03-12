// ... (previous JavaScript, drag-and-drop handling) ...
// No changes needed here for the combined form approach.
let dropArea = document.getElementById('drop-area');
let fileElem = document.getElementById('fileElem');
let progressBar = document.getElementById('progress-bar');
let fileList = document.getElementById('file-list');
let uploadForm = document.getElementById('upload-form');

// Listen for events on the whole document
;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
  document.addEventListener(eventName, preventDefaults, false); // Changed from dropArea
});

function preventDefaults (e) {
  e.preventDefault();
  e.stopPropagation();
}

;['dragenter', 'dragover'].forEach(eventName => {
  document.addEventListener(eventName, (e) => {
    highlight(e);
    e.preventDefault(); // Prevent default browser behavior
    e.stopPropagation(); // Stop event bubbling
  }, false);
});

;['dragleave', 'drop'].forEach(eventName => {
  document.addEventListener(eventName, (e) => {
    unhighlight(e);
    e.preventDefault();
    e.stopPropagation();
  }, false);
});

function highlight(e) {
    if (dropArea)
        dropArea.classList.add('highlight');
}

function unhighlight(e) {
    if (dropArea)
        dropArea.classList.remove('highlight');
}

document.addEventListener('drop', handleDrop, false); // Changed from dropArea

function handleDrop(e) {
  let dt = e.dataTransfer;
  let files = dt.files;

  handleFiles(files);
}
function handleFiles(files) {
  ([...files]).forEach(uploadFile);
    document.getElementById("submit-button").style.display = "block";

}

function uploadFile(file) {
    let url = window.location.href;
    let formData = new FormData(uploadForm);

    formData.append('file', file);

        // Display file name
    let fileItem = document.createElement('div');
    fileItem.textContent = file.name;
    fileList.appendChild(fileItem);


    fetch(url, {
      method: 'POST',
      body: formData,
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.text();
    })
    .then(() => {
        fileItem.textContent += " (Ready for Upload)";
    })
    .catch((error) => {
      console.error('Error:', error);
        fileItem.textContent += " (Upload Failed)";
    });
}
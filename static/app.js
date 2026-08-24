const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png"]);

const elements = {
  dropZone: document.querySelector("#dropZone"),
  fileInput: document.querySelector("#fileInput"),
  emptyState: document.querySelector("#emptyState"),
  previewState: document.querySelector("#previewState"),
  previewImage: document.querySelector("#previewImage"),
  fileName: document.querySelector("#fileName"),
  fileSize: document.querySelector("#fileSize"),
  removeFile: document.querySelector("#removeFile"),
  saveButton: document.querySelector("#saveButton"),
  checkButton: document.querySelector("#checkButton"),
  resultEmpty: document.querySelector("#resultEmpty"),
  loadingState: document.querySelector("#loadingState"),
  errorState: document.querySelector("#errorState"),
  successState: document.querySelector("#successState"),
  errorMessage: document.querySelector("#errorMessage"),
  tryAgainButton: document.querySelector("#tryAgainButton"),
  processAnotherButton: document.querySelector("#processAnotherButton"),
  statusBadge: document.querySelector("#statusBadge"),
  resultName: document.querySelector("#resultName"),
  resultDob: document.querySelector("#resultDob"),
  resultGender: document.querySelector("#resultGender"),
  resultAadhaar: document.querySelector("#resultAadhaar"),
};

let selectedFile = null;
let previewUrl = null;

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function showResult(name) {
  for (const state of ["resultEmpty", "loadingState", "errorState", "successState"]) {
    elements[state].hidden = state !== name;
  }
}

function setBusy(isBusy) {
  elements.saveButton.disabled = isBusy || !selectedFile;
  elements.checkButton.disabled = isBusy || !selectedFile;
  elements.fileInput.disabled = isBusy;
}

function clearFile() {
  selectedFile = null;
  elements.fileInput.value = "";
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null;
  elements.previewImage.removeAttribute("src");
  elements.previewState.hidden = true;
  elements.emptyState.hidden = false;
  setBusy(false);
  showResult("resultEmpty");
}

function showError(message) {
  elements.errorMessage.textContent = message;
  showResult("errorState");
}

function chooseFile(file) {
  if (!file) return;
  if (!ALLOWED_TYPES.has(file.type)) {
    showError("Choose a JPEG or PNG image.");
    return;
  }
  if (file.size > MAX_BYTES) {
    showError("The selected image is larger than 5 MB.");
    return;
  }

  selectedFile = file;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  elements.previewImage.src = previewUrl;
  elements.fileName.textContent = file.name;
  elements.fileSize.textContent = formatBytes(file.size);
  elements.emptyState.hidden = true;
  elements.previewState.hidden = false;
  setBusy(false);
  showResult("resultEmpty");
}

function readableStatus(status) {
  return {
    created: "Record created",
    existing: "Record found",
    new: "New record",
  }[status] || status;
}

async function processDocument(endpoint) {
  if (!selectedFile) return;
  setBusy(true);
  showResult("loadingState");

  const form = new FormData();
  form.append("file", selectedFile);

  try {
    const response = await fetch(endpoint, { method: "POST", body: form });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "The server could not process this image.");
    }

    const data = payload.data;
    elements.statusBadge.textContent = readableStatus(payload.status);
    elements.resultName.textContent = data.name || "Not detected";
    elements.resultDob.textContent = data.dob || "Not detected";
    elements.resultGender.textContent = data.gender || "Not detected";
    elements.resultAadhaar.textContent = data.aadhaar_masked || "Not detected";
    showResult("successState");
  } catch (error) {
    showError(error.message || "Something went wrong while processing the document.");
  } finally {
    setBusy(false);
  }
}

elements.dropZone.addEventListener("click", () => elements.fileInput.click());
elements.dropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    elements.fileInput.click();
  }
});
elements.fileInput.addEventListener("change", (event) => chooseFile(event.target.files[0]));

for (const eventName of ["dragenter", "dragover"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.add("dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("dragging");
  });
}
elements.dropZone.addEventListener("drop", (event) => chooseFile(event.dataTransfer.files[0]));

elements.removeFile.addEventListener("click", (event) => {
  event.stopPropagation();
  clearFile();
});
elements.saveButton.addEventListener("click", () => processDocument("/upload"));
elements.checkButton.addEventListener("click", () => processDocument("/recognise"));
elements.tryAgainButton.addEventListener("click", clearFile);
elements.processAnotherButton.addEventListener("click", clearFile);


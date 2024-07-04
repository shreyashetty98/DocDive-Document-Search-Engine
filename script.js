
function openNav() {
    document.getElementById("mySidebar").style.width = "250px";
    document.getElementById("main").style.marginLeft = "250px";
}
          
function closeNav() {
    document.getElementById("mySidebar").style.width = "0";
    document.getElementById("main").style.marginLeft= "0";
}
const input = document.querySelector(".finder__input");
const finder = document.querySelector(".finder");
const form = document.querySelector("form");

input.addEventListener("focus", () => {
  finder.classList.add("active");
});

input.addEventListener("blur", () => {
  if (input.value.length === 0) {
    finder.classList.remove("active");
  }
});

form.addEventListener("submit", (ev) => {
  ev.preventDefault();
  finder.classList.add("processing");
  finder.classList.remove("active");
  input.disabled = true;
  setTimeout(() => {
    finder.classList.remove("processing");
    input.disabled = false;
    if (input.value.length > 0) {
      finder.classList.add("active");
    }
  }, 1000);
});
// Function to open the input modal with a specific input type
function openInputModal(inputType) {
    var inputField = document.getElementById("inputField");
    inputField.innerHTML = ''; // Clear previous input field
  
    // Create input field based on the type
    if (inputType === 'pdf') {
      inputField.innerHTML = '<label class="upload-label" for="pdfInput">Upload PDF:</label><input type="file" id="pdfInput" name="pdfInput" accept="application/pdf" multiple><br><br>';
    } else if (inputType === 'text') {
      inputField.innerHTML = '<label class="upload-label" for="textInput">Enter Text File:</label><input type="file" id="textInput" name="textInput" accept="text/plain" multiple><br><br>';
    } else if (inputType === 'image') {
      inputField.innerHTML = '<label class="upload-label" for="imageInput">Upload Image:</label><input type="file" id="imageInput" name="imageInput" accept="image/*" multiple><br><br>';
    } else if (inputType === 'url') {
      inputField.innerHTML = '<label class="upload-label" for="urlInput">Enter URL:</label><input type="url" id="urlInput" name="urlInput"><br><br>';
    }
  
    // Display the modal
    document.getElementById("inputModal").style.display = "block";
  }
  
  // Function to close the input modal
  function closeInputModal() {
    document.getElementById("inputModal").style.display = "none";
  }
  
  // Function to handle the input form submission
  function submitInputForm() {
    // Implement the logic to handle the form submission
    console.log('Input form submitted');
    closeInputModal(); // Close the modal after submission
  }
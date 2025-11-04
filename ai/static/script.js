// Preview uploaded image
const imageUpload = document.getElementById('imageUpload');
const imagePreview = document.getElementById('imagePreview');

imageUpload.addEventListener('change', () => {
  const file = imageUpload.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = () => {
      imagePreview.src = reader.result;
      imagePreview.style.display = 'block';
    };
    reader.readAsDataURL(file);
  }
});

function analyzeSkin() {
  const skinType = document.getElementById('q1').value;
  const acneSeverity = document.getElementById('q4').value;

  const result = `
    <p><strong>Predicted Skin Type:</strong> ${skinType || 'Not answered'}</p>
    <p><strong>Acne Frequency:</strong> ${acneSeverity || 'Not answered'}</p>
  `;

  document.getElementById('result').innerHTML = result;
}

// Fetch episodes from the backend
async function fetchEpisodes() {
    const currentPath = window.location.pathname;
    const seasonNumber = currentPath.split('/').filter(Boolean).pop();
  
    console.log("Current Path:", currentPath);
    console.log("Extracted Season Number:", seasonNumber);
  
    try {
      const response = await fetch(`/api/season/${seasonNumber}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      });
  
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
  
      const data = await response.json();
      console.log("Fetched Episodes Data:", data);
  
      const episodeGrid = document.querySelector('.episode-grid');
      if (!episodeGrid) {
        console.error("Error: .episode-grid element not found.");
        return;
      }
  
      episodeGrid.innerHTML = ''; // Clear existing buttons
  
      if (!Array.isArray(data)) {
        console.error("Error: Data is not an array", data);
        return;
      }
  
      data.forEach((episode) => {
        const button = document.createElement('button');
        button.textContent = episode.title;
        button.addEventListener('click', () => {
          const videoPlayer = document.getElementById('videoPlayer');
          if (!videoPlayer) {
            console.error("Error: #videoPlayer element not found.");
            return;
          }
          videoPlayer.src = episode.video_url; // Update iframe source
          console.log("Playing Episode:", episode);
        });
        episodeGrid.appendChild(button);
      });
    } catch (error) {
      console.error("Error fetching episodes:", error);
    }
  }
  
  // Theme toggle
  document.addEventListener("DOMContentLoaded", () => {
    const themeToggle = document.getElementById('themeToggle');
    if (!themeToggle) {
      console.error("Error: #themeToggle element not found.");
      return;
    }
  
    themeToggle.addEventListener('click', () => {
      document.body.classList.toggle('dark-mode');
      themeToggle.textContent = document.body.classList.contains('dark-mode')
        ? 'Light Mode'
        : 'Dark Mode';

        if (themeToggle.textContent === 'Dark Mode') {
            themeToggle.style.backgroundColor = 'black';
            themeToggle.style.color = 'white';
            themeToggle.style.boxShadow = '0 4px 15px white;'
        } else if (themeToggle.textContent === 'Light Mode') {
            themeToggle.style.backgroundColor = 'white';
            themeToggle.style.color = 'black';
            themeToggle.style.boxShadow = '0 4px 15px black'
        }
    });
  });
  
  // Fetch episodes on page load
  document.addEventListener("DOMContentLoaded", fetchEpisodes);
  
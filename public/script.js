const metadataCache = new Map();
const menuOpen = document.getElementById('menu-open');
const menuClose = document.getElementById('menu-close');
const sidebar = document.querySelector('.container .sidebar');
const dynamicContent = document.getElementById('dynamic-content');
const initialContent = dynamicContent.innerHTML;
let currentPlaylist = [];
let generatedPlaylist = [];
let currentSongIndex = -1;

// Audio elements
const song = document.getElementById("song");
const progress = document.getElementById("progress");
const ctrlIcon = document.getElementById("ctrlIcon");
const currentTimeDisplay = document.getElementById("current-time");
const durationDisplay = document.getElementById("duration");
const playerTitle = document.querySelector('.music-player .description h3');
const playerArtist = document.querySelector('.music-player .description h5');
const playerImage = document.querySelector('.music-player .song-info img');

// Rating System
const ratingForm = document.getElementById('ratingForm');
const arousalSlider = document.getElementById('arousal');
const valenceSlider = document.getElementById('valence');
const overallSlider = document.getElementById('overall');
const arousalValue = document.getElementById('arousalValue');
const valenceValue = document.getElementById('valenceValue');
const overallValue = document.getElementById('overallValue');

const prevBtn = document.querySelector('.bx-skip-previous');
const nextBtn = document.querySelector('.bx-skip-next');

const favouriteSection = document.querySelector('a[data-section="favourites"]');

// Update display values in real-time
arousalSlider.addEventListener('input', (e) => {
    arousalValue.textContent = e.target.value;
});

valenceSlider.addEventListener('input', (e) => {
    valenceValue.textContent = e.target.value;
});

overallSlider.addEventListener('input', (e) => {
    overallValue.textContent = e.target.value;
});

// Handle form submission
ratingForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const currentSong = song.src;
    if (!currentSong) {
        alert('No song playing');
        return;
    }
    
    try {
        // Extract song ID more reliably
        const url = new URL(currentSong);
        const songId = url.pathname.split('/').pop().split('.')[0];
        
        const ratings = {
            arousal: parseInt(arousalSlider.value),
            valence: parseInt(valenceSlider.value),
            overall: parseInt(overallSlider.value),
            song_id: songId
        };

        console.log('Submitting ratings:', ratings); // Add logging
        
        const response = await fetch('/api/rate-song', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(ratings)
        });

        const result = await response.json();
        if (!response.ok) {
            console.error('Rating error:', result.error);
            alert(`Rating failed: ${result.error || 'Unknown error'}`);
            return;
        }

        alert('Rating submitted successfully!');
        // Reset sliders
        arousalSlider.value = 5;
        valenceSlider.value = 5;
        overallSlider.value = 3;
        arousalValue.textContent = '5';
        valenceValue.textContent = '5';
        overallValue.textContent = '3';
        
    } catch (error) {
        console.error('Rating error:', error);
        alert('Failed to submit rating. Please check console for details.');
    }
});

// Player controls
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function updatePlayerUI(songData) {
    // Always use the cover from songData, fallback to default
    const coverPath = songData.cover || '/assets/song-1.png';
    
    // Update player image
    playerImage.src = coverPath;
    playerImage.onerror = () => {
        playerImage.src = '/assets/song-1.png';
    };
    
    // Update list view images
    document.querySelectorAll(`.cover-image[data-s3-key="${songData.s3_key}"]`)
        .forEach(img => {
            img.src = coverPath;
            img.onerror = () => img.src = '/assets/song-1.png';
        });

    playerTitle.textContent = songData.title;
    playerArtist.textContent = songData.artist;
}

async function playSelectedSong(index) {
    const selectedSong = currentPlaylist[index];
    if (!selectedSong) return;

    currentSongIndex = index;

    try {
        // Show loading state
        updatePlayerUI({
            ...selectedSong,
            artist: 'Loading...',
            cover: '/assets/loading.gif'
        });

        // Fetch metadata if not cached
        if (!metadataCache.has(selectedSong.s3_key)) {
            const response = await fetch('/api/song-details', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ s3_key: selectedSong.s3_key })
            });
            
            if (!response.ok) throw new Error('Metadata load failed');
            const metadata = await response.json();
            
            // Update song data and cache
            Object.assign(selectedSong, metadata);
            metadataCache.set(selectedSong.s3_key, metadata);
        }

        // Update UI with cached data
        updatePlayerUI(selectedSong);
        
        // Handle audio playback
        song.src = selectedSong.file;
        await song.play();
        ctrlIcon.classList.replace('bxs-right-arrow', 'bx-pause');

    } catch (error) {
        console.error('Playback error:', error);
        updatePlayerUI({
            ...selectedSong,
            artist: 'Error loading song',
            cover: '/assets/error.png'
        });
    }
}

// Previous button click handler
prevBtn.addEventListener('click', () => {
    if (currentPlaylist.length === 0) return;
    if (currentSongIndex === -1) {
        currentSongIndex = currentPlaylist.length - 1;
    } else {
        currentSongIndex = (currentSongIndex - 1 + currentPlaylist.length) % currentPlaylist.length;
    }
    playSelectedSong(currentSongIndex);
});

// Next button click handler
nextBtn.addEventListener('click', () => {
    if (currentPlaylist.length === 0) return;
    if (currentSongIndex === -1) {
        currentSongIndex = 0;
    } else {
        currentSongIndex = (currentSongIndex + 1) % currentPlaylist.length;
    }
    playSelectedSong(currentSongIndex);
});

async function fetchMetadata(s3Key) {
    const response = await fetch('/api/song-details', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ s3_key: s3Key })
    });
    if (!response.ok) throw new Error('Metadata load failed');
    return response.json();
}

song.onerror = function() {
    console.error('Audio playback error:', song.error);
    updatePlayerUI({
        title: playerTitle.textContent,
        artist: 'Playback failed',
        cover: '/assets/error.png'
    });
};

// Event listeners
dynamicContent.addEventListener('click', (e) => {
    const songItem = e.target.closest('.item');
    if (songItem) {
        const index = songItem.dataset.index;
        const s3Key = songItem.dataset.s3Key;
        playSelectedSong(index, s3Key);  // Modified function signature
    }
});

song.onloadedmetadata = function() {
    progress.max = song.duration;
    durationDisplay.textContent = formatTime(song.duration);
}

progress.oninput = function() {
    song.currentTime = progress.value;
}

song.ontimeupdate = function() {
    progress.value = song.currentTime;
    currentTimeDisplay.textContent = formatTime(song.currentTime);
}

// When the current song ends, automatically play the next one
song.addEventListener('ended', function() {
    // Make sure the playlist is not empty
    if (currentPlaylist.length === 0) return;

    // Update currentSongIndex by incrementing it.
    // The modulo operator wraps it back to 0 when it reaches the end.
    currentSongIndex = (currentSongIndex + 1) % currentPlaylist.length;

    // Play the next song in the playlist
    playSelectedSong(currentSongIndex);
});

document.querySelector('.play-button').addEventListener('click', function() {
    if(song.paused) {
        song.play();
        ctrlIcon.classList.replace('bxs-right-arrow', 'bx-pause');
    } else {
        song.pause();
        ctrlIcon.classList.replace('bx-pause', 'bxs-right-arrow');
    }
});

// Menu functionality
menuOpen.addEventListener('click', () => sidebar.style.left = '0');
menuClose.addEventListener('click', () => sidebar.style.left = '-100%');

// Music list generation
function generateMusicList(songs, section) {
    return `
    <div class="music-list">
        <div class="header">
            <h5>${section === 'generated' ? 'Generated Music' : 'Local Music'}</h5>
        </div>
        <div class="items">
            ${songs.map((song, index) => `
            <div class="item" data-index="${index}">
                <div class="info">
                    <p>${(index + 1).toString().padStart(2, '0')}</p>
                    <img src="${song.cover || '/assets/song-1.png'}" 
                         class="cover-image" 
                         data-s3-key="${song.s3_key}">
                    <div class="details">
                        <h5>${song.title}</h5>
                        <p>${song.artist || 'Unknown Artist'}</p>
                    </div>
                </div>
                <div class="actions">
                    <p>${song.duration || '--:--'}</p>
                    <i class='bx bxs-right-arrow'></i>
                    <i class='bx ${song.liked ? 'bxs-heart' : 'bx-heart'} like-btn' data-s3-key="${song.s3_key}"></i>
                </div>
            </div>
            `).join('')}
        </div>
    </div>`;
}

// Favourite Section Starts

// Add event listeners for like buttons
function handleLikeButtonClick(e) {
    const likeBtn = e.target.closest('.like-btn');
    if (!likeBtn) return;

    const s3Key = likeBtn.dataset.s3Key;
    toggleFavourite(s3Key, likeBtn);
}
dynamicContent.addEventListener('click', handleLikeButtonClick);

// Favourites functionality
async function toggleFavourite(s3Key, element) {
    try {
        const response = await fetch('/api/toggle-favorite', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                s3_key: s3Key,
                user_id: 'user123' // Replace with actual user ID
            })
        });

        const result = await response.json();
        if (result.liked) {
            element.classList.replace('bx-heart', 'bxs-heart');
        } else {
            element.classList.replace('bxs-heart', 'bx-heart');
        }
        
        // Refresh favourites if section is active
        if (document.querySelector('.sidebar a.active')?.dataset.section === 'favourites') {
            loadFavourites();
        }
    } catch (error) {
        console.error('Like error:', error);
    }
}

async function loadFavourites() {
    try {
        const response = await fetch('/api/favourites?user_id=user123');
        const favourites = await response.json();
        currentPlaylist = favourites;
        dynamicContent.innerHTML = generateMusicList(favourites, 'favourites');
    } catch (error) {
        console.error('Favourites load error:', error);
        dynamicContent.innerHTML = `<div class="error">Failed to load favourites</div>`;
    }
}

// Favourites Section Ends

document.querySelectorAll('.sidebar a[data-section]').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        document.querySelectorAll('.sidebar a').forEach(a => a.classList.remove('active'));
        this.classList.add('active');
        const section = this.dataset.section;
        
        switch(section) {
            case 'explore':
                content = initialContent;
                break;
            case 'genres':
                content = `<div class="section"><h2>Genres</h2><p>Browse music by genre</p></div>`;
                break;
            case 'albums':
                content = `<div class="section"><h2>Albums</h2><p>All available albums</p></div>`;
                break;
                case 'local':
                    dynamicContent.innerHTML = '<p>Loading local music...</p>';
                    fetch('/api/local-music')
                        .then(response => {
                            if (!response.ok) throw new Error('Network response was not ok');
                            return response.json();
                        })
                        .then(songs => {
                            currentPlaylist = songs; // Store songs in playlist
                            dynamicContent.innerHTML = generateMusicList(songs, 'local');
                        })
                        .catch(error => {
                            console.error('Error loading local music:', error);
                            dynamicContent.innerHTML = `
                                <div class="error">
                                    <p>Failed to load local music</p>
                                    <button onclick="location.reload()">Retry</button>
                                </div>
                            `;
                        });
                    break;
            case 'generated':
                dynamicContent.innerHTML = '<p>Loading generated music...</p>';
                fetch('/api/generated-music')
                    .then(response => response.json())
                    .then(songs => {
                        generatedPlaylist = songs;
                        currentPlaylist = songs;
                        dynamicContent.innerHTML = generateMusicList(songs);
                    })
                    .catch(error => {
                        console.error('Error loading generated music:', error);
                        dynamicContent.innerHTML = `
                            <div class="error">
                                <p>Failed to load generated music</p>
                                <button onclick="location.reload()">Retry</button>
                            </div>
                        `;
                    });
                return;
            case 'favourites':
                dynamicContent.innerHTML = '<p>Loading favourites...</p>';
                loadFavourites();
                break;
            case 'recent':
                content = `<div class="section"><h2>Recent</h2><p>Recently played tracks</p></div>`;
                break;
            // Add more cases for other sections as needed
            default:
                content = initialContent;
        }
        
        dynamicContent.innerHTML = content;
    });
});

// Add Generate Now button handler
document.getElementById('generate-now').addEventListener('click', () => {
    const generateBtn = document.getElementById('generate-now');
    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating...';

    fetch('/api/generate-music', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            prompt: 'upbeat electronic music with a melodic synth line'
        })
    })
    .then(response => response.json())
    .then(data => {
        if(data.url) {
            // Refresh generated playlist
            return fetch('/api/generated-music');
        }
        throw new Error('Generation failed');
    })
    .then(response => response.json())
    .then(songs => {
        generatedPlaylist = songs;
        currentPlaylist = songs;
        
        // Find and play the latest generated song (assuming it's last in the array)
        const newSongIndex = generatedPlaylist.length - 1;
        if(newSongIndex >= 0) {
            playSelectedSong(newSongIndex);
        }
        
        // Update Generated section if active
        const activeSection = document.querySelector('.sidebar a.active');
        if(activeSection && activeSection.dataset.section === 'generated') {
            dynamicContent.innerHTML = generateMusicList(generatedPlaylist);
        }
    })
    .catch(error => {
        console.error('Generation error:', error);
        alert('Failed to generate music');
    })
    .finally(() => {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Now';
    });
});

// Animated counter
function animateCounters() {
    const counters = document.querySelectorAll('.counter');
    counters.forEach(counter => {
        const target = +counter.dataset.target;
        const duration = 2000;
        const step = target / (duration / 10);
        
        let current = 0;
        const updateCounter = () => {
            current += step;
            if(current < target) {
                counter.textContent = Math.ceil(current);
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = target;
            }
        }
        updateCounter();
    });
}

// Trigger when section is in view
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if(entry.isIntersecting) {
            animateCounters();
        }
    });
});

document.querySelectorAll('.platform-brief').forEach(el => {
    observer.observe(el);
});

// Navigation controls
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        const section = this.dataset.section;
        document.querySelector(`[data-section="${section}"]`).click();
    });
});

// Simulate battery status
function updateBattery() {
    navigator.getBattery().then(battery => {
        const level = Math.floor(battery.level * 100);
        document.getElementById('battery-level').textContent = `${level}%`;
        
        const batteryIcon = document.querySelector('.bx-battery');
        if (level <= 20) batteryIcon.className = 'bx bx-battery-low';
        else if (level <= 50) batteryIcon.className = 'bx bx-battery';
        else batteryIcon.className = 'bx bx-battery-full';
    });
}

// Update battery status every minute
updateBattery();
setInterval(updateBattery, 60000);

// Settings button
document.getElementById('app-settings').addEventListener('click', () => {
    // Add your settings modal logic here
    alert('Settings panel coming soon!');
});

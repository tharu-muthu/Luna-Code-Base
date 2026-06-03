// ============================================================
//  Luna OS – script.js
// ============================================================

lucide.createIcons();

/* ---- Tab Switching ---- */
document.querySelectorAll('.nav-btn').forEach(button => {
    button.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-section').forEach(s => {
            s.classList.add('hidden');
            s.classList.remove('active');
        });
        button.classList.add('active');
        const targetSection = document.getElementById(button.getAttribute('data-target'));
        targetSection.classList.remove('hidden');
        void targetSection.offsetWidth;
        targetSection.classList.add('active');

        // Show/hide playback bar only on media/education pages
        const mediaPages = ['media', 'education'];
        const bar = document.getElementById('playback-bar');
        if (mediaPages.includes(button.getAttribute('data-target'))) {
            showPlaybackBar();
        } else {
            bar.classList.add('hidden');
            bar.classList.remove('show');
        }
    });
});

/* ============================================================
   Playback Bar State
   ============================================================ */
let currentContext = null;   // 'story' | 'music' | 'education'
let currentTrack   = '';     // human-readable name e.g. "Story 3"
let isPaused       = false;

function showPlaybackBar() {
    const bar = document.getElementById('playback-bar');
    if (bar.classList.contains('hidden')) {
        bar.classList.remove('hidden');
        // Re-trigger animation
        bar.classList.remove('show');
        void bar.offsetWidth;
        bar.classList.add('show');
        lucide.createIcons(); // re-render icons inside bar
    }
}

function hidePlaybackBar() {
    const bar = document.getElementById('playback-bar');
    bar.classList.add('hidden');
    bar.classList.remove('show');
    // Also trigger stop on backend when closed
    stopCurrent();
}

function setPlayPauseUI(paused) {
    isPaused = paused;
    const btn = document.getElementById('play-pause-btn');
    const icon = document.getElementById('play-pause-icon');
    
    if (paused) {
        btn.title = "Resume";
        icon.outerHTML = `<i id="play-pause-icon" data-lucide="play" class="w-5 h-5 fill-current"></i>`;
    } else {
        btn.title = "Pause";
        icon.outerHTML = `<i id="play-pause-icon" data-lucide="pause" class="w-5 h-5 fill-current"></i>`;
    }
    lucide.createIcons();
}

function updatePlaybackBar(trackName, context) {
    currentContext = context;
    currentTrack   = trackName;
    document.getElementById('playback-title').textContent = trackName;

    // Swap icon based on context
    const iconEl = document.getElementById('playback-icon');
    const iconMap = {
        story:     'book-open',
        music:     'music-2',
        education: 'graduation-cap'
    };
    iconEl.innerHTML = `<i data-lucide="${iconMap[context] || 'music-2'}" class="w-5 h-5 text-cyan-400"></i>`;
    
    // Reset play/pause state to playing when new track starts
    setPlayPauseUI(false);

    showPlaybackBar();
}

/* Pause / Resume toggle */
function togglePlayPause() {
    if (!currentContext) return;
    const endpoint = isPaused ? '/resume' : '/pause';
    fetch(endpoint, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data && data.status) {
                setPlayPauseUI(data.status === 'paused');
                if (isPaused) {
                    document.getElementById('playback-title').textContent = currentTrack + ' (Paused)';
                } else {
                    document.getElementById('playback-title').textContent = currentTrack;
                }
            }
        })
        .catch(err => console.error("Toggle play/pause error:", err));
}

/* Stop current */
function stopCurrent() {
    if (!currentContext) return;
    const endpoints = {
        story:     '/story/stop',
        music:     '/music/stop',
        education: '/education/stop'
    };
    fetch(endpoints[currentContext], { method: 'POST' });
    document.getElementById('playback-title').textContent = 'Stopped';
}

/* Unified next */
function nextCurrent() {
    if (!currentContext) return;
    const endpoints = {
        story:     '/story/next',
        music:     '/music/next',
        education: '/education/next'
    };
    fetch(endpoints[currentContext], { method: 'POST' });
    
    // Optimistic UI Update: Predict next track name and update UI instantly
    if (currentContext === 'story' || currentContext === 'music') {
        const match = currentTrack.match(/\d+/);
        if (match) {
            let nextNum = parseInt(match[0]) + 1;
            if (nextNum <= 10) {
                const label = currentContext === 'story' ? 'Story ' : 'Music ';
                updatePlaybackBar(label + nextNum, currentContext);
            }
        }
    } else {
        setPlayPauseUI(false);
    }
    
    // Defer sync to let the robot load the next track
    setTimeout(syncStatus, 2600);
}

/* Unified previous */
function prevCurrent() {
    if (!currentContext) return;
    const endpoints = {
        story:     '/story/prev',
        music:     '/music/prev',
        education: '/education/prev'
    };
    fetch(endpoints[currentContext], { method: 'POST' });
    
    // Optimistic UI Update: Predict previous track name and update UI instantly
    if (currentContext === 'story' || currentContext === 'music') {
        const match = currentTrack.match(/\d+/);
        if (match) {
            let prevNum = parseInt(match[0]) - 1;
            if (prevNum >= 1) {
                const label = currentContext === 'story' ? 'Story ' : 'Music ';
                updatePlaybackBar(label + prevNum, currentContext);
            }
        }
    } else {
        setPlayPauseUI(false);
    }
    
    // Defer sync to let the robot load the previous track
    setTimeout(syncStatus, 2600);
}

/* ============================================================
   Movement
   ============================================================ */
function sendMove(dir) {
    fetch('/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'direction=' + encodeURIComponent(dir)
    });
}

/* ============================================================
   Volume Control & Reactive UI
   ============================================================ */
function updateVolumeUI(volumePercent) {
    const bar = document.getElementById('volume-indicator-bar');
    const text = document.getElementById('volume-text');
    if (bar) bar.style.width = volumePercent + '%';
    if (text) text.textContent = volumePercent + '%';
}

function fetchVolume() {
    fetch('/volume')
        .then(res => {
            if (!res.ok) throw new Error("Status " + res.status);
            return res.json();
        })
        .then(data => {
            if (data && typeof data.volume !== 'undefined') {
                updateVolumeUI(data.volume);
            }
        })
        .catch(err => {
            console.warn("Could not fetch volume (likely running older backend):", err);
            // Default visual fallback
            updateVolumeUI(50);
        });
}

function volumeUp() {
    fetch('/volume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'intensity=increase'
    })
    .then(res => {
        if (res.status === 204 || !res.ok) return null; // Safe fallback for older backend
        return res.json();
    })
    .then(data => {
        if (data && typeof data.volume !== 'undefined') {
            updateVolumeUI(data.volume);
        } else {
            // Local fallback if backend didn't return new volume (old backend compatibility)
            const text = document.getElementById('volume-text');
            if (text) {
                let current = parseInt(text.textContent) || 50;
                updateVolumeUI(Math.min(100, current + 10));
            }
        }
    })
    .catch(err => console.error("volumeUp error:", err));
}

function volumeDown() {
    fetch('/volume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'intensity=decrease'
    })
    .then(res => {
        if (res.status === 204 || !res.ok) return null; // Safe fallback for older backend
        return res.json();
    })
    .then(data => {
        if (data && typeof data.volume !== 'undefined') {
            updateVolumeUI(data.volume);
        } else {
            // Local fallback if backend didn't return new volume (old backend compatibility)
            const text = document.getElementById('volume-text');
            if (text) {
                let current = parseInt(text.textContent) || 50;
                updateVolumeUI(Math.max(0, current - 10));
            }
        }
    })
    .catch(err => console.error("volumeDown error:", err));
}

/* ============================================================
   Status Synchronization
   ============================================================ */
function syncStatus() {
    fetch('/status')
        .then(res => {
            if (!res.ok) throw new Error("Status " + res.status);
            return res.json();
        })
        .then(data => {
            if (data) {
                // If stopped, update title
                if (!data.playing && !data.paused) {
                    document.getElementById('playback-title').textContent = data.track || 'Stopped';
                    setPlayPauseUI(false);
                    return;
                }
                
                // Update state
                currentContext = data.category;
                currentTrack = data.track;
                
                if (data.paused) {
                    document.getElementById('playback-title').textContent = currentTrack + ' (Paused)';
                } else {
                    document.getElementById('playback-title').textContent = currentTrack;
                }
                
                setPlayPauseUI(data.paused);
                updateVolumeUI(data.volume);
                
                // Sync display icon
                const iconEl = document.getElementById('playback-icon');
                const iconMap = {
                    story:     'book-open',
                    music:     'music-2',
                    education: 'graduation-cap'
                };
                iconEl.innerHTML = `<i data-lucide="${iconMap[data.category] || 'music-2'}" class="w-5 h-5 text-cyan-400"></i>`;
                lucide.createIcons();
            }
        })
        .catch(err => console.warn("Could not sync status:", err));
}

// Fetch initial volume level and sync status when the page loads
document.addEventListener('DOMContentLoaded', () => {
    fetchVolume();
    syncStatus();
    
    // Poll status every 3 seconds to keep UI perfectly in sync
    setInterval(() => {
        const bar = document.getElementById('playback-bar');
        if (bar && !bar.classList.contains('hidden')) {
            syncStatus();
        }
    }, 3000);
});

/* ============================================================
   Stories
   ============================================================ */
function playStory(name) {
    fetch('/play', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'story=' + encodeURIComponent(name)
    });
    // Convert 'story3' → 'Story 3'
    const num = name.replace('story', '');
    updatePlaybackBar('Story ' + num, 'story');
}

/* ============================================================
   Music
   ============================================================ */
function playMusic(name) {
    fetch('/music', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'music=' + encodeURIComponent(name)
    });
    const num = name.replace('music', '');
    updatePlaybackBar('Music ' + num, 'music');
}

/* ============================================================
   Education
   ============================================================ */
function playEducation(type) {
    fetch('/education/play', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'type=' + encodeURIComponent(type)
    });
    const label = type.charAt(0).toUpperCase() + type.slice(1);
    updatePlaybackBar(label, 'education');
}

/* ============================================================
   Camera
   ============================================================ */
function startFeed() {
    fetch('/start', { method: 'POST' }).then(() => {
        document.getElementById('stream').src = '/video_feed?ts=' + Date.now();
    });
}
function stopFeed() {
    fetch('/stop', { method: 'POST' }).then(() => {
        document.getElementById('stream').src = '';
    });
}
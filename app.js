'use strict';

const CATEGORIES = [
  {
    label: 'Führerschein',
    clips: [
      { text: 'Mein Führerschein ist wie Gott: Viele glauben daran, gesehen hat ihn noch keiner.', file: 'audio/clip_09.mp3' },
      { text: 'Andere sammeln Kilometer, ich sammle Mitfahrten.',                                   file: 'audio/clip_10.mp3' },
      { text: 'Ich erkenne ein gutes Auto daran, wie bequem der Beifahrersitz ist.',                file: 'audio/clip_04.mp3' },
      { text: 'Mein Lieblingsauto ist das, in dem mich andere mitnehmen.',                         file: 'audio/clip_05.mp3' },
      { text: 'Ich bin der Beweis dafür, dass man auch ohne Führerschein im Leben völlig in die falsche Richtung fahren kann.', file: 'audio/clip_11.mp3' },
    ]
  },
  {
    label: 'Pascal',
    clips: [
      { text: 'Pascal, dafür dass du mich ständig fährst, zahle ich heute für dich und ich liebe dich.', file: 'audio/clip_12.mp3' },
      { text: 'Der Herr ist mein Hirte und mein Fahrer ist heute Pascal.',                               file: 'audio/clip_03.mp3' },
    ]
  },
  {
    label: 'Alkohol',
    clips: [
      { text: 'Wenn der Pegel steigt, sinkt das Niveau.',                     file: 'audio/clip_13.mp3' },
      { text: 'Der Geist ist willig, aber das Bier ist kalt.',                 file: 'audio/clip_14.mp3' },
      { text: 'Nich lang schnacken, Kopf in Nacken',                          file: 'audio/clip_15.mp3' },
      { text: 'Delirium, Delarium - Voll wie ein Aquarium',                   file: 'audio/clip_16.mp3' },
      { text: 'Ich fühle mich wie 2012 im Bierkönig.',                        file: 'audio/clip_07.mp3' },
      { text: 'Alkoholische Mitarbeit ist heute ausdrücklich erwünscht.',      file: 'audio/clip_06.mp3' },
      { text: 'Mein Verantwortungsbereich endet ab dem zweiten Bier.',        file: 'audio/clip_08.mp3' },
      { text: 'Heute geht die erste Runde Bier selbstverständlich auf mich.', file: 'audio/clip_02.mp3' },
    ]
  },
  {
    label: 'Anderes',
    clips: [
      { text: 'Wer auf Toilette möchte, hebt bitte die Hand.', file: 'audio/clip_01.mp3' },
    ]
  },
];

const audioCache = {};
let activeAudio  = null;
let activeBtn    = null;

const clipsGrid = document.getElementById('clipsGrid');
const toast     = document.getElementById('toast');
const lightbox  = document.getElementById('lightbox');
const avatarImg = document.getElementById('avatarImg');

avatarImg.addEventListener('click', () => lightbox.classList.add('open'));
lightbox.addEventListener('click',  () => lightbox.classList.remove('open'));

// ── Easter Egg ────────────────────────────────────────────────────────────────
// 10× auf das große Foto klicken innerhalb von 3 Sekunden → Vettel-Video

const lightboxImg   = document.getElementById('lightboxImg');
const videoOverlay  = document.getElementById('videoOverlay');
const easterVideo   = document.getElementById('easterEggVideo');

let eggClicks = 0;
let eggTimer  = null;

lightboxImg.addEventListener('click', (e) => {
  e.stopPropagation(); // Lightbox nicht schließen beim Klick auf's Foto

  eggClicks++;
  clearTimeout(eggTimer);
  eggTimer = setTimeout(() => { eggClicks = 0; }, 3000);

  if (eggClicks >= 10) {
    eggClicks = 0;
    lightbox.classList.remove('open');
    easterVideo.currentTime = 0;
    videoOverlay.classList.add('open');
    easterVideo.play().catch(() => showToast('Video konnte nicht abgespielt werden.'));
    easterVideo.addEventListener('ended', () => videoOverlay.classList.remove('open'), { once: true });
  }
});

videoOverlay.addEventListener('click', () => {
  easterVideo.pause();
  videoOverlay.classList.remove('open');
});

function clearPlaying() {
  if (activeBtn) activeBtn.classList.remove('playing');
  activeBtn = null;
  document.getElementById('avatarWrap')?.classList.remove('playing');
}

function setPlaying(btn, isPlaying) {
  if (isPlaying) {
    clearPlaying();
    btn.classList.add('playing');
    activeBtn = btn;
    document.getElementById('avatarWrap')?.classList.add('playing');
  } else if (activeBtn === btn) {
    clearPlaying();
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────────

let toastTimer;
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
}

// ── Audio playback ────────────────────────────────────────────────────────────

function playUrl(url) {
  if (activeAudio) {
    activeAudio.pause();
    activeAudio.currentTime = 0;
  }
  const audio = new Audio(url);
  activeAudio = audio;
  audio.play().catch(() => {});
  return audio;
}

// ── Build clip buttons ────────────────────────────────────────────────────────

function buildClips() {
  clipsGrid.innerHTML = '';

  let globalIndex = 0;
  CATEGORIES.forEach(cat => {
    const header = document.createElement('h3');
    header.className = 'category-header';
    header.textContent = cat.label;
    clipsGrid.appendChild(header);

    const grid = document.createElement('div');
    grid.className = 'clips-grid';
    clipsGrid.appendChild(grid);

    cat.clips.forEach(clip => {
      const i = globalIndex++;
      const btn = document.createElement('button');
      btn.className = 'clip-btn';
      btn.setAttribute('aria-label', clip.text);
      btn.dataset.index = i;

      btn.innerHTML = `
        <div class="clip-icon-row">
          <span class="clip-play-icon">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </span>
          <span class="clip-state" data-state="${i}"></span>
        </div>
        <span class="clip-text">${clip.text}</span>
      `;

      btn.addEventListener('click', () => handleClipClick(btn, clip, i));
      grid.appendChild(btn);
    });
  });
}

async function handleClipClick(btn, clip, index) {
  if (btn.classList.contains('loading')) return;

  const stateEl  = btn.querySelector(`[data-state="${index}"]`);
  const cacheKey = clip.file;

  if (audioCache[cacheKey]) {
    setPlaying(btn, true);
    const audio = playUrl(audioCache[cacheKey]);
    audio.addEventListener('ended', () => setPlaying(btn, false));
    return;
  }

  btn.classList.add('loading');
  stateEl.innerHTML = '<span class="spinner"></span>';

  try {
    const localRes = await fetch(clip.file).catch(() => null);
    if (!localRes || !localRes.ok) {
      showToast('Audio-Datei nicht gefunden.');
      return;
    }

    const blob = await localRes.blob();
    const url  = URL.createObjectURL(blob);
    audioCache[cacheKey] = url;

    stateEl.textContent = '✓';
    stateEl.className   = 'clip-state cached';

    setPlaying(btn, true);
    const audio = playUrl(url);
    audio.addEventListener('ended', () => setPlaying(btn, false));
  } catch (e) {
    stateEl.textContent = '✗';
    stateEl.style.color = 'var(--error)';
    showToast('Fehler: ' + e.message);
  } finally {
    btn.classList.remove('loading');
  }
}

// ── AUSKOMMENTIERT – ElevenLabs Settings & TTS (bei Bedarf wieder aktivieren) ─
/*
function getConfig() {
  return {
    apiKey:  localStorage.getItem('sb_api_key')  || '',
    voiceId: localStorage.getItem('sb_voice_id') || '',
  };
}

async function synthesize(text) {
  const { apiKey, voiceId } = getConfig();
  if (!apiKey || !voiceId) return null;
  if (audioCache[text]) return audioCache[text];
  const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
    method: 'POST',
    headers: { 'Accept': 'audio/mpeg', 'Content-Type': 'application/json', 'xi-api-key': apiKey },
    body: JSON.stringify({ text, model_id: 'eleven_multilingual_v2', voice_settings: { stability: 0.45, similarity_boost: 0.80 } }),
  });
  if (!res.ok) throw new Error(`Fehler ${res.status}`);
  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  audioCache[text] = url;
  return url;
}

const settingsBtn     = document.getElementById('settingsBtn');
const closeSettingsBtn= document.getElementById('closeSettingsBtn');
const settingsPanel   = document.getElementById('settingsPanel');
const overlay         = document.getElementById('overlay');
const apiKeyInput     = document.getElementById('apiKeyInput');
const voiceIdInput    = document.getElementById('voiceIdInput');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const settingsStatus  = document.getElementById('settingsStatus');
const speakBtn        = document.getElementById('speakBtn');
const speakBtnLabel   = document.getElementById('speakBtnLabel');
const ttsInput        = document.getElementById('ttsInput');

settingsBtn.addEventListener('click', () => {
  apiKeyInput.value  = getConfig().apiKey;
  voiceIdInput.value = getConfig().voiceId;
  settingsPanel.classList.add('open');
  overlay.classList.add('visible');
});
closeSettingsBtn.addEventListener('click', () => {
  settingsPanel.classList.remove('open');
  overlay.classList.remove('visible');
});
overlay.addEventListener('click', () => {
  settingsPanel.classList.remove('open');
  overlay.classList.remove('visible');
});
saveSettingsBtn.addEventListener('click', () => {
  localStorage.setItem('sb_api_key',  apiKeyInput.value.trim());
  localStorage.setItem('sb_voice_id', voiceIdInput.value.trim());
  settingsStatus.textContent = '✓ Gespeichert';
  setTimeout(() => { settingsPanel.classList.remove('open'); overlay.classList.remove('visible'); }, 700);
});
speakBtn.addEventListener('click', async () => {
  const text = ttsInput.value.trim();
  if (!text) { showToast('Bitte Text eingeben.'); return; }
  speakBtn.classList.add('loading');
  speakBtnLabel.textContent = 'Wird generiert…';
  try {
    const url = await synthesize(text);
    if (url) playUrl(url);
  } catch (e) {
    showToast('Fehler: ' + e.message);
  } finally {
    speakBtn.classList.remove('loading');
    speakBtnLabel.textContent = 'Sprechen';
  }
});
*/

// ── Init ──────────────────────────────────────────────────────────────────────

buildClips();

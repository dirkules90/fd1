'use strict';

const CLIPS = [
  'Wer auf Toilette möchte, hebt bitte die Hand.',
  'Heute geht die erste Runde Bier selbstverständlich auf mich.',
  'Der Herr ist mein Hirte. Mein Fahrer ist heute Pascal.',
  'Ich erkenne ein gutes Auto daran, wie bequem der Beifahrersitz ist.',
  'Mein Lieblingsauto ist das, in dem mich andere mitnehmen.',
  'Alkoholische Mitarbeit ist heute ausdrücklich erwünscht.',
  'Ich fühle mich wie 2009 im Bierkönig.',
  'Mein Verantwortungsbereich endet ab dem zweiten Bier.',
];

const audioCache = {};

// ── DOM refs ──────────────────────────────────────────────────────────────────

const settingsBtn      = document.getElementById('settingsBtn');
const closeSettingsBtn = document.getElementById('closeSettingsBtn');
const settingsPanel    = document.getElementById('settingsPanel');
const overlay          = document.getElementById('overlay');
const apiKeyInput      = document.getElementById('apiKeyInput');
const voiceIdInput     = document.getElementById('voiceIdInput');
const saveSettingsBtn  = document.getElementById('saveSettingsBtn');
const settingsStatus   = document.getElementById('settingsStatus');
const speakBtn         = document.getElementById('speakBtn');
const speakBtnLabel    = document.getElementById('speakBtnLabel');
const ttsInput         = document.getElementById('ttsInput');
const clipsGrid        = document.getElementById('clipsGrid');
const toast            = document.getElementById('toast');

// ── Settings ──────────────────────────────────────────────────────────────────

function getConfig() {
  return {
    apiKey:  localStorage.getItem('sb_api_key')   || '',
    voiceId: localStorage.getItem('sb_voice_id')  || '',
  };
}

function openSettings() {
  const { apiKey, voiceId } = getConfig();
  apiKeyInput.value  = apiKey;
  voiceIdInput.value = voiceId;
  settingsStatus.textContent = '';
  settingsPanel.classList.add('open');
  settingsPanel.setAttribute('aria-hidden', 'false');
  overlay.classList.add('visible');
}

function closeSettings() {
  settingsPanel.classList.remove('open');
  settingsPanel.setAttribute('aria-hidden', 'true');
  overlay.classList.remove('visible');
}

saveSettingsBtn.addEventListener('click', () => {
  const key     = apiKeyInput.value.trim();
  const voiceId = voiceIdInput.value.trim();

  if (!key || !voiceId) {
    settingsStatus.style.color = 'var(--error)';
    settingsStatus.textContent = 'Bitte beide Felder ausfüllen.';
    return;
  }

  localStorage.setItem('sb_api_key',   key);
  localStorage.setItem('sb_voice_id',  voiceId);
  settingsStatus.style.color = 'var(--success)';
  settingsStatus.textContent = '✓ Gespeichert';
  setTimeout(() => closeSettings(), 700);
  hideBanner();
});

settingsBtn.addEventListener('click', openSettings);
closeSettingsBtn.addEventListener('click', closeSettings);
overlay.addEventListener('click', closeSettings);

// ── Toast ─────────────────────────────────────────────────────────────────────

let toastTimer;
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
}

// ── TTS API call ──────────────────────────────────────────────────────────────

async function synthesize(text) {
  const { apiKey, voiceId } = getConfig();

  if (!apiKey || !voiceId) {
    openSettings();
    showToast('Bitte zuerst API Key & Voice ID eingeben.');
    return null;
  }

  if (audioCache[text]) return audioCache[text];

  const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
    method: 'POST',
    headers: {
      'Accept': 'audio/mpeg',
      'Content-Type': 'application/json',
      'xi-api-key': apiKey,
    },
    body: JSON.stringify({
      text,
      model_id: 'eleven_multilingual_v2',
      voice_settings: { stability: 0.45, similarity_boost: 0.80 },
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = err?.detail?.message || err?.detail || `Fehler ${res.status}`;
    throw new Error(msg);
  }

  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  audioCache[text] = url;
  return url;
}

function playUrl(url) {
  const audio = new Audio(url);
  audio.play().catch(() => {});
  return audio;
}

// ── Speak button (TTS input) ──────────────────────────────────────────────────

speakBtn.addEventListener('click', async () => {
  const text = ttsInput.value.trim();
  if (!text) { showToast('Bitte Text eingeben.'); return; }

  speakBtn.classList.add('loading');
  speakBtnLabel.textContent = 'Wird generiert…';

  try {
    const url = await synthesize(text);
    if (url) {
      playUrl(url);
      speakBtnLabel.textContent = '▶ Sprechen';
    }
  } catch (e) {
    showToast('Fehler: ' + e.message);
  } finally {
    speakBtn.classList.remove('loading');
    speakBtnLabel.textContent = 'Sprechen';
  }
});

// ── Build clip buttons ────────────────────────────────────────────────────────

function buildClips() {
  clipsGrid.innerHTML = '';

  CLIPS.forEach((text, i) => {
    const btn = document.createElement('button');
    btn.className = 'clip-btn';
    btn.setAttribute('aria-label', text);
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
      <span class="clip-text">${text}</span>
    `;

    btn.addEventListener('click', () => handleClipClick(btn, text, i));
    clipsGrid.appendChild(btn);
  });
}

async function handleClipClick(btn, text, index) {
  if (btn.classList.contains('loading')) return;

  const stateEl = btn.querySelector(`[data-state="${index}"]`);

  if (audioCache[text]) {
    btn.classList.add('playing');
    const audio = playUrl(audioCache[text]);
    audio.addEventListener('ended', () => btn.classList.remove('playing'));
    return;
  }

  btn.classList.add('loading');
  stateEl.innerHTML = '<span class="spinner"></span>';

  try {
    const url = await synthesize(text);
    if (!url) return;

    stateEl.textContent = '✓';
    stateEl.className = 'clip-state cached';

    btn.classList.add('playing');
    const audio = playUrl(url);
    audio.addEventListener('ended', () => btn.classList.remove('playing'));
  } catch (e) {
    stateEl.textContent = '✗';
    stateEl.className = 'clip-state';
    stateEl.style.color = 'var(--error)';
    showToast('Fehler: ' + e.message);
  } finally {
    btn.classList.remove('loading');
  }
}

// ── Setup banner (when no config yet) ────────────────────────────────────────

function showBannerIfNeeded() {
  const { apiKey, voiceId } = getConfig();
  if (apiKey && voiceId) return;

  const banner = document.createElement('div');
  banner.className = 'setup-banner';
  banner.id = 'setupBanner';
  banner.textContent = '⚙ Einstellungen öffnen – API Key & Voice ID eingeben';
  banner.addEventListener('click', openSettings);

  const main = document.querySelector('.main');
  main.insertBefore(banner, main.firstChild);
}

function hideBanner() {
  const b = document.getElementById('setupBanner');
  if (b) b.remove();
}

// ── Init ──────────────────────────────────────────────────────────────────────

buildClips();
showBannerIfNeeded();

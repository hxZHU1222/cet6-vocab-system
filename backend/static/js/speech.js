const CET6_AUTO_SPEAK_KEY = 'cet6_auto_speak';

function getAutoSpeakEnabled() {
  const saved = localStorage.getItem(CET6_AUTO_SPEAK_KEY);
  // 新版默认开启；用户手动关闭后才保持关闭。
  return saved === null ? true : saved === '1';
}

function setAutoSpeakEnabled(enabled) {
  localStorage.setItem(CET6_AUTO_SPEAK_KEY, enabled ? '1' : '0');
}

function speakEnglish(text, slow=false) {
  if (!('speechSynthesis' in window) || !text) return false;
  try {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = slow ? 0.72 : 0.82;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    const voices = window.speechSynthesis.getVoices ? window.speechSynthesis.getVoices() : [];
    const saved = localStorage.getItem('cet6_voice_name');
    let voice = voices.find(v => v.name === saved)
      || voices.find(v => v.lang === 'en-US' && /aria|samantha|google|natural|premium/i.test(v.name))
      || voices.find(v => v.lang === 'en-US')
      || voices.find(v => /^en/i.test(v.lang));
    if (voice) utterance.voice = voice;
    window.speechSynthesis.speak(utterance);
    return true;
  } catch (err) {
    console.warn('Speech synthesis failed:', err);
    return false;
  }
}

function autoSpeakEnglish(text) {
  if (!getAutoSpeakEnabled()) return false;
  // 延迟一点，避免文字刚刷新时被上一条发音打断得太生硬。
  window.setTimeout(() => speakEnglish(text, false), 120);
  return true;
}

function updateAutoSpeakButton(button) {
  if (!button) return;
  const enabled = getAutoSpeakEnabled();
  button.textContent = enabled ? '自动发音：开' : '自动发音：关';
  button.classList.toggle('is-on', enabled);
}

if ('speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}

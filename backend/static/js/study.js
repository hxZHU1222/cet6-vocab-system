const params = new URLSearchParams(location.search);
const mode = params.get('mode') || 'today_new';
let cards = [];
let index = 0;
let lastRenderedWordId = null;
const modeName = {
  today_new: '今日新词', today_review: '到期复习', weak: '弱词回看', wrong: '错词卡片', mastered: '熟词抽查', random: '随机刷词', preview: '继续预习'
};
function current() { return index >= 0 && index < cards.length ? cards[index] : null; }
function setText(id, value) { const el = document.getElementById(id); if (el) el.textContent = value; }
function showEmpty(done = false) {
  document.getElementById('emptyHint').style.display = 'block';
  setText('sessionInfo', done ? `${modeName[mode] || '单词学习'} 已完成` : `${modeName[mode] || '单词学习'} 0 / 0`);
  setText('wordModeLabel', 'WORDS');
  setText('wordText', done ? '这一组已完成' : '没有待学单词');
  setText('phonetic', '');
  setText('meaning', done ? '刷新页面也不会回到已经完成的词。可以去默写、弱词回看或随机刷词。' : '你可以切换到随机刷词、弱词回看或继续预习。');
  setText('exampleEn', '');
  setText('exampleCn', '');
  lastRenderedWordId = null;
}
function render(options = {}) {
  const shouldAutoSpeak = options.autoSpeak !== false;
  updateAutoSpeakButton(document.getElementById('autoSpeakToggle'));
  if (!cards.length || index >= cards.length) {
    showEmpty(cards.length > 0 && index >= cards.length);
    return;
  }
  document.getElementById('emptyHint').style.display = 'none';
  const item = current();
  setText('sessionInfo', `${modeName[mode] || '单词学习'} ${index + 1} / ${cards.length}`);
  setText('wordModeLabel', modeName[mode] || 'WORDS');
  setText('wordText', item.word);
  setText('phonetic', item.phonetic || '');
  setText('meaning', item.meaning_cn || '暂无释义');
  setText('exampleEn', item.example_en || '暂无英文例句');
  setText('exampleCn', item.example_cn || '');
  if (shouldAutoSpeak && item.id !== lastRenderedWordId) {
    lastRenderedWordId = item.id;
    autoSpeakEnglish(item.word);
  } else {
    lastRenderedWordId = item.id;
  }
}
async function load() {
  const data = await apiGet(`/api/words/study?mode=${encodeURIComponent(mode)}&limit=100`);
  cards = data.items || [];
  index = 0;
  lastRenderedWordId = null;
  render({ autoSpeak: true });
}
async function submitGrade(grade) {
  const item = current();
  if (!item) return;
  const buttons = document.querySelectorAll('.grade-btn');
  buttons.forEach(b => b.disabled = true);
  try {
    await apiPost('/api/words/grade', { word_id: item.id, grade, source: `word_${mode}` });
    // 单词页的四个熟悉度按钮就是“下一词”：保存成功后立即前进。
    index += 1;
    render({ autoSpeak: true });
  } finally {
    buttons.forEach(b => b.disabled = false);
  }
}
document.querySelectorAll('.grade-btn').forEach(btn => btn.addEventListener('click', () => submitGrade(Number(btn.dataset.grade))));
document.getElementById('prevCardBtn').addEventListener('click', () => {
  if (index > 0) index -= 1;
  render({ autoSpeak: true });
});
document.getElementById('speakBtn').addEventListener('click', () => { const item = current(); if (item) speakEnglish(item.word); });
document.getElementById('slowSpeakBtn').addEventListener('click', () => { const item = current(); if (item) speakEnglish(item.word, true); });
document.getElementById('autoSpeakToggle').addEventListener('click', () => {
  const next = !getAutoSpeakEnabled();
  setAutoSpeakEnabled(next);
  updateAutoSpeakButton(document.getElementById('autoSpeakToggle'));
  const item = current();
  if (next && item) speakEnglish(item.word);
});
load().catch(err => { setText('meaning', `加载失败：${err.message}`); });

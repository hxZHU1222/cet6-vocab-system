const params = new URLSearchParams(location.search);
const mode = params.get('mode') || 'today';
let cards = [];
let index = 0;
const modeName = { today: '今日最低默写', random: '随机默写', wrong: '错词默写', weak: '弱词默写', learned: '已学词默写' };
function current() { return cards[index]; }
function render() {
  const empty = cards.length === 0;
  document.getElementById('dictationInfo').textContent = empty ? `${modeName[mode] || '默写'} 0 / 0` : `${modeName[mode] || '默写'} ${index + 1} / ${cards.length}`;
  document.getElementById('resultBox').textContent = '';
  document.getElementById('answerInput').value = '';
  if (empty) {
    document.getElementById('dictationMeaning').textContent = '这一组暂时没有可默写单词。';
    document.getElementById('dictationExampleCn').textContent = '可以切换到随机默写。';
    return;
  }
  const item = current();
  document.getElementById('dictationMeaning').textContent = item.meaning_cn || '暂无释义';
  document.getElementById('dictationExampleCn').textContent = item.example_cn || '';
  setTimeout(() => document.getElementById('answerInput').focus(), 80);
}
async function load() {
  const data = await apiGet(`/api/words/dictation-session?mode=${encodeURIComponent(mode)}&limit=20`);
  cards = data.items || [];
  render();
}
async function submit() {
  if (!cards.length) return;
  const item = current();
  const answer = document.getElementById('answerInput').value;
  const result = await apiPost('/api/words/dictation-submit', { word_id: item.id, answer, source: `dictation_${mode}` });
  document.getElementById('resultBox').innerHTML = result.is_correct
    ? `<strong class="ok">正确</strong>：${result.correct_answer}`
    : `<strong class="error">错误</strong>：正确答案是 <b>${result.correct_answer}</b>，你的答案是 ${result.user_answer || '空'}`;
}
document.getElementById('submitAnswerBtn').addEventListener('click', submit);
document.getElementById('answerInput').addEventListener('keydown', e => { if (e.key === 'Enter') submit(); });
document.getElementById('prevBtn').addEventListener('click', () => { if (index > 0) index -= 1; render(); });
document.getElementById('nextBtn').addEventListener('click', () => { if (index < cards.length - 1) index += 1; else if (cards.length) cards.splice(index, 1), index = Math.max(0, index - 1); render(); });
load().catch(err => { document.getElementById('dictationMeaning').textContent = `加载失败：${err.message}`; });

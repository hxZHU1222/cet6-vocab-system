const params = new URLSearchParams(location.search);
const mode = params.get('mode') || 'new';
let cards = [];
let index = 0;
const modeName = { today_new: '今日新句型', today_review: '今日复习', new: '新句型', review: '到期复习', weak: '弱项回看', all: '随机抽查' };

function render() {
  const empty = cards.length === 0;
  document.getElementById('sessionInfo').textContent = empty ? '没有可学习句型' : `${modeName[mode] || '句型学习'} ${index + 1} / ${cards.length}`;
  if (empty) {
    document.getElementById('patternTitle').textContent = '没有可学习句型';
    document.getElementById('patternEn').textContent = '可以先导入句型，或切换到随机抽查。';
    document.getElementById('patternCn').textContent = '';
    document.getElementById('exampleEn').textContent = '';
    document.getElementById('exampleCn').textContent = '';
    document.getElementById('slots').textContent = '';
    document.getElementById('usageNote').textContent = '';
    return;
  }
  const item = cards[index];
  document.getElementById('patternCategory').textContent = item.category;
  document.getElementById('patternTitle').textContent = item.title;
  document.getElementById('patternEn').textContent = item.pattern_en;
  document.getElementById('patternCn').textContent = item.pattern_cn || '';
  document.getElementById('exampleEn').textContent = item.example_en || '';
  document.getElementById('exampleCn').textContent = item.example_cn || '';
  document.getElementById('slots').textContent = item.slots || '无';
  document.getElementById('usageNote').textContent = item.usage_note || '';
}
async function load() {
  const data = await apiGet(`/api/sentence-patterns/study?mode=${encodeURIComponent(mode)}&limit=20`);
  cards = data.items || [];
  render();
}
async function submitGrade(grade) {
  if (!cards.length) return;
  const item = cards[index];
  await apiPost('/api/sentence-patterns/grade', { pattern_id: item.id, grade, source: `pattern_${mode}` });
  // 句型页保留“阅读/吸收”节奏：评分只保存，不强制跳到下一张。
  const label = modeName[mode] || '句型学习';
  document.getElementById('sessionInfo').textContent = `${label} ${index + 1} / ${cards.length} · 已记录`;
}
document.querySelectorAll('.grade-btn').forEach(btn => btn.addEventListener('click', () => submitGrade(Number(btn.dataset.grade))));
document.getElementById('prevCardBtn').addEventListener('click', () => { if (index > 0) index -= 1; render(); });
document.getElementById('nextCardBtn').addEventListener('click', () => { if (index < cards.length - 1) index += 1; render(); });
load();

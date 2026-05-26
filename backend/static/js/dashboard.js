function pct(n) { return `${Math.round(Number(n || 0))}%`; }
function setBar(id, value) { const el = document.getElementById(id); if (el) el.style.width = `${Math.max(0, Math.min(100, Number(value || 0)))}%`; }
async function loadDashboard() {
  const data = await apiGet('/api/dashboard/today');
  const w = data.word.today || {};
  const p = data.patterns.today || {};
  document.getElementById('wordRate').textContent = pct(w.completion_rate);
  document.getElementById('wordSummary').textContent = `新词 ${w.new_done || 0}/${w.new_total || 0} · 复习 ${w.review_done || 0}/${w.review_total || 0} · 默写 ${w.dictation_done || 0}/${w.dictation_target || 20}`;
  setBar('wordBar', w.completion_rate);
  document.getElementById('patternRate').textContent = pct(p.completion_rate);
  document.getElementById('patternSummary').textContent = `新句型 ${p.new_done || 0}/${p.new_total || 0} · 复习 ${p.review_done || 0}/${p.review_total || 0}`;
  setBar('patternBar', p.completion_rate);
}
loadDashboard().catch(err => {
  document.getElementById('wordSummary').textContent = `读取失败：${err.message}`;
});

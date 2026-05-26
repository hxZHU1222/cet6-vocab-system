function pct(done, total) { return total ? Math.round(done / total * 100) : 0; }
function fmtPct(n) { return `${Math.max(0, Math.min(100, Math.round(Number(n || 0))))}%`; }
function setText(id, text) { const el = document.getElementById(id); if (el) el.textContent = text; }
function setBar(id, value) { const el = document.getElementById(id); if (el) el.style.width = `${Math.max(0, Math.min(100, Number(value || 0)))}%`; }
function setTaskLine(prefix, label, done, total) {
  const rate = pct(done, total);
  setText(`${prefix}Text`, `${label} ${done || 0}/${total || 0}`);
  setText(`${prefix}Rate`, fmtPct(rate));
  setBar(`${prefix}Bar`, rate);
  return rate;
}
function renderSegmented(dist, total) {
  const box = document.getElementById('wordSegmentedBar');
  const parts = [
    ['unlearned', '未学'],
    ['weak', '弱词'],
    ['semi', '半熟'],
    ['mastered', '熟词'],
  ];
  box.innerHTML = '';
  const base = Math.max(total || 0, 1);
  parts.forEach(([key, label]) => {
    const value = Number(dist?.[key] || 0);
    const span = document.createElement('span');
    span.className = `seg-${key}`;
    span.style.width = `${value / base * 100}%`;
    span.title = `${label} ${value}`;
    box.appendChild(span);
  });
}
async function loadStats() {
  const data = await apiGet('/api/dashboard/today');
  const ws = data.word.stats || {}; const wt = data.word.today || {};
  const ps = data.patterns.stats || {}; const pt = data.patterns.today || {};
  const newRate = setTaskLine('wordNew', '新词', wt.new_done || 0, wt.new_total || 0);
  const reviewRate = setTaskLine('wordReview', '复习', wt.review_done || 0, wt.review_total || 0);
  const dictRate = setTaskLine('wordDictation', '默写', wt.dictation_done || 0, wt.dictation_target || 20);
  const patternTotalToday = (pt.new_total || 0) + (pt.review_total || 0);
  const patternDoneToday = (pt.new_done || 0) + (pt.review_done || 0);
  const patternRate = pct(patternDoneToday, patternTotalToday);
  setText('patternTodayText', `今日句型 新句型 ${pt.new_done || 0}/${pt.new_total || 0} · 复习 ${pt.review_done || 0}/${pt.review_total || 0}`);
  setText('patternTodayRate', fmtPct(patternRate)); setBar('patternTodayBar', patternRate);
  const wordClosed = (wt.new_total === 0 || (wt.new_done || 0) >= (wt.new_total || 0)) &&
                     (wt.review_total === 0 || (wt.review_done || 0) >= (wt.review_total || 0)) &&
                     ((wt.dictation_done || 0) >= (wt.dictation_target || 20));
  const patternClosed = patternTotalToday === 0 || patternDoneToday >= patternTotalToday;
  if (wordClosed && patternClosed) {
    setText('todayCloseTitle', '今日闭环完成');
    setText('todayCloseAdvice', '今天可以只做自由复习、弱词回看或休息。');
  } else {
    setText('todayCloseTitle', '今日还差一点');
    const missing = [];
    if ((wt.new_done || 0) < (wt.new_total || 0)) missing.push(`新词 ${Math.max((wt.new_total || 0) - (wt.new_done || 0), 0)} 个`);
    if ((wt.review_done || 0) < (wt.review_total || 0)) missing.push(`复习 ${Math.max((wt.review_total || 0) - (wt.review_done || 0), 0)} 个`);
    if ((wt.dictation_done || 0) < (wt.dictation_target || 20)) missing.push(`默写 ${Math.max((wt.dictation_target || 20) - (wt.dictation_done || 0), 0)} 个`);
    if (patternDoneToday < patternTotalToday) missing.push(`句型 ${patternTotalToday - patternDoneToday} 个`);
    setText('todayCloseAdvice', `还差：${missing.join('、') || '无'}。建议先补新词，再做默写。`);
  }
  setText('wordTotal', ws.total || 0); setText('wordSeen', ws.seen || ws.learned || 0);
  setText('wordUnlearned', ws.distribution?.unlearned ?? ws.unlearned ?? 0);
  setText('wordWeak', ws.distribution?.weak ?? ws.weak ?? 0);
  setText('wordSemi', ws.distribution?.semi ?? ws.semi ?? 0);
  setText('wordMastered', ws.distribution?.mastered ?? ws.mastered ?? 0);
  setText('wordWrong', ws.active_wrong || 0); setText('wordDue', ws.due_review || 0);
  renderSegmented(ws.distribution || {}, ws.total || 0);
  setText('patternTotal', ps.total || 0); setText('patternSeen', ps.seen || 0); setText('patternWeak', ps.weak || 0); setText('patternMastered', ps.mastered || 0);
  const total = Math.max(ps.total || 0, 1);
  const box = document.getElementById('categoryBars'); box.innerHTML = '';
  (ps.categories || []).forEach(row => {
    const wrap = document.createElement('div'); wrap.className = 'bar-row';
    wrap.innerHTML = `<div class="bar-row-top"><span>${row.category}</span><span>${row.count}</span></div><div class="bar-track"><span class="bar-fill" style="width:${row.count/total*100}%"></span></div>`;
    box.appendChild(wrap);
  });
}
loadStats().catch(err => {
  setText('todayCloseTitle', '统计读取失败');
  setText('todayCloseAdvice', err.message);
});

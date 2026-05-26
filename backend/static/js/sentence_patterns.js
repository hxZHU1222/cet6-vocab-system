let currentPage = 1;
let totalPages = 1;

function gradeLabel(progress) {
  if (!progress || progress.familiarity === null) return '未开始';
  if (progress.is_mastered) return '熟了';
  return ['不会', '眼熟', '会套用', '熟了'][progress.familiarity] || '学习中';
}
function cardHTML(item) {
  return `<article class="pattern-card">
    <div class="meta-row"><span class="badge">${item.category}</span><span class="badge">难度 ${item.difficulty}</span><span class="badge">${gradeLabel(item.progress)}</span></div>
    <h3>${item.title}</h3>
    <p class="mini-label">句型模板</p>
    <p class="pattern-en">${item.pattern_en}</p>
    <p class="muted">${item.pattern_cn || ''}</p>
    <p class="mini-label">六级例句</p>
    <p>${item.example_en || ''}</p>
    <p class="muted">${item.example_cn || ''}</p>
    <div class="action-grid two"><a class="btn-secondary" href="/patterns/study?mode=all&start=${item.id}">练这一条</a><button class="btn-primary" data-id="${item.id}">标为熟了</button></div>
  </article>`;
}
async function loadCategories() {
  const select = document.getElementById('categorySelect');
  const cats = await apiGet('/api/sentence-patterns/categories');
  select.innerHTML = '<option value="">全部分类</option>' + cats.map(c => `<option value="${c.category}">${c.category} (${c.count})</option>`).join('');
}
async function loadPatterns(page = 1) {
  currentPage = page;
  const q = encodeURIComponent(document.getElementById('searchInput').value.trim());
  const category = encodeURIComponent(document.getElementById('categorySelect').value);
  const status = encodeURIComponent(document.getElementById('statusSelect').value);
  const data = await apiGet(`/api/sentence-patterns?page=${page}&per_page=20&q=${q}&category=${category}&status=${status}`);
  totalPages = data.pages || 1;
  document.getElementById('patternList').innerHTML = data.items.length ? data.items.map(cardHTML).join('') : '<section class="hero-card"><h2>没有找到句型</h2><p class="muted">可以换个关键词，或先导入内置 P10 数据。</p></section>';
  document.getElementById('pageInfo').textContent = `${data.page} / ${totalPages} · 共 ${data.total} 条`;
}
document.addEventListener('click', async (event) => {
  const btn = event.target.closest('button[data-id]');
  if (btn) {
    await apiPost('/api/sentence-patterns/grade', { pattern_id: Number(btn.dataset.id), grade: 3, source: 'pattern_list' });
    await loadPatterns(currentPage);
  }
});
document.getElementById('prevBtn').addEventListener('click', () => currentPage > 1 && loadPatterns(currentPage - 1));
document.getElementById('nextBtn').addEventListener('click', () => currentPage < totalPages && loadPatterns(currentPage + 1));
['searchInput','categorySelect','statusSelect'].forEach(id => document.getElementById(id).addEventListener('input', () => loadPatterns(1)));
loadCategories().then(() => loadPatterns());

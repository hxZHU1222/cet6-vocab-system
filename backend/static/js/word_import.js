document.getElementById('uploadWordBtn').addEventListener('click', async () => {
  const file = document.getElementById('wordCsv').files[0];
  if (!file) { alert('请先选择 CSV 文件'); return; }
  const result = await apiUpload('/api/words/import', file);
  document.getElementById('importResult').textContent = JSON.stringify(result, null, 2);
});

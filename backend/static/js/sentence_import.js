const box = document.getElementById('resultBox');
function show(data) { box.textContent = JSON.stringify(data, null, 2); }
document.getElementById('defaultImportBtn').addEventListener('click', async () => {
  box.textContent = '正在导入内置 P10 句型……';
  try { show(await apiPost('/api/sentence-patterns/default-import', {})); }
  catch (err) { box.textContent = String(err); }
});
document.getElementById('uploadBtn').addEventListener('click', async () => {
  const file = document.getElementById('csvFile').files[0];
  if (!file) { box.textContent = '请先选择 CSV 文件。'; return; }
  box.textContent = '正在上传导入……';
  try { show(await apiUpload('/api/sentence-patterns/import', file)); }
  catch (err) { box.textContent = String(err); }
});

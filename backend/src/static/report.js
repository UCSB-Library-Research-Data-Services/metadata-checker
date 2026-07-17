function toggleCheckFlip(flip) {
  const expanded = flip.getAttribute('aria-expanded') === 'true';
  flip.setAttribute('aria-expanded', String(!expanded));
}

document.addEventListener('click', function (event) {
  const flip = event.target.closest('.check-flip');
  if (!flip) return;
  toggleCheckFlip(flip);
});

document.addEventListener('keydown', function (event) {
  if (event.key !== 'Enter' && event.key !== ' ') return;
  const flip = event.target.closest ? event.target.closest('.check-flip') : null;
  if (!flip) return;
  event.preventDefault();
  toggleCheckFlip(flip);
});

document.addEventListener('click', async function (event) {
  const toggleBtn = event.target.closest('.visibility-toggle');
  if (!toggleBtn) return;

  const card = toggleBtn.closest('.check');
  const response = await fetch('/api/toggle-check-visibility', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      dataset_id: toggleBtn.dataset.datasetId,
      check_id: toggleBtn.dataset.checkId
    })
  });

  if (response.ok) {
    const result = await response.json();
    const isVisible = !!result.visibility;
    card.classList.toggle('ignored', !isVisible);
    toggleBtn.setAttribute('aria-pressed', String(isVisible));
    toggleBtn.textContent = isVisible ? 'Ignore' : 'Ignored';
  }
});

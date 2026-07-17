document.addEventListener('click', function (event) {
  const btn = event.target.closest('.check-toggle');
  if (!btn) return;
  const detail = btn.closest('.check').querySelector('.check-detail');
  const expanded = btn.getAttribute('aria-expanded') === 'true';
  btn.setAttribute('aria-expanded', String(!expanded));
  detail.hidden = expanded;
});

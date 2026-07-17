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

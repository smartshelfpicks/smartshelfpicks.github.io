(function () {
  var q = (new URLSearchParams(location.search).get('q') || '').trim();
  var box = document.getElementById('q'); if (box) box.value = q;
  var title = document.getElementById('s-title'), out = document.getElementById('s-results'), empty = document.getElementById('s-empty');
  if (!q) { title.textContent = 'Search picks'; return; }
  title.textContent = 'Results for “' + q + '”';
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  fetch('/products.json').then(function (r) { return r.json(); }).then(function (list) {
    var words = q.toLowerCase().split(/\s+/).filter(Boolean);
    var hits = list.filter(function (p) {
      var t = (p.name + ' ' + p.cat + ' ' + p.caption + ' ' + p.store).toLowerCase();
      return words.every(function (w) { return t.indexOf(w) >= 0; });
    });
    if (!hits.length) { empty.hidden = false; return; }
    out.innerHTML = hits.map(function (p) {
      return '<article class="card"><a class="card-img" href="/p/' + esc(p.slug) + '/">' + (p.badge ? '<span class="badge">' + esc(p.badge) + '</span>' : '') +
        '<img src="' + esc(p.image) + '" alt="' + esc(p.name) + '" loading="lazy" referrerpolicy="no-referrer"></a><div class="card-body">' +
        '<a class="card-cat" href="/category/' + esc(p.cat_slug) + '/">' + esc(p.cat) + '</a><h3><a href="/p/' + esc(p.slug) + '/">' + esc(p.name) + '</a></h3>' +
        '<p>' + esc(p.caption) + '</p><a class="btn" href="' + esc(p.link) + '" rel="sponsored nofollow noopener" target="_blank">See today’s price at ' + esc(p.store) + '</a></div></article>';
    }).join('');
  });
})();

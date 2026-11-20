(function () {
  var f = document.getElementById('contact-form');
  if (!f) return;
  var b = f.querySelector('button[type=submit]'), st = document.getElementById('ssp-status');
  function say(ok, msg) { st.className = 'ssp-status ' + (ok ? 'ok' : 'err'); st.textContent = msg; }
  f.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var email = f.email.value.trim(), msg = f.message.value.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) { say(false, 'Please enter a valid email address.'); f.email.focus(); return; }
    if (msg.length < 5) { say(false, 'Please write a short message.'); f.message.focus(); return; }
    b.disabled = true; b.textContent = 'Sending...'; st.textContent = '';
    var body = new URLSearchParams(new FormData(f));
    fetch(f.action, { method: 'POST', mode: 'no-cors', body: body })
      .then(function () { f.reset(); say(true, 'Thanks! Your message was sent. We’ll reply to the email you entered.'); })
      .catch(function () { say(false, 'Something went wrong. Please try again, or email smartshelfpicks@gmail.com.'); })
      .then(function () { b.disabled = false; b.textContent = 'Send message'; });
  });
})();

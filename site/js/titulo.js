(function () {
  var cfg = window.DESCREVI || {};
  var intake = (cfg.intakeUrl || "").replace(/\/$/, "");
  var form = document.getElementById("form");
  var msg = document.getElementById("msg");
  var saida = document.getElementById("saida");
  var btn = document.getElementById("enviar");

  // Atualiza o sitekey se o config trouxe outro
  var tw = document.querySelector(".cf-turnstile");
  if (tw && cfg.turnstileSiteKey) tw.setAttribute("data-sitekey", cfg.turnstileSiteKey);

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    msg.hidden = true;
    btn.disabled = true;
    var token = "";
    if (window.turnstile && tw) {
      try { token = window.turnstile.getResponse(tw) || ""; } catch (e) { token = ""; }
    }
    if (!token) {
      var hidden = document.querySelector("[name=cf-turnstile-response]");
      if (hidden) token = hidden.value || "";
    }
    fetch(intake + "/titulo-gratis", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        nome_produto: document.getElementById("nome").value,
        categoria: document.getElementById("cat").value,
        especificacoes: document.getElementById("esp").value,
        diferenciais: document.getElementById("dif").value,
        turnstile: token
      })
    }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        if (!res.ok) {
          msg.hidden = false;
          msg.className = "erro";
          msg.textContent = res.j.erro || "Não foi possível gerar o título.";
          saida.hidden = true;
          return;
        }
        saida.hidden = false;
        document.getElementById("titulo").textContent = res.j.titulo;
        document.getElementById("cont").textContent = res.j.caracteres + " de " + res.j.limite + " caracteres · " +
          (res.j.restantes_hoje != null ? res.j.restantes_hoje + " geração(ões) grátis restantes hoje." : "");
        document.getElementById("aviso").textContent = res.j.aviso || "";
      })
      .catch(function () {
        btn.disabled = false;
        msg.hidden = false;
        msg.className = "erro";
        msg.textContent = "Falha de rede. Tente de novo.";
      });
  });
})();

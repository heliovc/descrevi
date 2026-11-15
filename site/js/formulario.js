(function () {
  var cfg = window.DESCREVI || {};
  var intake = (cfg.intakeUrl || "").replace(/\/$/, "");
  var params = new URLSearchParams(location.search);
  var token = params.get("t") || "";
  var $resumo = document.getElementById("resumo");
  var $form = document.getElementById("form");
  var $itens = document.getElementById("itens");
  var $msg = document.getElementById("msg");
  var $enviar = document.getElementById("enviar");

  function erro(t) {
    $msg.hidden = false;
    $msg.textContent = t;
    $msg.className = "erro";
  }
  function ok(t) {
    $msg.hidden = false;
    $msg.textContent = t;
    $msg.className = "ok";
  }

  function campo(it) {
    var i = it.indice;
    var fs = document.createElement("fieldset");
    fs.innerHTML =
      "<legend>Produto " + i + (it.preenchido ? " (já salvo)" : "") + "</legend>" +
      '<div class="campo"><label for="nome_' + i + '">Nome do produto</label>' +
      '<p class="ajuda">Como você chama o item. Sem promoção, “frete grátis” ou “oferta”.</p>' +
      '<input type="text" id="nome_' + i + '" name="nome_' + i + '" required maxlength="200"></div>' +
      '<div class="campo"><label for="cat_' + i + '">Categoria</label>' +
      '<input type="text" id="cat_' + i + '" required maxlength="120" placeholder="Ex.: Utilidades domésticas"></div>' +
      '<div class="campo"><label for="esp_' + i + '">Características e especificações</label>' +
      '<p class="ajuda">Cole medidas, material, voltagem, capacidade, o que vem na caixa, garantia. Só o que for verdade.</p>' +
      '<textarea id="esp_' + i + '" required maxlength="4000"></textarea></div>' +
      '<div class="campo"><label for="dif_' + i + '">Diferenciais (opcional)</label>' +
      '<textarea id="dif_' + i + '" maxlength="2000" placeholder="O que esse produto tem de diferente, se você souber."></textarea></div>' +
      '<div class="campo"><label for="plat_' + i + '">Para qual plataforma</label>' +
      '<select id="plat_' + i + '"><option value="ambos">Mercado Livre e Shopee</option>' +
      '<option value="ml">Só Mercado Livre</option><option value="shopee">Só Shopee</option></select></div>' +
      '<div class="campo"><label for="link_' + i + '">Link do anúncio atual (opcional, só referência)</label>' +
      '<p class="ajuda">Não acessamos esta página. Se preencher, o endereço aparece no material entregue.</p>' +
      '<input type="url" id="link_' + i + '" maxlength="500" placeholder="https://"></div>';
    $itens.appendChild(fs);
    if (it.nome_produto) document.getElementById("nome_" + i).value = it.nome_produto;
    if (it.categoria) document.getElementById("cat_" + i).value = it.categoria;
    if (it.especificacoes) document.getElementById("esp_" + i).value = it.especificacoes;
    if (it.diferenciais) document.getElementById("dif_" + i).value = it.diferenciais;
    if (it.plataforma) document.getElementById("plat_" + i).value = it.plataforma;
    if (it.link_referencia) document.getElementById("link_" + i).value = it.link_referencia;
  }

  function ler(quantidade) {
    var itens = [];
    for (var i = 1; i <= quantidade; i++) {
      itens.push({
        indice: i,
        nome_produto: document.getElementById("nome_" + i).value,
        categoria: document.getElementById("cat_" + i).value,
        especificacoes: document.getElementById("esp_" + i).value,
        diferenciais: document.getElementById("dif_" + i).value,
        plataforma: document.getElementById("plat_" + i).value,
        link_referencia: document.getElementById("link_" + i).value
      });
    }
    return itens;
  }

  if (!token) {
    erro("Este link está incompleto. Use o endereço que chegou no seu e-mail.");
    $resumo.textContent = "Link inválido.";
    return;
  }

  fetch(intake + "/pedido?t=" + encodeURIComponent(token))
    .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, status: r.status, j: j }; }); })
    .then(function (res) {
      if (!res.ok) {
        $resumo.textContent = "Não foi possível abrir o pedido.";
        erro(res.j.erro || "link inválido ou expirado");
        return;
      }
      var d = res.j;
      $resumo.textContent = "Pacote de " + d.quantidade + " anúncio" + (d.quantidade > 1 ? "s" : "") +
        " · " + d.preenchidos + " já preenchido" + (d.preenchidos === 1 ? "" : "s") +
        (d.email ? " · " + d.email : "") + ".";
      if (d.status === "enviado") {
        ok("Este pedido já foi entregue por e-mail. Se não encontrou a mensagem, olhe no spam ou fale com o suporte.");
        return;
      }
      (d.itens || []).forEach(campo);
      $form.hidden = false;
      $form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        $enviar.disabled = true;
        var corpo = {
          token: token,
          consentimento: document.getElementById("consentimento").checked,
          itens: ler(d.quantidade)
        };
        fetch(intake + "/pedido/enviar", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(corpo)
        }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
          .then(function (res2) {
            $enviar.disabled = false;
            if (!res2.ok) {
              var det = (res2.j.detalhes || []).join(" ");
              erro((res2.j.erro || "não foi possível salvar") + (det ? " — " + det : ""));
              return;
            }
            if (res2.j.preenchidos >= res2.j.quantidade) {
              ok("Dados recebidos. Vamos montar o material e enviar por e-mail em até 24 horas. Pode fechar esta página.");
            } else {
              ok("Salvo: " + res2.j.preenchidos + " de " + res2.j.quantidade + " produtos. Falta preencher o restante para começarmos a montagem.");
            }
          })
          .catch(function () { $enviar.disabled = false; erro("Falha de rede. Tente de novo."); });
      });
    })
    .catch(function () {
      $resumo.textContent = "Não foi possível falar com o servidor.";
      erro("Falha de rede. Tente de novo em alguns minutos.");
    });
})();

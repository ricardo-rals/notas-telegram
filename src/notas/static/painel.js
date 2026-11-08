// Atalhos de busca e foto ampliada (research R4 da 004). Sem este arquivo, o painel funciona igual,
// só sem os atalhos, e a foto abre em tamanho original.
(() => {
  const editavel = (el) => el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName));
  const dialogo = () => document.getElementById("foto");

  document.addEventListener("keydown", (e) => {
    const q = document.getElementById("q");
    if (!q || dialogo()?.open) return;
    const atalho = (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey) ||
                   (e.key.toLowerCase() === "k" && (e.ctrlKey || e.metaKey));
    if (atalho && !editavel(document.activeElement)) {
      e.preventDefault();
      q.focus();
      q.select();
    } else if (e.key === "Escape" && document.activeElement === q) {
      if (q.value) {
        q.value = "";
        q.dispatchEvent(new Event("search", { bubbles: true }));
      }
      q.blur();
    }
  });

  let origem = null;
  document.addEventListener("click", (e) => {
    const link = e.target.closest("a.ampliar");
    const d = dialogo();
    if (link && d && typeof d.showModal === "function") {
      e.preventDefault();
      origem = link;
      d.querySelector("img").src = link.href;
      d.querySelector("img").alt = link.querySelector("img")?.alt || "";
      d.querySelector(".legenda").textContent = link.dataset.legenda || "";
      d.showModal();
    } else if (d?.open && (e.target === d || e.target.closest(".fechar"))) {
      d.close();  // clique no fundo (o próprio dialog) ou no botão fechar
    }
  });

  document.addEventListener("close", (e) => {
    if (e.target === dialogo()) {
      e.target.querySelector("img").src = "";
      origem?.focus();
      origem = null;
    }
  }, true);
})();

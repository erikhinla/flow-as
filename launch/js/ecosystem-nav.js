/**
 * Shared TransformBy10X ecosystem navigation.
 * TBTX is the hub. BizBuilders AI and BizBot Mrktng remain sibling subpages.
 */
(function () {
  var LAYERS = {
    tbtx: { sub: "Digital Fog diagnostic route" },
    infrastructure: { sub: "Business operating layer" },
    activation: { sub: "Growth after readiness" },
  };

  var PATHS = {
    home: "/",
    fog: "/#fog",
    diagnostic: "/diagnostic",
    kit: "/fog-free-daily",
    bbai: "/bizbuilders-ai/",
    bbm: "/bizbot-mrktng/",
  };

  function navLink(href, label, current, key) {
    var currentState = current === key ? ' class="is-current" aria-current="page"' : "";
    return '<a href="' + href + '"' + currentState + ">" + label + "</a>";
  }

  function layerCta(layer) {
    if (layer === "infrastructure") {
      return { href: PATHS.bbai + "diagnostic?entry=infrastructure", label: "Start assessment" };
    }
    if (layer === "activation") {
      return { href: PATHS.bbm + "#products", label: "View products" };
    }
    return { href: PATHS.diagnostic, label: "Take the diagnostic" };
  }

  function renderHeader(layer, current) {
    var meta = LAYERS[layer] || LAYERS.tbtx;
    var cta = layerCta(layer);
    var back =
      layer !== "tbtx"
        ? '<a class="eco-nav__back" href="' + PATHS.home + '"><span aria-hidden="true">←</span> TBTX hub</a>'
        : "";

    return (
      '<div class="eco-nav__inner">' +
      '<a class="eco-nav__brand" href="' + PATHS.home + '" aria-label="TransformBy10X home">' +
      '<span class="eco-nav__brand-main">TransformBy<em>10X</em></span>' +
      '<span class="eco-nav__brand-sub">' + meta.sub + "</span>" +
      "</a>" +
      back +
      '<nav class="eco-nav__links" aria-label="Ecosystem">' +
      navLink(PATHS.home, "Home", current, "home") +
      navLink(PATHS.diagnostic, "Diagnose", current, "diagnostic") +
      navLink(PATHS.bbai, "Business", current, "bbai") +
      navLink(PATHS.kit, "Personal", current, "kit") +
      navLink(PATHS.bbm, "Growth", current, "bbm") +
      "</nav>" +
      '<a class="eco-nav__cta" href="' + cta.href + '">' + cta.label + "</a>" +
      "</div>"
    );
  }

  function renderFooter() {
    return (
      '<div class="eco-footer__inner">' +
      "<span>© 2026 TransformBy10X</span>" +
      '<span class="eco-footer__trail">' +
      '<a href="' + PATHS.home + '">TBTX</a> / ' +
      '<a href="' + PATHS.diagnostic + '">Digital Fog Diagnostic</a> / ' +
      '<a href="' + PATHS.bbai + '">BizBuilders AI</a> / ' +
      '<a href="' + PATHS.bbm + '">BizBot Mrktng</a>' +
      "</span>" +
      "</div>"
    );
  }

  function mount() {
    var layer = document.body.getAttribute("data-eco-layer") || "tbtx";
    var current = document.body.getAttribute("data-eco-current") || "";
    var header = document.querySelector("[data-eco-header]");
    var footer = document.querySelector("[data-eco-footer]");

    if (header) {
      header.className = "eco-site-header eco-site-header--" + layer;
      header.innerHTML = renderHeader(layer, current);
    }

    if (footer) {
      footer.className = "eco-site-footer";
      footer.innerHTML = renderFooter();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();

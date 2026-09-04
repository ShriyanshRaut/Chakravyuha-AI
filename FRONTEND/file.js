(function () {
  "use strict";

  const scene = document.querySelector(".overlap-scene");
  const vision = document.querySelector(".vision-panel");
  const wash = document.querySelector(".backdrop-wash");
  let frame = 0;

  function updateBackdrop() {
    if (!scene || !vision || !wash) return;
    const rect = vision.getBoundingClientRect();
    const washProgress = Math.min(
      1,
      Math.max(0, (window.innerHeight - rect.top) / Math.max(1, rect.height)),
    );
    wash.style.opacity = String(washProgress * washProgress * (3 - 2 * washProgress));
  }

  function onScroll() {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(updateBackdrop);
  }

  updateBackdrop();
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });

  const revealItems = document.querySelectorAll("[data-reveal]");
  const cards = document.querySelectorAll("[data-card-reveal]");
  cards.forEach(function (card, index) {
    card.setAttribute("data-stagger", String(index % 3));
  });
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.setAttribute("data-visible", "true");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.14 },
    );
    revealItems.forEach(function (item) { observer.observe(item); });
  } else {
    revealItems.forEach(function (item) { item.setAttribute("data-visible", "true"); });
  }
})();
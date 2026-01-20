/**
 * Gantt color picker – initializes Pickr on .gantt-color-picker elements.
 * Expects: window.Pickr (loaded from CDN), and each .gantt-color-picker to contain
 * - .gantt-color-picker-swatch (Pickr mount) and an input[name="color"] or [data-color-input]
 */
(function () {
  function hexValid(v) {
    if (!v || typeof v !== 'string') return false;
    var s = v.trim();
    return /^#[0-9A-Fa-f]{6}$/.test(s) || /^[0-9A-Fa-f]{6}$/.test(s);
  }

  function toHex(c) {
    if (!c) return '';
    try {
      var s = (c.toHEXA && c.toHEXA().toString()) || (c.toHEX && c.toHEX().toString()) || '';
      if (!s || s.indexOf('#') !== 0) return '';
      return s.length > 7 ? s.slice(0, 7) : s;
    } catch (e) {
      return '';
    }
  }

  function init() {
    if (typeof Pickr === 'undefined') return;
    var roots = document.querySelectorAll('.gantt-color-picker');
    roots.forEach(function (root) {
      if (root.dataset.pickrInit) return;
      var swatch = root.querySelector('.gantt-color-picker-swatch');
      var input = root.querySelector('input[name="color"]') || root.querySelector('input[data-color-input]');
      if (!swatch || !input) return;

      var defaultHex = (input.value || input.placeholder || '#3b82f6').trim();
      if (!defaultHex.startsWith('#')) defaultHex = '#' + defaultHex;
      if (!hexValid(defaultHex)) defaultHex = '#3b82f6';

      var pickr = Pickr.create({
        el: swatch,
        theme: 'classic',
        default: defaultHex,
        components: {
          preview: true,
          opacity: false,
          hue: true,
          interaction: {
            hex: true,
            input: true,
            save: true
          }
        },
        swatches: [
          '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
          '#ec4899', '#06b6d4', '#84cc16', '#64748b', '#0ea5e9'
        ]
      });

      function setInput(val) {
        if (val && hexValid(val)) input.value = val; else input.value = val || '';
      }

      pickr.on('save', function (c) {
        setInput(toHex(c) || '');
        if (pickr && typeof pickr.hide === 'function') pickr.hide();
      });
      pickr.on('change', function (c) {
        setInput(toHex(c));
      });

      input.addEventListener('input', function () {
        var v = (input.value || '').trim();
        if (!v) return;
        if (!v.startsWith('#')) v = '#' + v;
        if (hexValid(v)) try { pickr.setColor(v); } catch (e) {}
      });
      input.addEventListener('change', function () {
        var v = (input.value || '').trim();
        if (!v) return;
        if (!v.startsWith('#')) v = '#' + v;
        if (hexValid(v)) try { pickr.setColor(v); } catch (e) {}
      });

      root.dataset.pickrInit = '1';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

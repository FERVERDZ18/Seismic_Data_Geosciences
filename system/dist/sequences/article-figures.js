/* Fixed scientific figures with entry points to the live sequence explorer. */
(function (global) {
  'use strict';

  const figures = {
    cases: {number:4, path:'figures/figure-4-families.png', width:1950, height:2100},
    diagnostics: {number:3, path:'figures/figure-3-diagnostics.png', width:2130, height:2250},
    scaling: {number:2, path:'figures/figure-2-search.png', width:3285, height:2520}
  };
  const messages = {
    es: {
      eyebrow:'DEL ARTÍCULO AL EXPLORADOR',
      title:'Explora los resultados del artículo',
      intro:'Abre las figuras completas o examina sus casos con los registros originales.',
      fixed:'Figuras fijas del análisis: los filtros del explorador no modifican estas imágenes.',
      figure:'Figura',
      casesTitle:'Tehuantepec y Michoacán',
      casesLead:'Dos casos para comparar las familias operativas de SSN y ComCat: mapa completo, ventana local y cronología.',
      cohort:'México · M reportada ≥4.5 · 2016–2025',
      weightTitle:'Sensibilidad al peso de magnitud',
      weightText:'Los anillos morados señalan incorporaciones al usar el b aparente de cada fuente. W1/W2 identifican testigos de SSN/ComCat, cuando existen.',
      explore2017:'Explorar 2017',
      explore2022:'Explorar 2022',
      exploreHint:'Abre el cálculo con cada catálogo completo, M≥4.5 y w=1. Después puedes cambiar el peso y la extensión de la familia.',
      familyLimit:'Una familia operativa no demuestra que un sismo haya causado otro. Las parejas entre catálogos siguen siendo candidatas.',
      casesAlt:'Figura 4: familias de 2017 y 2022 en mapas completos y locales, con cronologías; anillos morados muestran incorporaciones al cambiar el peso.',
      diagnosticsTag:'OBSERVACIONES Y UMBRALES',
      diagnosticsTitle:'Magnitudes y separación tiempo–distancia',
      diagnosticsText:'Distribuciones de magnitud reportada, cortes del método y diferencias entre parejas candidatas. Los diagnósticos no certifican completitud.',
      diagnosticsAlt:'Figura 3: seis paneles de magnitudes SSN y ComCat, separación tiempo–distancia, Alaska y diferencias de magnitud por tipo.',
      scalingTag:'EVALUACIÓN COMPUTACIONAL',
      scalingTitle:'El costo de buscar en el catálogo',
      scalingText:'Búsqueda indexada frente a la referencia exhaustiva y una partición octree. Tiempos medidos en un equipo; no son velocidades universales.',
      scalingAlt:'Figura 2: escalado de tiempos, fracción de parejas evaluadas, nodos visitados y fases de la búsqueda.',
      open:'Abrir figura completa',
      openLabel:'Abrir la figura {number} completa en una pestaña nueva',
      original:'PNG original · sin recortes',
      figureNote:'Las imágenes conservan los datos, las escalas y las leyendas del artículo.'
    },
    en: {
      eyebrow:'FROM THE ARTICLE TO THE EXPLORER',
      title:'Explore the article results',
      intro:'Open the complete figures or inspect their cases using the original records.',
      fixed:'Fixed analysis figures: explorer filters do not change these images.',
      figure:'Figure',
      casesTitle:'Tehuantepec and Michoacán',
      casesLead:'Two cases for comparing SSN and ComCat operational families: full map, local window and timeline.',
      cohort:'Mexico · reported M≥4.5 · 2016–2025',
      weightTitle:'Sensitivity to magnitude weighting',
      weightText:'Purple rings mark members added using each source’s apparent b. W1/W2 identify SSN/ComCat witnesses, where present.',
      explore2017:'Explore 2017',
      explore2022:'Explore 2022',
      exploreHint:'Opens the calculation with each complete catalogue, M≥4.5 and w=1. Then change the weight and family extent if needed.',
      familyLimit:'An operational family does not prove that one earthquake triggered another. Cross-catalogue pairs remain candidates.',
      casesAlt:'Figure 4: full and local maps of the 2017 and 2022 families with timelines; purple rings show additions under a different magnitude weight.',
      diagnosticsTag:'OBSERVATIONS AND THRESHOLDS',
      diagnosticsTitle:'Magnitudes and time–distance separation',
      diagnosticsText:'Reported-magnitude distributions, method cutoffs and differences between candidate pairs. These diagnostics do not certify completeness.',
      diagnosticsAlt:'Figure 3: six panels showing SSN and ComCat magnitudes, time–distance separation, Alaska and magnitude differences by type.',
      scalingTag:'COMPUTATIONAL EVALUATION',
      scalingTitle:'The cost of searching the catalogue',
      scalingText:'Indexed search against the exhaustive reference and an octree partition. Timings measured on one computer are not universal speeds.',
      scalingAlt:'Figure 2: timing scaling, fraction of pairs evaluated, visited nodes and search phases.',
      open:'Open complete figure',
      openLabel:'Open complete figure {number} in a new tab',
      original:'Original PNG · no cropping',
      figureNote:'Images retain the article’s data, scales and legends.'
    }
  };
  let root = null, language = 'es';

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
  }
  function openFigure(spec, content, className, text) {
    const link = node('a', className, text);
    link.href = spec.path;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.setAttribute('aria-label', content.openLabel.replace('{number}', String(spec.number)));
    return link;
  }
  function preview(spec, content, altKey, className) {
    const link = openFigure(spec, content, className);
    const image = node('img');
    image.src = spec.path;
    image.alt = content[altKey];
    image.width = spec.width;
    image.height = spec.height;
    image.loading = 'lazy';
    image.decoding = 'async';
    link.append(image);
    return link;
  }
  function caseButton(year, content) {
    const button = node('button', 'af-case-button af-case-'+year, content['explore'+year]);
    button.type = 'button';
    button.dataset.articleCase = year;
    button.addEventListener('click', () => root.dispatchEvent(new CustomEvent('article-case', {
      bubbles:true,
      detail:{year}
    })));
    return button;
  }
  function smallCard(key, content) {
    const spec = figures[key], card = node('article', 'af-secondary-card');
    card.append(preview(spec, content, key+'Alt', 'af-secondary-preview'));
    const body = node('div', 'af-secondary-body');
    body.append(node('p', 'af-kicker', content[key+'Tag']),
      node('h3', '', content.figure+' '+spec.number+' · '+content[key+'Title']),
      node('p', 'af-description', content[key+'Text']),
      openFigure(spec, content, 'af-figure-link', content.open+' ↗'));
    card.append(body);
    return card;
  }
  function render() {
    if (!root) return;
    const content = messages[language];
    root.classList.add('af-gallery');
    root.setAttribute('aria-label', content.title);
    root.setAttribute('lang', language);
    const header = node('div', 'af-heading');
    header.append(node('p', 'af-kicker', content.eyebrow), node('h2', '', content.title),
      node('p', 'af-intro', content.intro), node('p', 'af-fixed-note', content.fixed));

    const featured = node('article', 'af-featured');
    featured.append(preview(figures.cases, content, 'casesAlt', 'af-feature-preview'));
    const body = node('div', 'af-feature-body');
    body.append(node('span', 'af-figure-badge', content.figure+' 4'),
      node('p', 'af-cohort', content.cohort), node('h3', '', content.casesTitle),
      node('p', 'af-lead', content.casesLead));
    const weight = node('div', 'af-weight-note');
    weight.append(node('p', 'af-weight-heading', content.weightTitle),
      node('p', 'af-weight-equation', 'w = 1 → w = b'), node('p', '', content.weightText));
    body.append(weight);
    const buttons = node('div', 'af-case-actions');
    buttons.append(caseButton('2017', content), caseButton('2022', content));
    body.append(buttons, node('p', 'af-explore-hint', content.exploreHint),
      node('p', 'af-family-limit', content.familyLimit),
      openFigure(figures.cases, content, 'af-figure-link', content.open+' ↗'),
      node('p', 'af-original-note', content.original));
    featured.append(body);

    const secondary = node('div', 'af-secondary-grid');
    secondary.append(smallCard('diagnostics', content), smallCard('scaling', content));
    root.replaceChildren(header, featured, secondary, node('p', 'af-footer-note', content.figureNote));
  }
  global.ArticleFigures = Object.freeze({
    mount(element, options = {}) {
      if (!element || typeof element.replaceChildren !== 'function') throw new TypeError('A gallery container is required');
      root = element;
      language = options.language === 'en' ? 'en' : 'es';
      render();
    },
    setLanguage(value) {
      language = value === 'en' ? 'en' : 'es';
      render();
    }
  });
})(window);

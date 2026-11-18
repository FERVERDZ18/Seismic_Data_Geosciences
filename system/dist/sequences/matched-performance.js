/* The article's matched, one-thread benchmark and its native figure. */
(function (global) {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const methods = ['reference', 'kd', 'octree'];
  const colors = ['#334155', '#007783', '#ab4e15'];
  const labels = {
    en: {
      title: 'Matched benchmark · one thread for each method',
      scope: '81 retained Python runs on one AMD Ryzen 5 5600G / Windows 11 workstation. Each method used one thread and three fresh processes per input. The browser calculates the summaries from retained measurements.',
      bounds: 'Whiskers show the observed minimum and maximum. Speedup divides the exhaustive median by the index median. Peak working set includes imports, runtime, JIT and warm-up.',
      selection: 'Inspect an input', all: 'All nine inputs', dataset: 'Input', backend: 'Method',
      elapsed: 'Median time [min–max], s', speed: 'Speedup', memory: 'Peak working set [min–max], MiB',
      headings: ['A · Elapsed time (s)', 'B · Ratio of median times', 'C · Peak working set (MiB)', 'D · Index phases at 170,880'],
      x: 'Records in chronological SSN prefix', phaseX: 'Median component time (s)',
      phase: ['Preparation + postprocessing', 'Construction', 'Search'],
      methods: ['Exhaustive', 'KD', 'Octree'], original: 'Show the 81 measured runs',
      historical: 'Earlier four-thread benchmark', sx: 'Download Figure 2 · SVG', json: 'Download measurements · JSON',
      inputs: {ssn_native: 'SSN prefix · M ≥ 3.5', ssn_principal45: 'SSN · M ≥ 4.5', usgs_principal45: 'ComCat · M ≥ 4.5'},
      run: 'Run', seconds: 'Elapsed time (s)', peak: 'Peak working set (MiB)'
    },
    es: {
      title: 'Comparación emparejada · un hilo por método',
      scope: '81 ejecuciones conservadas de Python en un equipo AMD Ryzen 5 5600G / Windows 11. Cada método usó un hilo y tres procesos nuevos por entrada. El navegador calcula los resúmenes a partir de las mediciones conservadas.',
      bounds: 'Las barras muestran el mínimo y máximo observados. La aceleración divide la mediana exhaustiva por la del índice. La memoria pico del proceso incluye importaciones, entorno de ejecución, JIT y calentamiento.',
      selection: 'Inspeccionar una entrada', all: 'Las nueve entradas', dataset: 'Entrada', backend: 'Método',
      elapsed: 'Mediana [mín.–máx.], s', speed: 'Aceleración', memory: 'Memoria pico [mín.–máx.], MiB',
      headings: ['A · Tiempo transcurrido (s)', 'B · Cociente de medianas', 'C · Memoria pico (MiB)', 'D · Fases del índice con 170 880'],
      x: 'Registros en el prefijo cronológico SSN', phaseX: 'Mediana de tiempo por fase (s)',
      phase: ['Preparación y posproceso', 'Construcción', 'Búsqueda'],
      methods: ['Exhaustiva', 'KD', 'Octree'], original: 'Mostrar las 81 ejecuciones medidas',
      historical: 'Comparación anterior de cuatro hilos', sx: 'Descargar Figura 2 · SVG', json: 'Descargar mediciones · JSON',
      inputs: {ssn_native: 'Prefijo SSN · M ≥ 3.5', ssn_principal45: 'SSN · M ≥ 4.5', usgs_principal45: 'ComCat · M ≥ 4.5'},
      run: 'Ejecución', seconds: 'Tiempo transcurrido (s)', peak: 'Memoria pico (MiB)'
    }
  };
  const inputKey = row => row.dataset + ':' + row.n;
  const memory = bytes => bytes / 1048576;
  const phaseColors = ['#7891a7', '#7054a1', '#007783'];
  const timingFields = ['preparation_seconds', 'tree_seconds', 'kernel_seconds', 'postprocess_seconds', 'total_seconds'];
  const svgNode = (tag, attrs = {}, text = '') => {
    const element = document.createElementNS(NS, tag);
    for (const [name, value] of Object.entries(attrs)) element.setAttribute(name, String(value));
    if (text) element.textContent = text;
    return element;
  };
  function summary(data) {
    if (data.schema !== 'seismic-matched-search-performance/1' || data.threads !== 1 || data.repetitions !== 3 || data.measurements.length !== 81) {
      throw new Error('Invalid matched benchmark asset');
    }
    const seen = new Set();
    const groups = new Map();
    for (const row of data.measurements) {
      const id = `${inputKey(row)}:${row.backend}:${row.rep}`;
      if (seen.has(id) || !methods.includes(row.backend) || !Number.isInteger(row.n) || row.n < 2 || ![0, 1, 2].includes(row.rep) ||
          timingFields.some(field => !Number.isFinite(row[field]) || row[field] < 0) || row.total_seconds <= 0 ||
          !Number.isSafeInteger(row.peak_working_set_bytes) || row.peak_working_set_bytes <= 0) {
        throw new Error('Invalid or duplicate matched benchmark run');
      }
      seen.add(id);
      if (!groups.has(inputKey(row))) groups.set(inputKey(row), []);
      groups.get(inputKey(row)).push(row);
    }
    if (groups.size !== 9) throw new Error('Invalid matched benchmark input count');
    return Array.from(groups.values(), runs => {
      const results = methods.map(backend => {
        const subset = runs.filter(row => row.backend === backend);
        if (subset.length !== 3) throw new Error('Incomplete matched benchmark group');
        const times = subset.map(row => row.total_seconds);
        const peaks = subset.map(row => memory(row.peak_working_set_bytes));
        return {
          dataset: subset[0].dataset, n: subset[0].n, backend,
          median: PerformanceMath.median(times), range: [Math.min(...times), Math.max(...times)],
          peak: PerformanceMath.median(peaks), peakRange: [Math.min(...peaks), Math.max(...peaks)],
          phases: [PerformanceMath.median(subset.map(row => row.preparation_seconds)) + PerformanceMath.median(subset.map(row => row.postprocess_seconds)),
            PerformanceMath.median(subset.map(row => row.tree_seconds)), PerformanceMath.median(subset.map(row => row.kernel_seconds))]
        };
      });
      return results.map(row => ({...row, ratio: results[0].median / row.median}));
    }).flat();
  }
  function figure(rows, word, format, inspect) {
    const chart = svgNode('svg', {xmlns: NS, viewBox: '0 0 900 593', role: 'img', 'aria-label': word.title,
      'font-family': 'Arial, sans-serif', 'font-size': 17, fill: '#243a4a', 'data-matched-figure': '2'});
    chart.append(svgNode('rect', {width: 900, height: 593, fill: '#fff'}), svgNode('title', {}, word.title));
    const native = rows.filter(row => row.dataset === 'ssn_native');
    const sizes = [...new Set(native.map(row => row.n))].sort((a, b) => a - b);
    const maxN = sizes.at(-1);
    const segment = (x1, y1, x2, y2, stroke, width = 1) => svgNode('line', {x1, y1, x2, y2, stroke, 'stroke-width': width});
    const text = (x, y, value, anchor = 'start', attrs = {}) => svgNode('text', {x, y, 'text-anchor': anchor, ...attrs}, value);
    const lineSpecs = [
      {key: 'median', range: 'range', ticks: [.01, .1, 1, 10, 100, 1000], log: true, digits: 3},
      {key: 'ratio', ticks: [1, 10, 30, 60, 90], log: false, digits: 2},
      {key: 'peak', range: 'peakRange', ticks: [160, 185, 210, 235, 260, 285], log: false, digits: 2}
    ];
    for (const [index, spec] of lineSpecs.entries()) {
      const panel = svgNode('g', {transform: `translate(${index === 1 ? 454 : 0} ${index === 2 ? 278 : 0})`});
      const bounds = {left: 58, right: 414, top: 42, bottom: 217};
      const transform = spec.log ? Math.log10 : value => value;
      const start = transform(spec.ticks[0]);
      const span = transform(spec.ticks.at(-1)) - start;
      const x = n => bounds.left + Math.log(n / sizes[0]) / Math.log(maxN / sizes[0]) * (bounds.right - bounds.left);
      const y = value => bounds.bottom - (transform(value) - start) / span * (bounds.bottom - bounds.top);
      panel.append(text(13, 27, word.headings[index], 'start', {'font-size': 20, 'font-weight': 'bold'}));
      for (const value of spec.ticks) {
        const py = y(value);
        panel.append(segment(bounds.left, py, bounds.right, py, '#dce6eb'), text(bounds.left - 7, py + 6, format(value, 2), 'end'));
      }
      for (const n of sizes) {
        const px = x(n);
        panel.append(segment(px, bounds.top, px, bounds.bottom, '#edf2f4'),
          text(px, bounds.bottom + 23, format(n / 1000, 0) + 'k', 'middle', {'font-size': 16}));
      }
      panel.append(text((bounds.left + bounds.right) / 2, 263, word.x, 'middle'));
      for (const [methodIndex, backend] of methods.entries()) {
        const points = native.filter(row => row.backend === backend);
        const stroke = colors[methodIndex];
        panel.append(svgNode('polyline', {points: points.map(row => `${x(row.n)},${y(row[spec.key])}`).join(' '), fill: 'none', stroke,
          'stroke-width': 2.5, ...(methodIndex === 2 ? {'stroke-dasharray': '7 4'} : {})}));
        for (const row of points) {
          const px = x(row.n);
          if (spec.range) panel.append(segment(px, y(row[spec.range][0]), px, y(row[spec.range][1]), stroke, 2.4));
          const descriptor = `${word.methods[methodIndex]}, ${format(row.n, 0)}: ${format(row[spec.key], spec.digits)}`;
          const point = svgNode('circle', {cx: px, cy: y(row[spec.key]), r: 4.5, stroke: '#fff', 'stroke-width': 1, fill: stroke,
            tabindex: 0, role: 'button', 'aria-label': descriptor});
          point.append(svgNode('title', {}, descriptor));
          point.addEventListener('click', () => inspect(inputKey(row)));
          point.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); inspect(inputKey(row)); } });
          panel.append(point);
        }
      }
      chart.append(panel);
    }
    const phases = svgNode('g', {transform: 'translate(454 278)'});
    phases.append(text(13, 27, word.headings[3], 'start', {'font-size': 20, 'font-weight': 'bold'}));
    const phaseX = value => 73 + value * 47;
    for (let tick = 0; tick <= 7; tick++) {
      const px = phaseX(tick);
      phases.append(segment(px, 55, px, 175, '#dce6eb'), text(px, 199, String(tick), 'middle'));
    }
    for (const [index, row] of native.filter(row => row.n === maxN && row.backend !== 'reference').entries()) {
      const py = 74 + index * 57;
      let sum = 0;
      phases.append(text(8, py + 20, word.methods[methods.indexOf(row.backend)]));
      row.phases.forEach((seconds, phase) => {
        const block = svgNode('rect', {x: phaseX(sum), y: py, width: seconds * 47, height: 29, fill: phaseColors[phase]});
        block.append(svgNode('title', {}, `${word.phase[phase]}: ${format(seconds, 4)} s`));
        phases.append(block);
        sum += seconds;
      });
    }
    phases.append(text(238, 220, word.phaseX, 'middle'));
    for (const [i, xy] of [[243, 11], [243, 285], [267, 11]].entries()) {
      const [py, px] = xy;
      phases.append(svgNode('rect', {x: px, y: py - 12, width: 16, height: 12, fill: phaseColors[i]}),
        text(px + 21, py, word.phase[i], 'start', {'font-size': 15}));
    }
    chart.append(phases);
    for (const [index, label] of word.methods.entries()) {
      const x = 212 + index * 165;
      chart.append(segment(x, 575, x + 28, 575, colors[index], 4), text(x + 35, 581, label));
    }
    return chart;
  }
  const node = (tag, content = '') => {
    const element = document.createElement(tag);
    if (content) element.textContent = content;
    return element;
  };
  function table(headers, rows) {
    const wrap = node('div');
    wrap.className = 'np-table-wrap';
    const table = node('table');
    table.className = 'np-table';
    const head = node('thead');
    const headings = node('tr');
    for (const header of headers) {
      const th = node('th', header);
      th.scope = 'col';
      headings.append(th);
    }
    head.append(headings);
    const body = node('tbody');
    for (const row of rows) {
      const tr = node('tr');
      for (const value of row) tr.append(node('td', value));
      body.append(tr);
    }
    table.append(head, body);
    wrap.append(table);
    return wrap;
  }
  function render(root, data, {lang, onHistorical, download}) {
    const word = labels[lang];
    const rows = summary(data);
    const format = (value, digits = 3) => value.toLocaleString(lang, {maximumFractionDigits: digits});
    const label = row => `${word.inputs[row.dataset]} · N=${format(row.n, 0)}`;
    const formatRange = range => `${format(range[0])}–${format(range[1])}`;
    const heading = node('div');
    heading.className = 'np-heading';
    heading.append(node('h2', word.title), node('p', word.scope), node('p', word.bounds));
    const controls = node('div');
    controls.className = 'np-controls';
    const wrapper = node('label', word.selection);
    wrapper.className = 'np-control';
    const select = node('select');
    const all = node('option', word.all);
    all.value = '';
    select.append(all);
    for (const row of rows.filter(row => row.backend === 'reference')) {
      const option = node('option', label(row));
      option.value = inputKey(row);
      select.append(option);
    }
    wrapper.append(select);
    const historical = node('button', word.historical);
    historical.type = 'button';
    historical.addEventListener('click', onHistorical);
    controls.append(wrapper, historical);
    const panel = node('article');
    panel.className = 'np-chart np-matched';
    const inspected = node('section');
    inspected.className = 'np-summary';
    inspected.setAttribute('aria-live', 'polite');
    function update() {
      const selected = rows.filter(row => !select.value || select.value === inputKey(row));
      inspected.replaceChildren(table([word.dataset, word.backend, word.elapsed, word.speed, word.memory], selected.map(row => [
        label(row), word.methods[methods.indexOf(row.backend)], `${format(row.median)} [${formatRange(row.range)}]`,
        `${format(row.ratio, 2)}×`, `${format(row.peak, 2)} [${formatRange(row.peakRange)}]`
      ])));
    }
    select.addEventListener('change', update);
    const plot = figure(rows, word, format, key => { select.value = key; update(); });
    panel.append(plot);
    const actions = node('div');
    actions.className = 'np-actions';
    const svg = node('button', word.sx);
    svg.type = 'button';
    svg.addEventListener('click', () => {
      const copy = plot.cloneNode(true);
      copy.querySelectorAll('[tabindex]').forEach(point => { point.removeAttribute('tabindex'); point.removeAttribute('role'); });
      download('figure-2-matched-one-thread.svg', new XMLSerializer().serializeToString(copy), 'image/svg+xml');
    });
    const json = node('button', word.json);
    json.type = 'button';
    json.addEventListener('click', () => download('matched-one-thread-measurements.json', JSON.stringify(data, null, 2), 'application/json'));
    actions.append(svg, json);
    const raw = node('details');
    raw.className = 'np-runs';
    raw.append(node('summary', word.original), table([word.dataset, word.backend, word.run, word.seconds, word.peak],
      data.measurements.map(row => [label(row), word.methods[methods.indexOf(row.backend)], String(row.rep + 1), String(row.total_seconds), format(memory(row.peak_working_set_bytes), 2)])));
    root.replaceChildren(heading, controls, actions, panel, inspected, raw);
    update();
  }
  global.MatchedPerformance = Object.freeze({render});
})(window);

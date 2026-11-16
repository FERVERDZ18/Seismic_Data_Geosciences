(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SeismicCatalogComposition = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const combinedId = 'all-catalogs';
  const provenanceFields = Object.freeze(['source_event_id', 'catalog_id', 'data_provider', 'source_snapshot',
    'source_identifier_kind', 'depth_unit', 'country_id', 'shared_event_id', 'duplicate_group']);
  const copy = value => JSON.parse(JSON.stringify(value));
  const fail = reason => {throw new Error('Invalid catalogue composition: ' + reason);};

  function depthUnit(catalog, manifest) {
    if (catalog.depth_unit_status === 'not_documented_in_source' || manifest.depth_unit_status === 'not_documented_in_source') return null;
    return catalog.depth_unit === 'km' || manifest.depth_unit === 'km' || catalog.provider === 'usgs' ? 'km' : null;
  }

  function identifierKind(catalog, manifest) {
    return catalog.identifier_kind || manifest.identifier_kind || (catalog.provider === 'usgs' ? 'source_event_id' : 'unknown');
  }

  function validatePack(pack, seenCatalogs) {
    if (!pack || typeof pack !== 'object') fail('pack must be an object');
    const {catalog, fields, events, manifest, hashes} = pack;
    if (!catalog || !/^[A-Za-z0-9_-]+$/.test(catalog.id || '') || catalog.id === combinedId) fail('catalogue identifier');
    if (seenCatalogs.has(catalog.id)) fail('repeated catalogue ' + catalog.id);
    seenCatalogs.add(catalog.id);
    if (typeof catalog.provider !== 'string' || !catalog.provider || catalog.provider === 'all') fail('provider');
    if (!Array.isArray(fields) || !fields.includes('id') || fields.some(f => typeof f !== 'string' || !f) || new Set(fields).size !== fields.length) fail('fields');
    if (!Array.isArray(events) || !manifest || typeof manifest !== 'object' || !hashes || typeof hashes !== 'object') fail('events, manifest or hashes');
    if (!Array.isArray(catalog.years) || catalog.years.length !== 2 || !catalog.years.every(Number.isFinite) || catalog.years[0] > catalog.years[1]) fail('year bounds');
    if (!Number.isFinite(catalog.minimum_magnitude)) fail('minimum magnitude');
    if (!Array.isArray(catalog.bounds) || catalog.bounds.length !== 2 || catalog.bounds.some(p => !Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite))) fail('geographic bounds');
    if (catalog.bounds[0][0] > catalog.bounds[1][0] || catalog.bounds[0][1] > catalog.bounds[1][1]) fail('inverted geographic bounds');
    const seen = new Set();
    for (const event of events) {
      if (!event || typeof event !== 'object' || typeof event.id !== 'string' || !event.id || event.id.includes('~')) fail('record identifier');
      if (seen.has(event.id)) fail('repeated record identifier within ' + catalog.id);
      seen.add(event.id);
      // Source packages must not silently override the composite provenance columns.
      for (const key of provenanceFields) {
        if (key !== 'country_id' && Object.hasOwn(event, key)) fail('reserved provenance field ' + key);
      }
    }
  }

  function combine(packs) {
    if (!Array.isArray(packs) || !packs.length) fail('at least one source package is required');
    const seenCatalogs = new Set();
    for (const pack of packs) validatePack(pack, seenCatalogs);
    const fields = [...new Set(packs.flatMap(pack => pack.fields))];
    for (const key of provenanceFields) if (!fields.includes(key)) fields.push(key);
    // Only an identical ComCat identifier in separate USGS packages is flagged.
    // Spatial/temporal proximity across distributors never establishes identity.
    const usgsIds = new Map();
    let usgsRows = 0;
    for (const {catalog, events} of packs) if (catalog.provider === 'usgs') {
      usgsRows += events.length;
      for (const event of events) {
        if (!usgsIds.has(event.id)) usgsIds.set(event.id, new Set());
        usgsIds.get(event.id).add(catalog.id);
      }
    }
    const shared = new Set([...usgsIds].filter(([, catalogs]) => catalogs.size > 1).map(([id]) => id));
    const events = [];
    for (const {catalog, fields:sourceFields, events:rows, manifest} of packs) {
      const snapshot = catalog.snapshot ?? manifest.snapshot_commit ?? null;
      const kind = identifierKind(catalog, manifest), unit = depthUnit(catalog, manifest);
      const sourceColumns = new Set(sourceFields);
      for (const row of rows) {
        const event = {};
        for (const key of fields) event[key] = sourceColumns.has(key) || key === 'country_id' ? row[key] ?? null : null;
        // Retain computed client fields (e.g. UTC year) without adding them to CSV.
        for (const [key, value] of Object.entries(row)) if (!Object.hasOwn(event, key)) event[key] = value;
        const sharedId = catalog.provider === 'usgs' && shared.has(row.id);
        Object.assign(event, {id: catalog.id + '~' + row.id, source_event_id:row.id, catalog_id:catalog.id,
          data_provider:catalog.provider, source_snapshot:snapshot, source_identifier_kind:kind,
          depth_unit:unit, shared_event_id:sharedId, duplicate_group:sharedId ? 'usgs:' + row.id : null,
          _catalog_id:catalog.id});
        events.push(event);
      }
    }
    const bounds = [[Math.min(...packs.map(p => p.catalog.bounds[0][0])), Math.min(...packs.map(p => p.catalog.bounds[0][1]))],
      [Math.max(...packs.map(p => p.catalog.bounds[1][0])), Math.max(...packs.map(p => p.catalog.bounds[1][1]))]];
    // Bounds use the same western antimeridian display convention as the map.
    // Original event coordinates are never shifted by this composition.
    bounds[0][1] = Math.max(-210, bounds[0][1]);bounds[1][1] = Math.min(180, bounds[1][1]);
    const catalog = {id:combinedId, provider:'all', provider_name:'Multiple catalogue distributors',
      label:{es:'Todos los catálogos · vista conjunta', en:'All catalogues · combined view'},
      years:[Math.min(...packs.map(p => p.catalog.years[0])), Math.max(...packs.map(p => p.catalog.years[1]))],
      minimum_magnitude:Math.min(...packs.map(p => p.catalog.minimum_magnitude)), bounds,
      role:'combined_exploration', event_count:events.length, record_count:events.length, count_unit:'records',
      identifier_kind:'catalogue_qualified_record_key', depth_unit:null,
      depth_unit_status:'per_record', events_bytes:packs.reduce((n,p) => n + (p.catalog.events_bytes || 0),0)};
    const inputs = packs.map(({catalog, fields, manifest, hashes}) => ({catalog:copy(catalog), fields:[...fields], manifest:copy(manifest), hashes:copy(hashes)}));
    const hashes = {inputs:Object.fromEntries(inputs.map(p => [p.catalog.id, copy(p.hashes)]))};
    const stats = {total_rows:events.length, usgs_rows:usgsRows, usgs_unique_event_ids:usgsIds.size,
      usgs_shared_event_ids:shared.size, usgs_extra_rows:usgsRows - usgsIds.size};
    const manifest = {schema_version:1, composition_schema:'seismic-catalogue-composition/1', files:[],
      identifier_kind:'catalogue_qualified_record_key', depth_unit:null, depth_unit_status:'per_record',
      packaged_records:events.length, inputs, stats,
      composition_rule:'Preserve every packaged row in catalogue input order; no deduplication or cross-provider event matching.',
      overlap_rule:'shared_event_id and duplicate_group flag only exact source identifiers present in more than one USGS catalogue. No cross-provider identity is inferred.',
      identifier_rule:'id qualifies the original packaged key by catalogue. source_event_id retains that packaged key; source_identifier_kind distinguishes official event IDs from derived row keys.',
      limits:['Counts describe source records, not distinct earthquakes or independent observations.',
        'Country labels, when present, describe a separate geographic overlay and are not inferred from the distributor.',
        'Unknown source fields remain null; magnitude scales, clocks and status vocabularies are not harmonized.',
        'Source rights, hashes, files, coverage and field semantics remain separate in inputs.']};
    return {events, fields, manifest, catalog, hashes, inputs, stats};
  }
  const exactSchema = 'seismic-exact-source-evidence/1';
  const exactFields = Object.freeze(['exact_group_key','exact_member_count','exact_member_keys','exact_group_rule']);
  const usgsSourceFields = ['time','latitude','longitude','depth','mag','magType','nst','gap','dmin','rms','net','id',
    'updated','place','type','horizontalError','depthError','magError','magNst','status','locationSource','magSource'];
  const nrcanSourceFields = ['date','latitude','longitude','depth','magnitude','magnitude type','place','',''];
  const exactRules = {
    'usgs-comcat':{provider:'usgs',rule:'same_provider_id_and_all_22_original_cells',fields:usgsSourceFields},
    'nrcan-earthquakes-canada':{provider:'nrcan',rule:'all_9_original_cells_no_source_event_id',fields:nrcanSourceFields}
  };
  const exactFail = reason => {throw new Error('Invalid exact-record grouping: ' + reason);};
  const hexDigest = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
  const equal = (a,b) => a === b || (a !== undefined && b !== undefined && JSON.stringify(a) === JSON.stringify(b));

  // Synchronous SHA-256 is applied only to the small original-cell proofs, never
  // to 287k normalized browser rows. The loader separately verifies asset bytes.
  function proofHash(text) {
    const input = new TextEncoder().encode(text), length = Math.ceil((input.length + 9) / 64) * 64;
    const bytes = new Uint8Array(length);bytes.set(input);bytes[input.length] = 128;
    const view = new DataView(bytes.buffer);view.setUint32(length - 4, input.length * 8);
    const initial = [], constants = [];
    for (let n=2; constants.length<64; n++) {
      let prime = true;for (let d=2; d*d<=n; d++) if (n%d===0) {prime=false;break;}
      if (!prime) continue;
      if (initial.length<8) initial.push((Math.sqrt(n)%1 * 4294967296)|0);
      constants.push((Math.cbrt(n)%1 * 4294967296)|0);
    }
    const rotate = (n,k) => (n>>>k)|(n<<(32-k)), words = new Int32Array(64), hash = initial;
    for (let offset=0; offset<length; offset+=64) {
      for (let i=0;i<16;i++) words[i]=view.getInt32(offset+i*4);
      for (let i=16;i<64;i++) {
        const a=words[i-15],b=words[i-2];
        words[i]=(words[i-16]+(rotate(a,7)^rotate(a,18)^(a>>>3))+words[i-7]+(rotate(b,17)^rotate(b,19)^(b>>>10)))|0;
      }
      let [a,b,c,d,e,f,g,h]=hash;
      for (let i=0;i<64;i++) {
        const t1=(h+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+constants[i]+words[i])|0;
        const t2=((rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c)))|0;
        h=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=a;a=(t1+t2)|0;
      }
      [a,b,c,d,e,f,g,h].forEach((value,i)=>{hash[i]=(hash[i]+value)|0;});
    }
    return hash.map(value=>(value>>>0).toString(16).padStart(8,'0')).join('');
  }

  function sourceNumber(cell) {
    if (cell === '') return null;
    if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(cell.trim()) || !Number.isFinite(Number(cell))) exactFail('non-numeric source measurement');
    return Number(cell);
  }

  function checkOriginalCells(group, member, row) {
    const cells=group.source_cells;
    let expected;
    if (group.provider_namespace==='usgs-comcat') {
      const original=Object.fromEntries(usgsSourceFields.map((key,i)=>[key,cells[i]]));
      if (original.id!==member.source_event_id || original.type!=='earthquake') exactFail('USGS source identity/type');
      const numeric=new Set(['latitude','longitude','depth','mag','horizontalError','depthError','magError']);
      expected=Object.fromEntries(Object.entries(original).filter(([key])=>key!=='id' && Object.hasOwn(row,key)).map(([key,value])=>[key,numeric.has(key)?sourceNumber(value):value]));
      if (row.event_type!==null && row.event_type!==undefined) expected.event_type=original.type;
    } else {
      const time=cells[0].replace(/\+0000$/,'Z');
      if (!Number.isFinite(Date.parse(time)) || !/\+0000$/.test(cells[0])) exactFail('NRCan UTC source date');
      expected={time,latitude:sourceNumber(cells[1]),longitude:sourceNumber(cells[2]),depth:null,mag:sourceNumber(cells[4]),
        magType:cells[5],raw_depth:cells[3],place:cells.slice(6).filter(Boolean).join(', ')};
      const originalHash=proofHash(JSON.stringify(cells));
      if (!new RegExp('^nrcan-local-'+originalHash.slice(0,24)+'-[1-9][0-9]*$').test(member.source_event_id)) exactFail('NRCan derived source key');
      sourceNumber(cells[3]); // Unknown depth units stay null; source tokens must still be finite.
    }
    for (const [key,value] of Object.entries(expected)) if (!equal(row[key],value)) exactFail('original/package disagreement '+member.record_key+' '+key);
    if (row.file!==member.source_file) exactFail('source filename');
  }

  function checkedComposition(packs, supplied) {
    const composition=supplied || combine(packs), expected=new Map();
    for (const pack of packs) {
      const bound=composition.hashes?.inputs?.[pack.catalog.id];
      if (!bound || bound.events!==pack.hashes.events || bound.manifest!==pack.hashes.manifest) exactFail('composition input hashes');
      for (const row of pack.events) expected.set(pack.catalog.id+'~'+row.id,{pack,row});
    }
    if (composition.catalog?.id!==combinedId || !Array.isArray(composition.events) || composition.events.length!==expected.size
        || !Array.isArray(composition.inputs) || composition.inputs.length!==packs.length) exactFail('composition scope');
    const expectedFields=new Set([...packs.flatMap(pack=>pack.fields),...provenanceFields]);
    if (!Array.isArray(composition.fields) || composition.fields.length!==expectedFields.size
        || composition.fields.some(key=>!expectedFields.has(key)) || new Set(composition.fields).size!==expectedFields.size
        || Object.keys(composition.hashes.inputs).length!==packs.length) exactFail('composition columns/hashes');
    const inputs=new Set(composition.inputs.map(input=>input.catalog?.id));
    if (inputs.size!==packs.length || packs.some(pack=>!inputs.has(pack.catalog.id))) exactFail('composition catalogues');
    for (const pack of packs) {
      const input=composition.inputs.find(item=>item.catalog.id===pack.catalog.id);
      if (!equal(input.catalog,pack.catalog) || !equal(input.fields,pack.fields)
          || !equal(input.manifest,pack.manifest) || !equal(input.hashes,pack.hashes)) exactFail('composition input metadata');
    }
    const byKey=new Map();
    for (const event of composition.events) {
      const match=expected.get(event.id);
      if (!match || byKey.has(event.id)) exactFail('composition record identity');
      const {pack,row}=match;
      if (event.source_event_id!==row.id || event.catalog_id!==pack.catalog.id || event._catalog_id!==pack.catalog.id
          || event.data_provider!==pack.catalog.provider || event.source_identifier_kind!==identifierKind(pack.catalog,pack.manifest)
          || event.depth_unit!==depthUnit(pack.catalog,pack.manifest)
          || event.source_snapshot!==(pack.catalog.snapshot??pack.manifest.snapshot_commit??null)) exactFail('composition provenance');
      for (const [key,value] of Object.entries(row)) if (key!=='id' && !equal(event[key],value??null)) exactFail('composition changed source field '+key);
      for (const key of exactFields) if (Object.hasOwn(event,key)) exactFail('composition contains grouping annotations');
      byKey.set(event.id,event);
    }
    return {composition,byKey};
  }

  /** Exact source copies only. Missing/mismatched full-cell evidence fails closed.
   * Supplied composition is reused after validation. Singletons share untouched
   * composite row references; only multi-copy representatives are shallow clones.
   */
  function groupExactRecords(packs, options={}) {
    if (!Array.isArray(packs) || !packs.length) exactFail('source packages required');
    const seenCatalogs=new Set();for (const pack of packs) validatePack(pack,seenCatalogs);
    const evidence=options.evidence;
    if (!evidence || evidence.schema!==exactSchema || !evidence.inputs || !Array.isArray(evidence.source_files) || !Array.isArray(evidence.groups)) exactFail('full original-cell evidence required');
    const packById=new Map(packs.map(pack=>[pack.catalog.id,pack])), files=new Map();
    for (const pack of packs) {
      const binding=evidence.inputs[pack.catalog.id];
      if (!binding || !hexDigest(pack.hashes.events) || !hexDigest(pack.hashes.manifest)
          || binding.events_sha256!==pack.hashes.events || binding.manifest_sha256!==pack.hashes.manifest
          || binding.provider!==pack.catalog.provider || binding.record_count!==pack.events.length) exactFail('evidence/package binding '+pack.catalog.id);
      if (!Array.isArray(pack.manifest.files) || (pack.events.length && !pack.manifest.files.length)) exactFail('original-file inventory');
      for (const file of pack.manifest.files) files.set(pack.catalog.id+'\n'+file.path,file.sha256);
    }
    const provenFiles=new Map();
    for (const file of evidence.source_files) {
      const key=file.catalog_id+'\n'+file.path;
      if (provenFiles.has(key) || !hexDigest(file.sha256) || !Number.isInteger(file.bytes) || file.bytes<0) exactFail('source-file proof');
      provenFiles.set(key,file.sha256);
    }
    for (const [key,digest] of files) if (!hexDigest(digest) || provenFiles.get(key)!==digest) exactFail('original-file binding');
    const {composition,byKey}=checkedComposition(packs,options.composition), membership=Object.create(null);
    for (const key of byKey.keys()) membership[key]='source-record:'+key;
    const groups=[], grouped=new Set(), replacements=new Map(), seenGroups=new Set(), seenMembers=new Set();
    for (const proof of evidence.groups) {
      const rule=exactRules[proof.provider_namespace];
      if (!rule || proof.rule!==rule.rule || !equal(proof.source_fields,rule.fields)
          || !Array.isArray(proof.source_cells) || proof.source_cells.length!==rule.fields.length
          || proof.source_cells.some(cell=>typeof cell!=='string') || !hexDigest(proof.signature)
          || proofHash(JSON.stringify([proof.provider_namespace,proof.source_fields,proof.source_cells]))!==proof.signature
          || proof.group_key!=='exact:'+proof.provider_namespace+':'+proof.signature || seenGroups.has(proof.group_key)
          || !Array.isArray(proof.members) || proof.members.length<2) exactFail('exact source-cell proof');
      seenGroups.add(proof.group_key);
      const members=[];
      for (const member of proof.members) {
        const input=evidence.inputs[member.catalog_id],fileKey=member.catalog_id+'\n'+member.source_file;
        if (!input || input.provider!==rule.provider || member.record_key!==member.catalog_id+'~'+member.source_event_id
            || member.signature!==proof.signature || provenFiles.get(fileKey)!==member.source_file_sha256
            || !Number.isInteger(member.source_row) || member.source_row<2 || seenMembers.has(member.record_key)) exactFail('member provenance');
        seenMembers.add(member.record_key);
        if (!packById.has(member.catalog_id)) continue;
        const row=byKey.get(member.record_key);
        if (!row || files.get(fileKey)!==member.source_file_sha256 || !hexDigest(member.source_file_sha256)) exactFail('missing proven member/source file');
        checkOriginalCells(proof,member,row);members.push(member);
      }
      if (members.length<2) continue;
      // Raw-identical positions must not acquire inconsistent filtering overlays.
      const first=byKey.get(members[0].record_key);
      for (const member of members) for (const key of ['country_id','admin1_id']) {
        if (!equal(byKey.get(member.record_key)[key],first[key])) exactFail('inconsistent geographic overlay '+key);
      }
      const priority=id=>id==='usgs-na-2020-2025'?0:id==='usgs-mx-historical'?1:2;
      members.sort((a,b)=>priority(a.catalog_id)-priority(b.catalog_id)||(a.record_key<b.record_key?-1:a.record_key>b.record_key?1:0));
      const memberKeys=members.map(member=>member.record_key),representativeKey=memberKeys[0];
      const group={group_key:proof.group_key,rule:proof.rule,provider_namespace:proof.provider_namespace,signature:proof.signature,
        representative_key:representativeKey,member_keys:memberKeys,members:members.map(member=>({...member})),exact_member_count:members.length};
      groups.push(group);
      for (const key of memberKeys) {membership[key]=proof.group_key;grouped.add(key);}
      replacements.set(representativeKey,{...byKey.get(representativeKey),exact_group_key:proof.group_key,
        exact_member_count:members.length,exact_member_keys:memberKeys,exact_group_rule:proof.rule});
    }
    groups.sort((a,b)=>a.group_key<b.group_key?-1:a.group_key>b.group_key?1:0);
    const events=[];
    for (const [key,row] of byKey) if (!grouped.has(key)) events.push(row);else if (replacements.has(key)) events.push(replacements.get(key));
    events.sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0);
    const stats={input_records:composition.events.length,group_count:events.length,
      collapsed_records:composition.events.length-events.length,multi_member_groups:groups.length,count_unit:'exact_source_record_groups'};
    return {schema:'seismic-exact-record-groups/1',events,representatives:events,groups,membership,
      member_records:composition.events,stats,evidence,composition};
  }

  function compose(packs, options={}) {
    if (!options.mode || options.mode==='records') return combine(packs);
    if (options.mode==='exact') return groupExactRecords(packs,options);
    exactFail('unknown composition mode');
  }
  return {combinedId, provenanceFields, combine, exactFields, groupExactRecords, compose};
});

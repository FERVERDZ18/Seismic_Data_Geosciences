/* Presentation analysis over live nearest-parent results; no stored classifications. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.CaseAnalysis=api;})(typeof window!=='undefined'?window:this,function(){
  'use strict';
  const DAY=86400000,RADIUS_KM=6371.0088;
  function distance(a,b){const rad=Math.PI/180,p=(Number(b.latitude)-Number(a.latitude))*rad,l=(Number(b.longitude)-Number(a.longitude))*rad,h=Math.sin(p/2)**2+Math.cos(Number(a.latitude)*rad)*Math.cos(Number(b.latitude)*rad)*Math.sin(l/2)**2;return 2*RADIUS_KM*Math.asin(Math.sqrt(Math.max(0,Math.min(1,h))));}
  function anchor(caseDefinition){return {record_id:caseDefinition.anchor_usgs_record_id,time_utc:caseDefinition.anchor_time_utc,latitude:Number(caseDefinition.anchor_latitude),longitude:Number(caseDefinition.anchor_longitude),magnitude:Number(caseDefinition.anchor_reported_magnitude)};}
  function inside(row,a,view){const days=(Date.parse(row.time_utc)-Date.parse(a.time_utc))/DAY;return days>=-Number(view.before)&&days<=Number(view.after)&&distance(row,a)<=Number(view.radius);}
  function span(rows,indices){const times=indices.map(i=>Date.parse(rows[i].time_utc)).sort((a,b)=>a-b);let maximumGapDays=0;for(let i=1;i<times.length;i++)maximumGapDays=Math.max(maximumGapDays,(times[i]-times[i-1])/DAY);return {span_days:times.length?(times.at(-1)-times[0])/DAY:0,maximum_gap_days:maximumGapDays};}
  function sourceAnalysis(source,definition,classified,view){
    const fixed=classified.fixed,weighted=classified.reported_b,rows=fixed.rows,a=anchor(definition);
    if(rows.length!==weighted.rows.length)throw new Error('Weight comparison requires identical members');
    for(const value of [fixed.result,weighted.result])if(['ids','parent','component','roles','log_eta'].some(key=>!value[key]||value[key].length!==rows.length)||!Number.isFinite(value.metadata?.threshold_log10))throw new Error('Incomplete source classification');
    const index=new Map();
    rows.forEach((r,i)=>{if(r.record_id!==weighted.rows[i].record_id||r.record_id!==fixed.result.ids[i]||r.record_id!==weighted.result.ids[i])throw new Error('Classifications do not match ordered source records');index.set(r.record_id,i);});
    const anchorId=definition.clock_FMD_excluded_anchor_record_ids[source],anchorIndex=index.get(anchorId);
    if(anchorIndex===undefined)throw new Error('The source anchor is absent from this membership');
    const fixedComponent=fixed.result.component[anchorIndex],weightedComponent=weighted.result.component[anchorIndex];
    const membersFixed=[],membersWeighted=[],local=[],localFixed=[],localWeighted=[],added=[],removed=[];
    const fixedSet=new Set(),weightedSet=new Set();
    for(let i=0;i<rows.length;i++){
      const f=fixed.result.component[i]===fixedComponent,w=weighted.result.component[i]===weightedComponent;
      if(f){membersFixed.push(i);fixedSet.add(i);}if(w){membersWeighted.push(i);weightedSet.add(i);}
      if(w&&!f)added.push(i);if(f&&!w)removed.push(i);
      if(inside(rows[i],a,view)){local.push(i);if(f)localFixed.push(i);if(w)localWeighted.push(i);}
    }
    // Published witnesses retain the predeclared 150-km, -7/+30-day selection.
    // Changing only the displayed window must not silently rename them.
    const published={radius:definition.radius_km||150,before:Math.abs(definition.relative_days?.[0]??-7),after:definition.relative_days?.[1]??30};
    const candidates=rows.map((_,i)=>i).filter(i=>(fixedSet.has(i)||weightedSet.has(i))&&fixed.result.roles[i]!==weighted.result.roles[i]&&!inside(rows[i],a,published));
    candidates.sort((i,j)=>Date.parse(rows[i].time_utc)-Date.parse(rows[j].time_utc)||(rows[i].record_id<rows[j].record_id?-1:rows[i].record_id>rows[j].record_id?1:0));
    return {source,rows,index,anchorId,anchorIndex,fixed:fixed.result,weighted:weighted.result,membersFixed,membersWeighted,fixedSet,weightedSet,added,removed,local,localFixed,localWeighted,witnessIndex:candidates[0]??null,fixedSpan:span(rows,membersFixed),weightedSpan:span(rows,membersWeighted)};
  }
  function analyze({definitions,classified,pairs,state}){
    const definition=definitions.find(c=>String(c.year)===String(state.case));if(!definition)throw new Error('Unknown predeclared case');
    const view={radius:Number(state.radius??150),before:Number(state.before??7),after:Number(state.after??30)};
    if(![view.radius,view.before,view.after].every(Number.isFinite)||view.radius<=0||view.before<0||view.after<0)throw new Error('Invalid display window');
    const sources={};for(const source of ['ssn','usgs'])sources[source]=sourceAnalysis(source,definition,classified[source],view);
    const localIds=Object.fromEntries(Object.entries(sources).map(([s,v])=>[s,new Set(v.local.map(i=>v.rows[i].record_id))]));
    const localPairs=pairs.filter(p=>localIds.ssn.has(p.ssn)&&localIds.usgs.has(p.usgs));
    return {definition,anchor:anchor(definition),view,sources,localPairs};
  }
  function inspect(analysis,source,i){const s=analysis.sources[source],row=s.rows[i];if(!row)throw new Error('Unknown source record');const describe=r=>({role:r.roles[i],parent_record_id:r.parent[i]>=0?s.rows[r.parent[i]].record_id:null,log10_eta:r.log_eta[i],threshold_log10:r.metadata.threshold_log10,w:r.metadata.w});return {source,record_id:row.record_id,time_utc:row.time_utc,latitude:row.latitude,longitude:row.longitude,magnitude:row.magnitude,magnitude_type:row.magnitude_type??null,fixed:{...describe(s.fixed),in_anchor_family:s.fixedSet.has(i)},reported_b:{...describe(s.weighted),in_anchor_family:s.weightedSet.has(i)}};}
  function circle(a,radius=150){const rad=Math.PI/180,p=a.latitude*rad,l=a.longitude*rad,d=radius/RADIUS_KM,out=[];for(let i=0;i<=180;i++){const q=i*2*Math.PI/180,lat=Math.asin(Math.sin(p)*Math.cos(d)+Math.cos(p)*Math.sin(d)*Math.cos(q)),lon=l+Math.atan2(Math.sin(q)*Math.sin(d)*Math.cos(p),Math.cos(d)-Math.sin(p)*Math.sin(lat));out.push([lat/rad,((lon/rad+540)%360)-180]);}return out;}
  return Object.freeze({analyze,inspect,distance,inside,circle,DAY});
});

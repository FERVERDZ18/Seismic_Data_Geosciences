/* Summaries derived from retained measured runs, without making new timings. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.PerformanceMath=api;})(typeof window!=='undefined'?window:this,function(){
  'use strict';
  const BACKENDS=['cached_reference','kd','octree'];
  const TIMINGS=['preparation_seconds','tree_seconds','kernel_seconds','postprocess_seconds','total_seconds'];
  const COUNTERS=['candidate_pairs','visited_nodes','bound_tests','pruned_on_pop','pruned_before_push'];
  function median(values){
    if(!values.length||values.some(v=>!Number.isFinite(v)))throw new TypeError('Finite measurements required');
    const sorted=values.slice().sort((a,b)=>a-b),middle=Math.floor(sorted.length/2);
    return sorted.length%2?sorted[middle]:(sorted[middle-1]+sorted[middle])/2;
  }
  function summarize(data){
    if(data?.schema!=='seismic-measured-search-performance/1'||!Array.isArray(data.measurements))throw new TypeError('Unknown measured-performance schema');
    const result=[],groups=new Map(),seen=new Set();
    for(const row of data.measurements){
      if(!Number.isInteger(row.n)||row.n<2||!BACKENDS.includes(row.backend)||!Number.isInteger(row.rep))throw new TypeError('Invalid measured run');
      for(const field of TIMINGS)if(!Number.isFinite(row[field])||row[field]<0)throw new TypeError('Invalid duration: '+field);
      const id=[row.n,row.backend,row.rep].join(':');if(seen.has(id))throw new Error('Duplicate measured run');seen.add(id);
      const key=row.n+':'+row.backend;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);
    }
    const sizes=[...new Set(data.measurements.map(row=>row.n))].sort((a,b)=>a-b);
    for(const n of sizes){
      const reference=groups.get(n+':cached_reference');if(!reference?.length)throw new Error('Missing measured exhaustive reference');
      const referenceTime=median(reference.map(row=>row.total_seconds));
      const eligible=Number(data.eligible_earlier_pairs?.[String(n)]);
      if(!Number.isSafeInteger(eligible)||eligible<=0||eligible>n*(n-1)/2)throw new Error('Invalid strictly earlier pair count');
      for(const backend of BACKENDS){
        const runs=groups.get(n+':'+backend);if(!runs?.length)throw new Error('Missing measured backend');
        const row={n,backend,repetitions:runs.length,threads:backend==='cached_reference'?4:1,
          median_total_seconds:median(runs.map(r=>r.total_seconds)),
          min_total_seconds:Math.min(...runs.map(r=>r.total_seconds)),max_total_seconds:Math.max(...runs.map(r=>r.total_seconds)),
          median_build_seconds:median(runs.map(r=>r.tree_seconds)),median_kernel_seconds:median(runs.map(r=>r.kernel_seconds)),
          median_preparation_seconds:median(runs.map(r=>r.preparation_seconds)),median_postprocess_seconds:median(runs.map(r=>r.postprocess_seconds)),eligible_earlier_pairs:eligible};
        row.speedup_vs_native=referenceTime/row.median_total_seconds;
        for(const field of COUNTERS){
          const values=runs.map(r=>r[field]);
          if(backend==='cached_reference')row[field]=null;
          else {if(values.some(v=>!Number.isSafeInteger(v)||v<0)||new Set(values).size!==1)throw new Error('Non-deterministic or absent search counter: '+field);row[field]=values[0];}
        }
        row.evaluated_percent=row.candidate_pairs===null?null:100*row.candidate_pairs/eligible;
        row.visited_per_query=row.visited_nodes===null?null:row.visited_nodes/n;
        row.pruned_per_query=row.pruned_on_pop===null?null:(row.pruned_on_pop+row.pruned_before_push)/n;
        result.push(row);
      }
    }
    return result;
  }
  function phases(row){return [
    {id:'build',seconds:row.median_build_seconds},
    {id:'search',seconds:row.median_kernel_seconds},
    {id:'numeric',seconds:row.median_preparation_seconds+row.median_postprocess_seconds}
  ];}
  function eligiblePairs(rows){
    const counts=new Map();
    for(const row of rows){const seconds=Number(row.t_year)*31557600;if(!Number.isFinite(seconds))throw new TypeError('Invalid observed event time');counts.set(seconds,(counts.get(seconds)||0)+1);}
    let eligible=rows.length*(rows.length-1)/2;for(const count of counts.values())eligible-=count*(count-1)/2;
    return eligible;
  }
  return Object.freeze({BACKENDS,median,summarize,phases,eligiblePairs});
});

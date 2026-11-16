/* Observed-magnitude diagnostics. These transforms never rewrite source rows. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.SequenceDiagnosticsMath=api;})(typeof self!=='undefined'?self:this,function(){
  'use strict';
  function decimal(value){
    if(!Number.isFinite(Number(value)))throw new TypeError('Finite reported magnitude required');
    const s=String(value).trim(),m=/^([+-]?)(\d+)(?:\.(\d*))?(?:e([+-]?\d+))?$/i.exec(s);
    if(!m)throw new TypeError('Decimal magnitude required');
    const fraction=m[3]||'',exponent=Number(m[4]||0)-fraction.length;
    if(Math.abs(exponent)>400)throw new RangeError('Magnitude exponent out of range');
    return {n:BigInt((m[1]==='-'?'-':'')+(m[2]+fraction)),exponent};
  }
  function compareDecimal(a,b){
    const x=decimal(a),y=decimal(b),e=Math.min(x.exponent,y.exponent),xx=x.n*10n**BigInt(x.exponent-e),yy=y.n*10n**BigInt(y.exponent-e);
    return xx<yy?-1:xx>yy?1:0;
  }
  function tenthHalfUp(value){
    const x=decimal(value),e=x.exponent+1;
    if(e>=0)return Number(x.n*10n**BigInt(e));
    const sign=x.n<0n?-1n:1n,n=x.n*sign,d=10n**BigInt(-e),q=n/d,r=n%d;
    return Number(sign*(q+(2n*r>=d?1n:0n)));
  }
  function gft(values,cut){
    const threshold=Number(cut);if(!Number.isFinite(threshold))throw new TypeError('Finite cut required');
    const hist=new Map();let n=0,sumTenths=0;
    for(const value of values){if(compareDecimal(value,cut)<0)continue;const m=tenthHalfUp(value);hist.set(m,(hist.get(m)||0)+1);n++;sumTenths+=m;}
    if(!n)return {n:0,b_reported_MLE:null,fit_percent:null,conventional_ShI_Bolt_se_not_declustered:null,points:[]};
    const mean=sumTenths/(n*10),denominator=mean-(threshold-.05),b=denominator>0?Math.LOG10E/denominator:null;
    const low=tenthHalfUp(cut),high=Math.max(...hist.keys()),counts=[];let cumulative=0;
    for(let k=high;k>=low;k--){cumulative+=hist.get(k)||0;counts.push({magnitude:k/10,observed:cumulative,predicted:b===null?null:n*10**(-b*(k/10-threshold))});}
    counts.reverse();let observedSum=0,absoluteError=0,squared=0;
    for(const p of counts){observedSum+=p.observed;absoluteError+=Math.abs(p.observed-p.predicted);}
    for(const [k,count] of hist)squared+=count*(k/10-mean)**2;
    return {n,b_reported_MLE:b,fit_percent:b===null?null:100*(1-absoluteError/observedSum),conventional_ShI_Bolt_se_not_declustered:n>1&&b!==null?2.30*b*b*Math.sqrt(squared/(n*(n-1))):null,points:counts};
  }
  function cumulativeFmd(rows){
    const histogram=new Map();for(const row of rows){const value=Number(row.magnitude);if(!Number.isFinite(value))throw new TypeError('Invalid observed magnitude');histogram.set(value,(histogram.get(value)||0)+1);}
    const values=[...histogram.keys()].sort((a,b)=>b-a);let n=0;
    return values.map(magnitude=>({magnitude,count:histogram.get(magnitude),cumulative:n+=histogram.get(magnitude)})).reverse();
  }
  function quantile(sorted,p){if(!sorted.length)return null;const h=(sorted.length-1)*p,i=Math.floor(h);return sorted[i]+(sorted[Math.min(i+1,sorted.length-1)]-sorted[i])*(h-i);}
  function boxSummary(items){
    const values=items.map(p=>Number(p.delta_m)).sort((a,b)=>a-b);if(!values.length)return null;
    const q1=quantile(values,.25),median=quantile(values,.5),q3=quantile(values,.75),iqr=q3-q1,lower=q1-1.5*iqr,upper=q3+1.5*iqr;
    const inside=values.filter(v=>v>=lower&&v<=upper);
    return {n:values.length,q1,median,q3,iqr,lower_whisker:inside[0],upper_whisker:inside[inside.length-1],outliers:items.filter(p=>Number(p.delta_m)<lower||Number(p.delta_m)>upper)};
  }
  function pairedGroups(pairs,ssnRows,usgsRows,cut='3.5'){
    const ssn=new Map(ssnRows.map(r=>[r.record_id,r])),usgs=new Map(usgsRows.map(r=>[r.record_id,r]));
    const retained=[];for(const pair of pairs){const a=ssn.get(pair.ssn),b=usgs.get(pair.usgs);if(!a||!b||compareDecimal(a.magnitude,cut)<0||compareDecimal(b.magnitude,cut)<0)continue;
      const delta=pair.delta_m;if(!Number.isFinite(Number(delta)))throw new TypeError('Missing observed decimal difference');
      retained.push({...pair,delta_m:delta,ssn_row:a,usgs_row:b,type:b.magnitude_type||'unreported'});
    }
    const counts=new Map();for(const p of retained)counts.set(p.type,(counts.get(p.type)||0)+1);
    const names=[...counts.keys()].filter(k=>counts.get(k)>=50).sort();const groups=names.map(name=>({name,pairs:retained.filter(p=>p.type===name)}));
    const other=retained.filter(p=>!names.includes(p.type));if(other.length)groups.push({name:'other',pairs:other});
    return {pairs:retained,groups:groups.map(g=>({...g,...boxSummary(g.pairs)}))};
  }
  function trPoints(rows,result){
    if(rows.length!==result.ids.length)throw new Error('Classification/input length mismatch');
    const points=[];let noParent=0,nonpositive=0;
    for(let i=0;i<rows.length;i++){
      if(result.parent[i]<0){noParent++;continue;}
      const tn=result.tn[i],rn=result.rn[i];if(!(tn>0&&rn>0&&Number.isFinite(tn)&&Number.isFinite(rn))){nonpositive++;continue;}
      const x=Math.log10(tn),y=Math.log10(rn),score=x+y;
      points.push({i,x,y,score,retained:score<=result.metadata.threshold_log10});
    }
    return {points,no_parent:noParent,nonpositive_with_parent:nonpositive,total:rows.length};
  }
  return Object.freeze({compareDecimal,tenthHalfUp,gft,cumulativeFmd,quantile,boxSummary,pairedGroups,trPoints});
});
